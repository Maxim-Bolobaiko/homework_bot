import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
import telegram.ext
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info("Бот отправил сообщение!")
        return True
    except Exception:
        logger.exception("Сообщение не отправлено!")
        return False


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp
    params = {"from_date": timestamp}
    error_text = "Ошибка при запросе к API!"
    error_text_json = "Ой, вренулся не json!"

    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
    except Exception as error:
        logger.error(f"Ошибка {error} при запросе к API!")
        raise Exception(f"Ошибка {error}")

    if homework_statuses.status_code != HTTPStatus.OK:
        logger.error(error_text)
        raise Exception(error_text)

    try:
        return homework_statuses.json()

    except ValueError:
        logger.error(error_text_json)
        raise ValueError(error_text_json)


def check_response(response):
    """Проверяет ответ API на корректность."""
    error_text = "Неверный тип данных!"

    try:
        homeworks = response["homeworks"]
    except KeyError:
        raise KeyError("Искомое значение отсутствует!")
    if not isinstance(homeworks, list):
        logger.error(error_text)
        raise TypeError(error_text)

    return homeworks


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    try:
        homework_name = homework["homework_name"]
        homework_status = homework["status"]
        verdict = HOMEWORK_VERDICTS[homework_status]
    except KeyError:
        raise KeyError("Искомое значение отсутствует!")

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if not TELEGRAM_TOKEN or not PRACTICUM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.critical("Отсутствуют необходимые токены!")
        return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    error_text = "Домашек нет: проверять нечего!"
    last_message_1 = ""
    last_message_2 = ""

    while True:
        try:
            response = get_api_answer(current_timestamp)

            chek = check_response(response)

            if not chek:
                logger.debug(error_text)
                message = error_text
                if last_message_1 != message:
                    send_message(bot, message)
                    last_message_1 = message
            message = parse_status(chek[0])

            send_message(bot, message)

            current_timestamp = response.get("current_date")
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            if last_message_2 != message:
                if send_message(bot, message):
                    last_message_2 = message
            time.sleep(RETRY_TIME)


if __name__ == "__main__":
    main()
