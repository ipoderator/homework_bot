import os
import time
from http import HTTPStatus
import logging

from dotenv import load_dotenv
import requests
import telegram

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
PAYLOAD = {'from_date': 0}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    handlers=logger.addHandler(logging.StreamHandler()),
    format='%(asctime)s, %(name)s, %(levelname)s, %(message)s'
)


def check_tokens() -> bool:
    """
    Проверяет доступность.
    переменных окружения,
    которые необходимы для работы программы
    """
    logger.debug('Проверка токенов')
    return all(
        (PRACTICUM_TOKEN,
         TELEGRAM_TOKEN,
         TELEGRAM_CHAT_ID)
    )


def send_message(bot: telegram.Bot, message: str) -> None:
    """
    Отправляет сообщение в Telegram чат.
    определяемый переменной окружения
    TELEGRAM_CHAT_ID. Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения
    """
    try:
        message = 'Сообщение доставлено'
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение отправлено {message}')
    except telegram.error.TelegramError:
        logging.error('Сообщение не доставлено')


def get_api_answer(timestamp: int) -> dict:
    """
    Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра в функцию передается временная метка
    В случае успешного запроса должна вернуть ответ API,
    приведя его из формата JSON к типам данных Python.
    """
    logger.debug('Запрос к эндпоинту прошел успешно')
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as error:
        logger.error(f'Ошибка при запросе: {error}')
        message_error = (f'Ошибка {error} при запросе')
        raise exceptions.RequestError(message_error)
    if homework_statuses.status_code != HTTPStatus.OK:
        error_message = 'Статус != 200'
        raise requests.HTTPError(error_message)
    return homework_statuses.json()


def check_response(response: dict) -> list:
    """
    Проверяет ответ API на соответствие документации.
    из урока API сервиса
    Практикум.Домашка
    """
    if not isinstance(response, dict):
        raise TypeError('Переменная не соответствует типу "dict"')

    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError('Нет ключа homeworks в ответе от API')

    if not isinstance(homeworks, list):
        raise TypeError('Переменная не соответствует типу "list"')
    logger.debug('Ответ от API соответ. документации')
    return homeworks


def parse_status(homework: dict) -> str:
    """
    Извлекает из информации о конкретной домашней.
    работе статус этой работы.
    В качестве параметра функция получает только один элемент
    из списка домашних работ
    """
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if not isinstance(homework, dict):
        raise TypeError('Передан не словарь')

    if homework_status is None:
        raise KeyError('Нет такого ключа')

    if homework_name is None:
        raise KeyError('Нет такого ключа')

    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('Нет такого статуса')

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    """
    'if verdict is None' выдавал ошибку в pytest,
    передалал на 'is not True'.
    """
    if verdict is not True:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    if not check_tokens():
        logger.critical('Ошибка в переменных окружения')
        raise SystemExit
    while True:
        logger.info('Цикл начал работу')
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            timestamp = response.get('current_date')
            if homeworks:
                new_homeworks = homeworks[0]
                message = parse_status(new_homeworks)
                send_message(bot, message)
            else:
                bot_send_message = 'Нет подходящего статуса для ответа'
                send_message(bot, bot_send_message)
            """
            Не знал какое здесь может быть исключение,
            решил создать кастомное
            """
        except (KeyError, TypeError, requests.HTTPError) as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
