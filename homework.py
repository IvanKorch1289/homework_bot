import logging
import os
import sys
import time
import requests

from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import EnvironmentVarsException, NotHttp200StatusException


load_dotenv()


PRACTICUM_TOKEN = os.getenv('YANDEX_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler_out = logging.StreamHandler(sys.stdout)
handler_out.setLevel(logging.DEBUG)
handler_out.setFormatter(formatter)

handler_err = logging.StreamHandler(sys.stderr)
handler_err.setLevel(logging.WARNING)
handler_err.setFormatter(formatter)

logger.addHandler(handler_out)
logger.addHandler(handler_err)

current_verdict = None


def check_tokens():
    """Функция проверки переменных окружения."""
    const_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return (False if None in const_list else True)


def send_message(bot, message):
    """Функция отправки сообщения боту."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено')
    except Exception as error:
        logging.error(f'Сообщение не отправлено: {error}')


def get_api_answer(timestamp):
    """Функция отправки запроса по API."""
    payload = {'from_date': timestamp}

    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=payload
        )
        if response.status_code != 200:
            raise NotHttp200StatusException('Статус ответа не равен 200')
        return response.json()
    except requests.RequestException:
        pass


def check_response(response):
    """Функция проверки ответа сервиса."""
    if not isinstance(response, dict):
        raise TypeError
    if not isinstance(response.get('homeworks'), list):
        raise TypeError

    homeworks = response.get('homeworks')
    if len(homeworks) > 0:
        return homeworks[0]
    return None


def parse_status(homework):
    """Функция получения результата из запроса."""
    global current_verdict
    check_key_name = 'homework_name' in homework.keys()
    check_status = homework['status'] in HOMEWORK_VERDICTS.keys()
    if check_key_name and check_status:
        homework_name = homework.get('homework_name')
        verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
        if current_verdict != verdict:
            current_verdict = verdict
            return (
                'Изменился статус проверки работы '
                f'"{homework_name}". {verdict}'
            )
    else:
        raise KeyError


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Не найдены переменные окружения')
        raise EnvironmentVarsException
    else:
        bot = TeleBot(TELEGRAM_TOKEN)
        timestamp = int(time.time())

        while True:
            try:
                result = get_api_answer(timestamp)
                logging.debug('Ответ получен')
                check = check_response(result)
                logging.debug('Ответ разобран')
                parsing = parse_status(check)
                send_message(bot, message=parsing)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message=message)
            finally:
                time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
