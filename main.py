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

from database import (
    USER_LIMIT,
    User,
    create_user,
    delete_user,
    get_user,
    get_user_count,
)

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

start_reply_markup = ReplyKeyboardMarkup(
    [[KeyboardButton('Start')]],
    resize_keyboard=True,
    is_persistent=True,
)
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
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex('^(Manage database|/database)$'), database,
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
                    filters.Regex('^(Status|Update|Reminder|Graph)$'),
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
                filters.Regex('^(Manage database|/database)$'), database,
            ),
        ],
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.ALL, invalid_input))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
