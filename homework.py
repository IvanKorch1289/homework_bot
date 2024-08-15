import logging
import os
import sys
import time
from http import HTTPStatus

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


class CurrentVerdict:
    """Класс-синглтон для хранения последнего вердикта."""

    _verdict = None

    def __new__(cls):
        """Метод создания одного единственного экземпляра класса."""
        if not hasattr(cls, 'instance'):
            cls.instance = super(CurrentVerdict, cls).__new__(cls)
        return cls.instance

    def change_verdict(self, current_verdict):
        """Метод изменения атрибута verdict экземпляра."""
        self._verdict = current_verdict


def check_tokens():
    """Функция проверки переменных окружения."""
    const_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(const_list)


def send_message(bot, message):
    """Функция отправки сообщения боту."""
    try:
        logging.debug('Попытка отправить сообщение')
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
        if response.status_code != HTTPStatus.OK:
            raise NotHttp200StatusException('Статус ответа не равен 200')
        return response.json()
    except requests.RequestException:
        logging.error('Ошибка запроса к Яндекс.Практикум')


def check_response(response):
    """Функция проверки ответа сервиса."""
    if not isinstance(response, dict):
        raise TypeError('Некорректная структура ответа сервиса')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('Некорректный формат ответа для параметра "homeworks"')

    homeworks = response.get('homeworks')
    return homeworks[0] if homeworks else None


def parse_status(homework):
    """Функция получения результата из запроса."""
    current_verdict = CurrentVerdict()
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
    if current_verdict._verdict != verdict and homework_name and verdict:
        current_verdict.change_verdict(verdict)
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        raise KeyError('Не найдены необходимые параметры в ответе')


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
                if check:
                    parsing = parse_status(check)
                    send_message(bot, message=parsing)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message=message)
            finally:
                time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
