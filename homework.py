import requests
import os

import logging
import time
from time import sleep
from http import HTTPStatus
from dotenv import load_dotenv

import telegram


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
payload = {'from_date': 0}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(name)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def check_tokens():
    """
    Проверяет доступность.
    переменных окружения,
    которые необходимы для работы программы
    """
    return all(
        [PRACTICUM_TOKEN,
         TELEGRAM_TOKEN,
         TELEGRAM_CHAT_ID]
    )


logger.debug('С токенами все ОК')


def send_message(bot, message):
    """
    Отправляет сообщение в Telegram чат.
    определяемый переменной окружения
    TELEGRAM_CHAT_ID. Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения
    """
    try:
        message = 'Сообщение доставлено'
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.NetworkError:
        sleep(5)
    except telegram.error.TelegramError:
        logging.error('Сообщение не доставлено')
    else:
        logging.debug('Сообщение отправлено')


def get_api_answer(timestamp):
    """
    Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра в функцию передается временная метка
    В случае успешного запроса должна вернуть ответ API,
    приведя его из формата JSON к типам данных Python.
    """
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        logger.error(f'Ошибка при запросе: {Exception}')
    else:
        if homework_statuses.status_code != HTTPStatus.OK:
            error_message = 'Статус != 200'
            raise requests.HTTPError(error_message)
        return homework_statuses.json()
    logger.debug('Запрос к эндпоинту прошел успешно')


def check_response(response):
    """
    Проверяет ответ API на соответствие документации.
    из урока API сервиса
    Практикум.Домашка
    """
    if not isinstance(response, dict):
        raise TypeError('Переменная не соответствует типу "dict"')

    if 'homeworks' not in response:
        raise KeyError('Нет ключа homeworks в ответе от API')

    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Переменная не соответствует типу "list"')
    else:
        logger.debug('Ответ от API соответ. документации')
    return homeworks


def parse_status(homework):
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

    if 'status' not in homework:
        raise KeyError('Нет такого ключа')

    if 'homework_name' not in homework:
        raise KeyError('Нет такого ключа')

    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('Нет такого статуса')

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


logger.debug('Статус успешно получен')


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    if check_tokens() is not True:
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
                return 'Нет подходящего статуса для ответа'

        except Exception:
            message = f'Сбой в работе программы: {Exception}'
            logging.error(message)
            send_message(bot, message)
        else:
            logger.error('Ошибка в цикле True')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
