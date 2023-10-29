"""
Asynchronous Telegram bot for keeping up with activities timelines.

Bot commands:
    - `/start` - Start the bot
    - `/database` - Manage the database
    - `/end` - End the conversation
"""
import datetime
import logging
import re
from functools import partial
from pathlib import Path

from decouple import config
from telegram import ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

BASE_DIR = Path(__file__).resolve().parent.parent

filePath = BASE_DIR / 'data' / 'teledate.log'

filePath.touch(exist_ok=True)

import database as db
from exceptions import TeledateError
from utils import ReplyMarkups, get_graph, get_time_since

logging.basicConfig(
    level=logging.DEBUG,
    filename=filePath,
    filemode='w',
    encoding='utf-8',
    format='%(asctime)s %(name)s [%(levelname)s] %(message)s',
    datefmt='%d.%m.%y %H:%M:%S',
)


TELEGRAM_TOKEN = config('TELEGRAM_TOKEN', default='123')

DB, DB_MANAGE, DB_ACTIVITY, MAIN, REMINDER = range(5)


# Handlers


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation when `/start` command is issued."""
    username = update.effective_user.username
    db_user_id = context.user_data.get('db_user_id')
    db_user_activity = context.user_data.get('db_user_activity')
    reminder = context.user_data.get('reminder')
    if not db_user_id:
        db_user_id, db_user_activity = await db.get_user_info(
            username,
        )
        (
            context.user_data['db_user_id'],
            context.user_data['db_user_activity'],
        ) = (
            db_user_id,
            db_user_activity,
        )
    if reminder is None:
        reminder = context.user_data['reminder'] = bool(
            context.job_queue.get_jobs_by_name(username),
        )
    if db_user_id:
        await update.effective_message.reply_text(
            fr'*Hello, {username}\!*'
            + '\n\n'
            + r'To create manual record use this format\:'
            + '\n'
            + '`Add record 01.01.2000 10:00`',
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyMarkups.main_reminder
            if reminder
            else ReplyMarkups.main,
        )
        return MAIN
    await update.effective_message.reply_text(
        'Database does not exists. Try to set up one?',
        reply_markup=ReplyMarkups.start,
    )
    return DB


async def database(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get database options when `/database` command is issued."""
    db_user_id = context.user_data.get('db_user_id')
    db_user_activity = context.user_data.get('db_user_activity')
    if not db_user_id:
        db_user_id, db_user_activity = await db.get_user_info(
            update.effective_user.username,
        )
        (
            context.user_data['db_user_id'],
            context.user_data['db_user_activity'],
        ) = (
            db_user_id,
            db_user_activity,
        )
    if db_user_id:
        await update.effective_message.reply_text(
            'Database exists. Do you want to delete it?',
            reply_markup=ReplyMarkups.db_delete,
        )
        return DB_MANAGE
    if await db.get_user_count() >= db.USER_LIMIT:
        await update.effective_message.reply_text(
            "Can't create the database because the quota is over.",
            reply_markup=ReplyMarkups.end,
        )
        return ConversationHandler.END
    await update.effective_message.reply_text(
        'Create the database?',
        reply_markup=ReplyMarkups.db_create,
    )
    return DB_MANAGE


async def database_manage(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Handle the database management with messages.

    Messages:
        - Create database - proceed to database activity setup
        - Delete database - end the conversation upon deletion
        - Cancel - cancel the operation and gets back to previous state
    """
    db_user_id = context.user_data.get('db_user_id')
    message = update.effective_message.text
    username = update.effective_user.username
    current_jobs = context.user_data[
        'reminder'
    ] = context.job_queue.get_jobs_by_name(username)
    reminder = bool(current_jobs)
    # Database exists
    if message == 'Cancel' and db_user_id:
        await update.effective_message.reply_text(
            'Deletion was canceled',
            reply_markup=ReplyMarkups.main_reminder
            if reminder
            else ReplyMarkups.main,
        )
        return MAIN
    if db_user_id and message == 'Delete database':
        db_del = await db.delete_user(db_user_id)
        if not db_del:
            await update.effective_message.reply_text(
                "Can't delete database",
                reply_markup=ReplyMarkups.end,
            )
            return ConversationHandler.END
        del context.user_data['db_user_id']
        del context.user_data['db_user_activity']
        if reminder:
            for job in current_jobs:
                job.schedule_removal()
        context.user_data['reminder'] = False
        await update.effective_message.reply_text(
            'Database has been deleted',
            reply_markup=ReplyMarkups.end,
        )
        return ConversationHandler.END

    # Database doesn't exists
    if not db_user_id and message == 'Create database':
        await update.effective_message.reply_text(
            'What is your activity?',
            reply_markup=ReplyMarkups.db_activity,
        )
        return DB_ACTIVITY
    await update.effective_message.reply_text(
        'Database was not created',
        reply_markup=ReplyMarkups.end,
    )
    return ConversationHandler.END


async def database_activity(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int | None:
    """
    Set up the database activity name with messages.

    Messages:
        - Message - set the name of the activity with user message
        - Default - set Default name for the activity
        - Cancel - cancel the operation and gets back to the previous state
    """
    message = update.effective_message.text
    username = update.effective_user.username
    if message == 'Cancel':
        await update.effective_message.reply_text(
            'Database was not created',
            reply_markup=ReplyMarkups.end,
        )
        return ConversationHandler.END
    try:
        activity = message.capitalize() if message != 'Default' else None
        db_user_id, activity = await db.create_user(username, activity)
        await update.effective_message.reply_text(
            '*Database has been created*\n\n'
            + r'To create manual record use this format\:'
            + '\n'
            + '`Add record 01.01.2000 10:00`',
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyMarkups.main,
        )
        context.user_data['db_user_id'] = db_user_id
        context.user_data['db_user_activity'] = activity
        return MAIN
    except TeledateError:
        await update.effective_message.reply_text(
            "Can't create database. Try another activity name",
        )
        return None


async def main_messages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int | None:
    """
    Handle bot main menu with messages.

    Messages:
        - Status - get the current record info
        - Graph - get a graph of user's records
        - Reminder - proceed to the reminder settings
        - Add record [params] - add a new user's record
    """
    db_user_id = context.user_data.get('db_user_id')
    db_user_activity = context.user_data.get('db_user_activity')
    reminder = context.user_data.get('reminder')
    add_record_msg = re.compile(
        r'^Add record(\s\d{2}.\d{2}.\d{4}\s\d{2}:\d{2})?$',
    )
    match update.effective_message.text:
        case 'Status':
            status = await get_status(db_user_id)
            if not status:
                await update.effective_message.reply_text(
                    'No records have been created',
                )
                return None
            record_date, time_since = status
            text = f'*{db_user_activity}*\n\n`{record_date}`\n{time_since} ago'
        case 'Graph':
            records_dt = await db.get_user_records(db_user_id)
            text = 'No records have been created'
            if records_dt:
                try:
                    graph = await get_graph(records_dt, db_user_activity)
                    await update.effective_message.reply_photo(
                        graph,
                        reply_markup=ReplyMarkups.main_reminder
                        if reminder
                        else ReplyMarkups.main,
                    )
                    return None
                except TeledateError:
                    text = "Can't load the graph"
        case 'Reminder' | 'Reminder: On' | 'Reminder: Off':
            await update.effective_message.reply_text(
                ('You have an active reminder. Unset?')
                if reminder
                else (
                    r'`Set (default interval: 48)`' + '\n'
                    '`Set <hour_interval>`\n'
                ),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyMarkups.unset
                if reminder
                else ReplyMarkups.set,
            )
            return REMINDER
        case add_record_msg:
            year_time: list | None = re.findall(
                r'(\d{2}.\d{2}.\d{4}\s\d{2}:\d{2})',
                add_record_msg,
            )
            created = await add_record(db_user_id, *year_time)
            if not created:
                await update.effective_message.reply_text(
                    "Can't create a record",
                )
                return None
            text = f'*{db_user_activity}*\n\n{created}'
    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyMarkups.main_reminder
        if reminder
        else ReplyMarkups.main,
    )
    return None


async def reminder_manage(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int | None:
    """
    Schedule or unschedule the reminder task with messages.

    Messages:
        - Set [params] - schedule the reminder task for the current user's
        record and proceed to the main menu
        - Unset - unschedule the reminder task and proceed to the main menu
        - Cancel - cancel the operation and get back to the main menu
    """
    command = update.effective_message.text
    if command == 'Cancel':
        await update.effective_message.reply_text(
            'Operation was canceled',
            reply_markup=ReplyMarkups.main_reminder,
        )
        return MAIN
    chat_id = update.effective_message.chat_id
    username = update.effective_user.username
    db_user_id = context.user_data.get('db_user_id')
    db_user_activity = context.user_data.get('db_user_activity')
    reminder = context.user_data.get('reminder')
    unset: list | None = re.findall(r'^Unset$', command)
    try:
        if reminder:
            current_jobs = context.job_queue.get_jobs_by_name(username)
            for job in current_jobs:
                job.schedule_removal()
            if unset:
                context.user_data['reminder'] = False
                await update.effective_message.reply_text(
                    'Reminder has been disabled',
                    reply_markup=ReplyMarkups.main,
                )
                return MAIN
        if not unset:
            params: list | None = re.findall(r'(\d{2})', command)
            interval, start = datetime.timedelta(hours=48), datetime.time(9)
            if params:
                interval = datetime.time(int(params[0]))
            record_date: datetime.datetime = await db.get_last_user_record(
                db_user_id,
            )
            start = record_date
            # interval = 5  # For 5 sec inteval tests
            context.job_queue.run_repeating(
                alarm,
                interval,
                first=start,
                chat_id=chat_id,
                name=username,
                data=(db_user_id, db_user_activity),
            )
            context.user_data['reminder'] = True
            await update.effective_message.reply_text(
                (
                    f'{db_user_activity}\n\n'
                    f'The reminder has been set on {start.strftime("%H:%M")} '
                    f'for every {interval} hours'
                ),
                reply_markup=ReplyMarkups.main_reminder,
            )
            return MAIN
    except (IndexError, ValueError):
        await update.effective_message.reply_text(
            ('`Set <hours_interval>`\n\n' '`Unset`'),
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def invalid_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    keyboard_markup: ReplyKeyboardMarkup = None,
    extra_message: str = None,
) -> None:
    """Handle invalid user inputs."""
    await update.effective_message.reply_text(
        'Invalid input' + (f'\n\n{extra_message}' if extra_message else ''),
        reply_markup=keyboard_markup,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End the conversation when `/end` command is issued."""
    await update.effective_message.reply_text(
        f'Goodbye, {update.effective_user.username}.',
        reply_markup=ReplyMarkups.end,
    )
    return ConversationHandler.END


# Helpers


async def get_status(db_user_id: int) -> tuple[str] | None:
    """
    Get user's record info.

    Returns:
        The record info and time since, None otherwise.
    """
    record_dt = await db.get_last_user_record(db_user_id)
    if not record_dt:
        return None
    # Moscow Time (UTC+3)
    record_dt += datetime.timedelta(hours=3)
    return (
        record_dt.strftime('%d.%m.%Y %H:%M:%S'),
        get_time_since(record_dt),
    )


async def add_record(
    db_user_id: int,
    year_time: str | None = None,
) -> str | None:
    """
    Create a new user's record.

    Returns:
        The record info and extra message, None otherwise.
    """
    extra_message = (
        'Old records have been deleted'
        if await clear_old_record(db_user_id)
        else ''
    )
    try:
        if year_time:
            year_time_dt = datetime.datetime.strptime(
                year_time,
                '%d.%m.%Y %H:%M',
            )
            current_record_date = await db.get_last_user_record(
                db_user_id,
            )
            if (
                current_record_date
                and year_time_dt
                < current_record_date
                + datetime.timedelta(
                    hours=3,
                )
            ):
                raise
            if year_time_dt > datetime.datetime.today():
                raise
            record_date = await db.create_record(
                db_user_id,
                date=year_time_dt,
            )
        else:
            record_date = await db.create_record(db_user_id)
            # Moscow Time (UTC+3)
            record_date = (record_date + datetime.timedelta(hours=3)).strftime(
                '%d.%m.%Y %H:%M',
            )
        return f'`{record_date}`\n{extra_message}'
    except TeledateError:
        return None


async def clear_old_record(db_user_id: str) -> bool:
    """Delete old user's records according to database records limit."""
    records = await db.get_user_records(db_user_id)
    if len(records) > db.RECORDS_LIMIT:
        deleted = await db.delete_records(
            db_user_id,
            count=db.RECORDS_LIMIT // 3,
        )
        if deleted:
            return True
    return False


async def alarm(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the alarm message to a user."""
    db_user_id, db_user_activity = context.job.data
    record_info, time_since = await get_status(db_user_id)
    await context.bot.send_message(
        context.job.chat_id,
        text=f'*{db_user_activity}*\n\n`{time_since}`\nSince the last record',
        parse_mode=ParseMode.MARKDOWN_V2,
    )


# Main bot cycle


def main() -> None:
    """Start the main bot cycle."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex('^(Manage database|/database)$'),
                database,
            ),
            MessageHandler(filters.Regex('^(Start|/start)$'), start),
        ],
        states={
            DB: [
                MessageHandler(
                    ~filters.Regex('^(/end|Manage database|/database)$'),
                    invalid_input,
                ),
            ],
            DB_MANAGE: [
                MessageHandler(
                    filters.Regex(
                        '^(Create database|Delete database|Cancel)$',
                    ),
                    database_manage,
                ),
                MessageHandler(~filters.Regex('^(/end)$'), invalid_input),
            ],
            DB_ACTIVITY: [
                MessageHandler(
                    filters.Regex(
                        r'^(Default|Cancel|([a-zA-Z]|\s|\d){1,50})$',
                    ),
                    database_activity,
                ),
                MessageHandler(
                    ~filters.Regex('^(/end)$'),
                    partial(
                        invalid_input,
                        extra_message=(
                            'Use only letters, digits and space characters'
                        ),
                    ),
                ),
            ],
            MAIN: [
                MessageHandler(
                    filters.Regex(
                        r'^(Status|Reminder(:\s(On|Off))?|Graph|'
                        r'Add record(\s\d{2}.\d{2}.\d{4}\s\d{2}:\d{2})?)$',
                    ),
                    main_messages,
                ),
                MessageHandler(
                    ~filters.Regex('^(/end|Manage database|/database)$'),
                    partial(
                        invalid_input,
                        extra_message=(
                            'Manual record format:\n'
                            '`Add record 01.01.2000 10:00`\n'
                        ),
                    ),
                ),
            ],
            REMINDER: [
                MessageHandler(
                    filters.Regex(r'^(Set(\s\d{1,2})?|Unset|Cancel)$'),
                    reminder_manage,
                ),
                MessageHandler(
                    ~filters.Regex('^(/end|Manage database|/database)$'),
                    invalid_input,
                ),
            ],
        },
        fallbacks=[
            CommandHandler('end', end),
            MessageHandler(
                filters.Regex('^(Manage database|/database)$'),
                database,
            ),
        ],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('end', end))
    application.add_handler(
        MessageHandler(
            filters.ALL,
            partial(invalid_input, keyboard_markup=ReplyMarkups.end),
        ),
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
