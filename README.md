# Teledate

Asynchronous Telegram bot for keeping up with activities timelines.

Bot commands:

- `/start` - Start the bot
- `/database` - Manage the database
- `/end` - End the conversation.

## Technologies

- Python
- Python Telegram Bot
- Asyncio
- SQLAlchemy
- Pytest
- MySQL

## Standards

- pep8
- flake8
- black
- pymarkdown

## How to run

1. Clone the repository.
2. From the root folder run:

    ```bash
    python teledate/app/main.py
    ```

3. Check log at teledate/data/teledate.log

## TBD

- Add the ability to add multiple records for a user
- Cover the rest of the functionality with `Pytest` tests
