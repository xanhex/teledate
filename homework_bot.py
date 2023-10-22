# coding: utf-8
"""Телеграм бот для проверки статуса домашней работы."""

import logging
import time
from functools import wraps
from operator import itemgetter
from typing import Any, Dict, Union

import requests
import telegram
from decouple import config

import exeptions

PRACTICUM_TOKEN = config('PRACTICUM_TOKEN', default='123')
TELEGRAM_TOKEN = config('TELEGRAM_TOKEN', default='123')
TELEGRAM_CHAT_ID = config('TELEGRAM_CHAT_ID', default='0123456789')

TRUNCATE = 79
RETRY_PERIOD = 600  # период запроса к API в 10 минут (600/60)
START_DATE = 1549962000  # Unix time даты открытия Практикума
DT = 604800  # временной сдвиг на одну неделю (60*60*24*7)
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='bot.log',
    filemode='w',
    encoding='utf-8',
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%d.%m.%y %H:%M:%S',
)


def func_logger(func):
    """Декоторатор для логирования функций."""

    @wraps(func)
    def inner(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            logging.debug(
                'Функция <%s> выполнена успешно',
                func.__name__,
            )
            return result
        except Exception as error:
            logging.exception(
                'Функция <%s> с аргументами %s вызвала ошибку %r',
                func.__name__,
                (args, kwargs),
                error,
                exc_info=False,
            )
            raise error.__class__(
                f'Функция <{func.__name__}> вызвала ошибку {repr(error)}',
            )

    return inner


def check_tokens() -> None:
    """Проверяет константы окружения.

    Raises:
        Exception: При отсуствие константы.
    """
    missing = [
        env
        for env in ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
        if env not in globals() or not globals().get(env)
    ]
    if missing:
        message = (
            'Отсутствуют константы окружения: '
            f'{", ".join(map(lambda x: "`{}`".format(x), missing))}'
        )
        logging.critical(message)
        raise exeptions.EnviriableError(message)


@func_logger
def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправить сообщение в телеге.

    Args:
        bot: объект бота телеги.
        message: пересылаемое сообщение.

    Raises:
        Exception: При отправке сообщения в телегу.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        raise telegram.error.TelegramError(
            f'Ошибка соединения с Telegram: `{error}`',
        )


@func_logger
def get_api_answer(timestamp: float) -> Dict[str, Any]:
    """Проверяет ответ от API Практикума.

    Args:
        timestamp: метка начала отрезка времени.

    Returns:
        Ответ от API Практикума в формате JSON.

    Raises:
        Exception: При проблеме с соединением.
        PracticumStatusError: При неверном статусе ответа от API Практикума.
    """
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp},
        )
    except requests.RequestException as error:
        raise Exception('Проблема с соединением: `%s`', error)
    if homework_statuses.status_code != requests.codes.OK:
        raise exeptions.PracticumStatusError(
            'Неверный статус ответа от API Практикума: '
            f'`{homework_statuses.status_code}`',
        )
    return homework_statuses.json()


@func_logger
def check_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Проверяет корректность полученного ответа.

    Args:
        response: ответ API в формате JSON.

    Raises:
        TypeError: Если ответ API некорректен.
    """
    if (
        isinstance(response, dict)
        and all(key in response for key in ('current_date', 'homeworks'))
        and isinstance(response.get('homeworks'), list)
    ):
        return response
    raise TypeError('Полученый от API ответ некорректен')


@func_logger
def parse_status(homework: Dict[str, Any]) -> str:
    """Проверяет корректность полученного ответа.

    Args:
        response: ответ API в формате JSON.

    Returns:
        Строку с информацией о статусе домашней работы.

    Raises:
        KeyError: Если необходимые ключи отсутствуют в словаре.
        UnexpectedStatusError: При неожиданном статусе домашней работы.
    """
    try:
        homework_name, homework_status = itemgetter('homework_name', 'status')(
            homework,
        )
    except KeyError as error:
        raise KeyError(f'Ключ {error} отсутствует в словаре')
    if homework_status not in HOMEWORK_VERDICTS:
        raise exeptions.UnexpectedStatusError(
            'Неожиданный статус домашней работы',
        )
    return (
        f'Изменился статус проверки работы '
        f'"{homework_name}". {HOMEWORK_VERDICTS[homework_status]}'
    )


def main() -> None:
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    # timestamp = int(time.time()) - DT  # для недавних работ
    timestamp = START_DATE
    errors = []
    current_status: Union[str, None] = None

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response.get('homeworks')
            if homework and isinstance(homework, list):
                status = parse_status(homework[0])
                if status != current_status:
                    current_status = status
                    send_message(bot, status)
            else:
                print('Cписок работ за выбранный период пуст.')
        except Exception as error:
            message = str(error)
            if message not in errors and not isinstance(
                error,
                telegram.TelegramError,
            ):
                errors.append(message)
                send_message(bot, message)
        logging.debug('Бот ушёл спать на %s минут', int(RETRY_PERIOD / 60))
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
