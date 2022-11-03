import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_STATUSES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

logging.basicConfig(
    level=logging.DEBUG,
    filename="program.log",
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s - %(name)s",
)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def send_message(bot, message):
    """Отправляет сообщения пользователю."""
    try:
        post_message = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Бот отправил сообщение "{message}"')
        return post_message

    except telegram.error.TelegramError as error:
        logger.error(error)
        raise error


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )

    except ConnectionError as error:
        logger.error(error)
        raise error

    if homework_statuses.status_code != requests.codes.ok:
        homework_statuses.raise_for_status()

    try:
        result = homework_statuses.json()

    except requests.exceptions.JSONDecodeError as error:
        logger.error(error)
        raise error

    return result


def check_response(response):
    """Проверяет ответ API на корректность"""
    try:
        homeworks = response["homeworks"]
        response["current_date"]

    except KeyError as error:
        logger.error(error)
        raise error

    except TypeError as error:
        logger.error("Ответ от API пришёл не в виде словаря.")
        raise error
    homeworks = response["homeworks"]

    if not isinstance(homeworks, list):
        raise TypeError

    if homeworks == []:
        logger.debug("Новые статусы отсутствуют")

    return homeworks


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы"""
    try:
        homework_name = homework["homework_name"]
        homework_status = homework["status"]

    except KeyError as error:
        logger.error(error)
        raise error

    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения"""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True

    else:
        error_message = (
            "Отсутствует(ют) обязательная(ые) переменная(ые) окружения:"
        )
        if not PRACTICUM_TOKEN:
            error_message += "PRACTICUM_TOKEN"

        if not TELEGRAM_TOKEN:
            error_message += "TELEGRAM_TOKEN"

        if not TELEGRAM_CHAT_ID:
            error_message += "TELEGRAM_CHAT_ID"

        logger.critical(error_message)

        return False


def main():
    """Основная логика работы бота."""
    logger.debug("Бот запущен")

    if check_tokens() is False:
        logger.critical("Отсутствуют переменные окружения")
        sys.exit("Прервать: Отсутствуют переменные окружения")

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)

            for homework in homeworks:
                message = parse_status(homework)
                send_message(bot, message)

            current_timestamp = int(response["current_date"])
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logger.error(message)
            send_message(bot, message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == "__main__":
    main()
