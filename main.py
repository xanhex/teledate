import io
from datetime import datetime, timedelta
from functools import partial
from math import floor

import matplotlib.pyplot as plt
from decouple import config
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database import (
    RECORD_LIMIT,
    USER_LIMIT,
    Record,
    User,
    create_record,
    create_user,
    delete_records,
    delete_user,
    get_last_user_record,
    get_user,
    get_user_count,
    get_user_records,
)

TELEGRAM_TOKEN = config('TELEGRAM_TOKEN', default='123')

DB, DB_MANAGE = range(2)
MAIN = range(1)

start_reply_markup = ReplyKeyboardMarkup(
    [[KeyboardButton('Start')]],
    resize_keyboard=True,
    is_persistent=True,
)
main_reply_markup = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton('Status'),
            KeyboardButton('Add a record'),
        ],
        [
            KeyboardButton('Graph'),
            KeyboardButton('Reminder'),  # Should get changed accordingly
        ],
    ],
    resize_keyboard=True,
    is_persistent=True,
)


async def db_check(username: str, db_exists: bool):
    if db_exists is False:
        return False
    if db_exists is True:
        return True
    return await get_user(username)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    username = update.effective_user.username
    db_exists = context.user_data['database_exists'] = await db_check(
        username,
        context.user_data.get('database_exists'),
    )
    if db_exists:
        await update.effective_message.reply_text(
            f'Hey, {username}!',
            reply_markup=main_reply_markup,
        )
        return MAIN
    await update.effective_message.reply_text(
        'Database does not exists. Try to set up one?',
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton('Manage database')]],
            resize_keyboard=True,
            is_persistent=True,
        ),
    )
    return ConversationHandler.END


async def database(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    db_exists = context.user_data['database_exists'] = await db_check(
        update.effective_user.username,
        context.user_data.get('database_exists'),
    )
    if db_exists:
        await update.effective_message.reply_text(
            'Database exists. Do you want to delete it?',
            reply_markup=ReplyKeyboardMarkup(
                [
                    [
                        KeyboardButton('Delete database'),
                        KeyboardButton('Cancel'),
                    ],
                ],
                resize_keyboard=True,
                is_persistent=True,
            ),
        )
        return DB_MANAGE
    if await get_user_count() >= USER_LIMIT:
        return await end_conversation(
            update,
            context,
            reply_text="Can't create the database because the quota is over.",
            reply_markup=start_reply_markup,
        )
    await update.effective_message.reply_text(
        'Create the database?',
        reply_markup=ReplyKeyboardMarkup(
            [
                [
                    KeyboardButton('Create database'),
                    KeyboardButton('Cancel'),
                ],
            ],
            resize_keyboard=True,
            is_persistent=True,
        ),
    )
    return DB_MANAGE


async def database_manage(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Send a message when the command /start is issued."""
    db_exists = context.user_data.get('database_exists')
    # Database exists
    if update.effective_message.text == 'Cancel' and db_exists:
        await update.effective_message.reply_text(
            'Deletion was canceled',
            reply_markup=main_reply_markup,
        )
        return MAIN
    if db_exists and update.effective_message.text == 'Delete database':
        db_del = await delete_user(update.effective_user.username)
        if not db_del:
            return await end_conversation(
                update,
                context,
                reply_text="Can't delete database",
                reply_markup=start_reply_markup,
            )
        context.user_data['database_exists'] = False
        return await end_conversation(
            update,
            context,
            reply_text='Database has been deleted',
            reply_markup=start_reply_markup,
        )
    # Database doesn't exists
    if not db_exists and update.effective_message.text == 'Create database':
        user_created = await create_user(update.effective_user.username)
        if not isinstance(user_created, User):
            return await end_conversation(
                update,
                context,
                reply_text="Can't create database",
                reply_markup=start_reply_markup,
            )
        await update.effective_message.reply_text(
            'Database has been created',
            reply_markup=main_reply_markup,
        )
        context.user_data['database_exists'] = True
        return MAIN
    return await end_conversation(
        update,
        context,
        reply_text='Database was not created',
        reply_markup=start_reply_markup,
    )


async def end_conversation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    reply_text: str = 'Bye! To talk again send /start',
    reply_markup: ReplyKeyboardMarkup = start_reply_markup,
) -> int:
    """Cancels and ends the conversation."""
    await update.effective_message.reply_text(
        reply_text,
        reply_markup=reply_markup,
    )
    return ConversationHandler.END


async def invalid_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    keyboard_markup: ReplyKeyboardMarkup = None,
) -> None:
    """Send a message when the command /help is issued."""
    if keyboard_markup:
        await update.effective_message.reply_text(
            'Invalid input!',
            reply_markup=keyboard_markup,
        )
    else:
        await update.effective_message.reply_text('Invalid input!')


async def main_messages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Echo the user message."""
    username = update.effective_user.username
    match update.effective_message.text:
        case 'Status':
            text = await get_status(username)
        case 'Add a record':
            text = await add_record(username)
        case 'Reminder':
            text = await set_reminder(username)
        case 'Graph':
            graph = await get_graph(username)
            if not isinstance(graph, str):
                await update.effective_message.reply_photo(
                    graph,
                    reply_markup=main_reply_markup,
                )
                return
            text = graph
    await update.effective_message.reply_text(
        text,
        reply_markup=main_reply_markup,
    )
    return


async def set_reminder(username: str) -> str:
    """Schedule the reminder task for the user."""
    return 'Reminder is set'


async def get_graph(username: str):
    records = await get_user_records(username)
    if not records:
        return 'No records have been created'
    x = []
    y = []
    for record in records:
        conv_record = record.date + timedelta(hours=3)
        x.append(conv_record.strftime('%d.%m'))
        if not y:
            prev_date = conv_record - timedelta(hours=48)
        y.append(floor((conv_record - prev_date).total_seconds() / 60 / 60))
        prev_date = conv_record
    fig, ax = plt.subplots()
    ax.plot(
        x,
        y,
        marker='o',
    )
    ax.set_ylabel('Hours')
    ax.set_xlabel('Date')
    with io.BytesIO() as buf:
        fig.savefig(buf)
        return buf.getvalue()


async def clear_old_record(username: str):
    records = await get_user_records(username)
    if len(records.all()) > RECORD_LIMIT:
        deleted = await delete_records(username, count=RECORD_LIMIT // 3)
        if deleted:
            return 'Old records have been removed.'
    return None


async def add_record(username: str):
    extra_message = await clear_old_record(username)
    record = await create_record(username)
    if not isinstance(record, Record):
        return "Can't create a record"
    # Moscow Time (UTC+3)
    return (
        (f'{extra_message}\n' if extra_message else '')
        + f"{(record.date + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M:%S')}"
    )


async def get_status(username: str):
    record = await get_last_user_record(username)
    if (not isinstance(record, Record)) or (
        isinstance(record, Record) and not isinstance(record.date, datetime)
    ):
        return 'No record has been created yet'
    # Moscow Time (UTC+3)
    record_dt = record.date + timedelta(hours=3)
    record_info = record_dt.strftime('%d.%m.%Y %H:%M:%S')
    diff_dt = datetime.today() - record_dt
    hours_diff = floor(diff_dt.total_seconds() / 60 / 60) - diff_dt.days * 24
    min_diff = floor(diff_dt.total_seconds() / 60) - hours_diff * 60
    sec_diff = round(diff_dt.total_seconds()) - min_diff * 60
    days_case = 'day' if diff_dt.days == 1 else 'days'
    hours_case = 'hour' if hours_diff == 1 else 'hours'
    if diff_dt.days:
        return (
            f'• {record_info}\n'
            f'• {diff_dt.days} {days_case} {hours_diff} {hours_case} ago'
        )
    if hours_diff:
        return (
            f'• {record_info}\n'
            f'• {hours_diff} {hours_case} {min_diff} min ago'
        )
    if min_diff:
        return f'• {record_info}\n' f'• {min_diff} min {sec_diff} sec ago'
    return f'• {record_info}\n' f'• {sec_diff} sec ago'


def main() -> None:
    """Start the bot."""
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
            DB: [MessageHandler(~filters.Regex('^(/end)$'), invalid_input)],
            DB_MANAGE: [
                MessageHandler(
                    filters.Regex(
                        '^(Create database|Delete database|Cancel)$',
                    ),
                    database_manage,
                ),
                MessageHandler(~filters.Regex('^(/end)$'), invalid_input),
            ],
            MAIN: [
                MessageHandler(
                    filters.Regex('^(Status|Add a record|Reminder|Graph)$'),
                    main_messages,
                ),
                MessageHandler(
                    ~filters.Regex('^(/end|Manage database|/database)$'),
                    invalid_input,
                ),
            ],
        },
        fallbacks=[
            CommandHandler('end', end_conversation),
            MessageHandler(
                filters.Regex('^(Manage database|/database)$'),
                database,
            ),
        ],
    )

    application.add_handler(conv_handler)
    application.add_handler(
        MessageHandler(
            filters.ALL,
            partial(invalid_input, keyboard_markup=start_reply_markup),
        ),
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
