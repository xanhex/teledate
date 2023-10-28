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
- Uvicorn
- Docker

## Standards

- pep8
- flake8
- black
- pymarkdown

## How to run

1. Clone the repository.
2. From the root folder run:

    ```bash
    docker compose up
    ```

## TBD

- Add `Pytest` tests
- Add logging
- Add the ability to add multiple records for a user
- Add demonization (`Uvicorn`) and `Docker`
