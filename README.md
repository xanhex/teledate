# Telegram бот для проверки статуса домашки Практикума

Приложение, которое позволяет автоматически отслеживать статус домашки
на Практикуме и получать уведомления в телегу.

## Технологии

- Python 3.9.10

## Библиотеки и модули

- python-telegram-bot
- requests

## Используемые стандарты

- pep8
- flake8
- black
- mypy
- pymarkdown

## Как развернуть

1. Склонируйте проект в рабочую директорию.
2. Создайте виртуальное окружение.
3. Установите зависимости из файла `requirements.txt`.
4. Получите [токен](
https://oauth.yandex.ru/authorize?response_type=token&client_id=1d0b9dd4d652455a9eb710d450ff456a)
для авторизации.
5. В корне проекта создайте файл с переменными окружения `.env`

     ```.env
    PRACTICUM_TOKEN=XXX
    TELEGRAM_TOKEN=XXX
    TELEGRAM_CHAT_ID=123
    ```
