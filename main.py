from telegram.ext import (Updater, CommandHandler, ConversationHandler, MessageHandler,
                          Filters, CallbackContext)
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from data_source import DataSource
import os
import threading
import time
import datetime

ADD_REMINDER_TEXT = 'Add a reminder ⏰'
INTERVAL = 30

TOKEN = os.getenv("BOT_TOKEN")
ENTER_MESSAGE, ENTER_TIME = range(2)
dataSource = DataSource(os.environ.get("DATABASE_URL"))


def start_handler(update, context):
    update.message.reply_text("Hello, creator!", reply_markup=add_reminder_button())


def add_reminder_button():
    keyboard = [[KeyboardButton(ADD_REMINDER_TEXT)]]
    return ReplyKeyboardMarkup(keyboard)


def add_reminder_handler(update: Update, context: CallbackContext):
    update.message.reply_text("Please enter a message of the reminder:")
    return ENTER_MESSAGE


def enter_message_handler(update: Update, context: CallbackContext):
    update.message.reply_text("Please enter a time when bot should remind:")
    context.user_data["message_text"] = update.message.text
    return ENTER_TIME


def enter_time_handler(update: Update, context: CallbackContext):
    message_text = context.user_data["message_text"]
    time = datetime.datetime.strptime(update.message.text, "%d/%m/%Y %H:%M")
    message_data = dataSource.create_reminder(update.message.chat_id, message_text, time)
    update.message.reply_text("Your reminder: " + message_data.__repr__())
    return ConversationHandler.END


def start_check_reminders_task():
    thread = threading.Thread(target=check_reminders, args=())
    thread.daemon = True
    thread.start()


def check_reminders():
    while True:
        for reminder_data in dataSource.get_all_reminders():
            if reminder_data.should_be_fired():
                dataSource.fire_reminder(reminder_data.reminder_id)
                updater.bot.send_message(reminder_data.chat_id, reminder_data.message)
        time.sleep(INTERVAL)

def echo(update, context):
    reply_message = update.message.text.upper()
    context.bot.send_message(chat_id=update.effective_chat.id, text=reply_message)


if __name__ == '__main__':
    updater = Updater(TOKEN, use_context=True)
    updater.dispatcher.add_handler(CommandHandler("start", start_handler))
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(ADD_REMINDER_TEXT), add_reminder_handler)],
        states={
            ENTER_MESSAGE: [MessageHandler(Filters.all, enter_message_handler)],
            ENTER_TIME: [MessageHandler(Filters.all, enter_time_handler)]
        },
        fallbacks=[],
    )
    echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
    updater.dispatcher.add_handler(conv_handler)
    updater.dispatcher.add_handler(echo_handler)
    dataSource.create_tables()
    updater.start_polling()
    start_check_reminders_task()
