import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, Filters

TELEGRAM_BOT_TOKEN = "TG-BOT-API-KEY"

#to go state by state
STATE_WAIT_USERNAME = 0
STATE_WAIT_PASSWORD = 1
STATE_WAIT_SENDER_NAME = 2
STATE_WAIT_PHONE_NUMBER = 3
STATE_WAIT_MESSAGE = 4
STATE_WAIT_CONTACTS = 5

user_states = {}

#The used API that includes many security vulnerability and not acceptable to law.
def send_sms(username, password, sender_name, number, message):
    string = f"""
    <request>
        <authentication>
            <username>{username}</username>
            <password>{password}</password>
        </authentication>
        <order>
            <sender>{sender_name}</sender>
            <sendDateTime></sendDateTime>
            <message>
                <text>{message}</text>
                <receipents>
                    <number>{number}</number>
                </receipents>
            </message>
        </order>
    </request>"""
    
    r = requests.post("http://api.iletimerkezi.com/v1/send-sms", data={'data': string})
    return r.status_code, r.reason

#introduce commands and get username, jump to next state
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_states[user_id] = STATE_WAIT_USERNAME
    update.message.reply_text(
        "Available commands:\n"
        "/start - Start the bot\n"
        "/newmessage - Start a new message\n"
        "/forgetme - Forget the saved credentials and stop the current process\n\n"
        "Please enter your username:"
    )

def new_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in user_states or user_states[user_id] != STATE_WAIT_CONTACTS:
        update.message.reply_text("Please send /start to initiate the process.")
        return

    user_states[user_id] = STATE_WAIT_MESSAGE
    update.message.reply_text("Please enter a new message to send.")

def forget_me(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in user_states:
        del user_states[user_id]

    if "username" in context.user_data:
        del context.user_data["username"]
    if "password" in context.user_data:
        del context.user_data["password"]
    if "sender_name" in context.user_data:
        del context.user_data["sender_name"]
    if "message" in context.user_data:
        del context.user_data["message"]

    update.message.reply_text("Your credentials have been removed, and the current process is stopped.")

def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in user_states:
        start(update, context)
        return

    state = user_states[user_id]
    #decide as the message pattern
    if state == STATE_WAIT_USERNAME:
        context.user_data["username"] = text
        user_states[user_id] = STATE_WAIT_PASSWORD
        update.message.reply_text("Please enter your password.")
    elif state == STATE_WAIT_PASSWORD:
        context.user_data["password"] = text
        user_states[user_id] = STATE_WAIT_SENDER_NAME
        update.message.reply_text("Please enter your sender name.")
    elif state == STATE_WAIT_SENDER_NAME:
        context.user_data["sender_name"] = text
        user_states[user_id] = STATE_WAIT_PHONE_NUMBER
        update.message.reply_text("Please enter a phone number for testing.")
    elif state == STATE_WAIT_PHONE_NUMBER:
        test_number = text
        status_code, reason = send_sms(
            context.user_data["username"],
            context.user_data["password"],
            context.user_data["sender_name"],
            test_number,
            "Test"
        )
        #test message for first time login. after that it loops to new contact or new messages
        if status_code == 200:
            user_states[user_id] = STATE_WAIT_MESSAGE
            update.message.reply_text("Credentials saved. Please enter your message.")
        else:
            del user_states[user_id]
            del context.user_data["username"]
            del context.user_data["password"]
            del context.user_data["sender_name"]
            update.message.reply_text(f"Invalid credentials. Status code: {status_code}, Reason: {reason}")
    elif state == STATE_WAIT_MESSAGE:
        context.user_data["message"] = text
        user_states[user_id] = STATE_WAIT_CONTACTS
        update.message.reply_text("Please send contacts (as attachments).")

def handle_contact(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if user_id not in user_states or user_states[user_id] != STATE_WAIT_CONTACTS:
        update.message.reply_text("Please send /start to initiate the process.")
        return

    phone_number = update.message.contact.phone_number
    status_code, reason = send_sms(
        context.user_data["username"],
        context.user_data["password"],
        context.user_data["sender_name"],
        phone_number,
        context.user_data["message"]
    )

    if status_code == 200:
        update.message.reply_text(f"Message sent to {phone_number}.")
    else:
        update.message.reply_text(f"Failed to send message to {phone_number}. Status code: {status_code}, Reason: {reason}")

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("newmessage", new_message))
    dp.add_handler(CommandHandler("forgetme", forget_me))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(MessageHandler(Filters.contact, handle_contact))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

