# Teledate

Asynchronous Telegram bot for keeping up with activities timelines.

Bot commands:

- `/start` - Start the bot
- `/database` - Manage the database / Create user
- `/end` - End the conversation.

From the main menu you can perform commands with messages:

- `Status` - get current record timiline
- `Add record` - add new record or update the current one
- `Graph` - draw a graph of your activity timelines (x - dates, y - hours)
- `Reminder` - set or unset reminder with specified time interval
(default: 48 hours)

From the database management menu you can perform commands with messages:

- `Create database` - create a database for the current user
- `Delete database` - delete the current user's database
- `Delete last record` - delete the last user record


## Technologies

- Python
- Python Telegram Bot
- Asyncio
- SQLAlchemy
- Matplotlib
- Pytest
- MySQL
- SQLite

## Standards

- pep8
- flake8
- black
- pymarkdown

## How to run

1. Clone the repository.
2. Add `.env` file to the root folder with `TELEGRAM_TOKEN` variable
3. From the root folder run:

    ```bash
    python teledate/app/main.py
    ```

4. Check log at teledate/data/teledate.log

## TBD

- Add the capability to create multiple records for a user
- Cover the rest of the functionality with `Pytest` tests
