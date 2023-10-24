# import matplotlib.pyplot as plt
from decouple import config
from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database import USER_LIMIT, get_user, get_user_count

TELEGRAM_TOKEN = config('TELEGRAM_TOKEN', default='123')

DB, DB_MANAGE = range(2)
MAIN = range(1)

# fig, ax = plt.subplots()
# ax.plot(
#     ['01.01.23', '02.01.23', '04.01.23', '06.01.23', '08.01.23', '10.01.23'],
#     [48, 49, 58, 28, 43, 48],
#     marker='o',
# )
# ax.set_ylabel('Hours')
# ax.set_xlabel('Date')
# plt.savefig('foo.png')

main_reply_markup = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton('Status'),
            KeyboardButton('Update'),
        ],
        [KeyboardButton('Graph')],
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
            [[KeyboardButton('Database')]],
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
        text = 'Database exists. Do you want to delete it?'
        keyboard = [
            [KeyboardButton('Delete database'), KeyboardButton('Cancel')],
        ]
    elif await get_user_count() < USER_LIMIT:
        text = 'Create the database?'
        keyboard = [
            [KeyboardButton('Create database'), KeyboardButton('Cancel')],
        ]
    else:
        await update.effective_message.reply_text(
            "Can't create the database because the quota is over.",
        )
        return await end_conversation(update, context)

    await update.effective_message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
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
    if not db_exists and update.effective_message.text == 'Create database':
        await update.effective_message.reply_text(
            'Database has been created',
            reply_markup=main_reply_markup,
        )
        context.user_data['database_exists'] = True
        return MAIN
    if db_exists and update.effective_message.text == 'Delete database':
        await update.message.reply_text(
            'Database has been deleted',
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data['database_exists'] = False
        await end_conversation(update, context)
    if update.effective_message.text == 'Cancel' and db_exists:
        await update.effective_message.reply_text(
            'What would you like to do?',
            reply_markup=main_reply_markup,
        )
        return MAIN
    await update.effective_message.reply_text(
        'Database was not created',
        reply_markup=ReplyKeyboardRemove(),
    )
    return await end_conversation(update, context)


async def end_conversation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Cancels and ends the conversation."""
    await update.effective_message.reply_text(
        f'Bye, {update.effective_user.username}! To talk again send /start',
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton('Start')]],
            resize_keyboard=True,
            is_persistent=True,
        ),
    )
    return ConversationHandler.END


async def invalid_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Send a message when the command /help is issued."""
    await update.effective_message.reply_text('Invalid input!')


async def main_messages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Echo the user message."""

    match update.effective_message.text:
        case 'Status':
            await update.effective_message.reply_text('Status')
        case 'Update':
            await update.effective_message.reply_text('Update')
        case 'Reminder':
            await update.effective_message.reply_photo('1.png')
        case 'Graph':
            await update.effective_message.reply_photo('1.png')


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    db_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex('^(Database|/database)$'),
                database),
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
                CommandHandler('database', database),
                MessageHandler(
                    filters.Regex('^(Status|Update|Reminder|Graph)$'),
                    main_messages,
                ),
                MessageHandler(~filters.Regex('^(/end)$'), invalid_input),
            ],
        },
        fallbacks=[CommandHandler('end', end_conversation)],
    )
    main_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^(Start|/start)$'), start),
        ],
        states={
            MAIN: [
                MessageHandler(
                    filters.Regex('^(Status|Update|Reminder|Graph)$'),
                    main_messages,
                ),
                MessageHandler(~filters.Regex('^(/end)$'), invalid_input),
            ],
        },
        fallbacks=[
            CommandHandler('end', end_conversation),
            MessageHandler(
                filters.Regex('^(Database|/database)$'),
                database,
            ),
        ],
    )
    application.add_handler(db_conv_handler)
    application.add_handler(main_conv_handler)
    application.add_handler(CommandHandler('end', end_conversation))
    application.add_handler(MessageHandler(filters.ALL, invalid_input))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
