import logging
import subprocess
import shlex
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode

load_dotenv()

# Keep basic logging for system errors/warnings, but we'll use print() for the chat interface
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.WARNING)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in .env file!")

allowed_ids_string = os.getenv("ALLOWED_IDS", "")
ALLOWED_IDS = [int(user_id.strip()) for user_id in allowed_ids_string.split(",") if user_id.strip().isdigit()]

if not ALLOWED_IDS:
    raise ValueError("No valid ALLOWED_IDS found in .env file! Please add them.")

bot_started = False

# Helper function to get the best display name
def get_username(user):
    return user.username if user.username else user.first_name

# Send a welcome message when /start is issued
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global bot_started
    bot_started = True  
    user = update.effective_user
    username = get_username(user)
    
    print(f"{username} : {update.message.text}")
    
    reply_html = rf"Hi {user.mention_html()}! Bot initialized and locked to authorized users. Send /bash to run commands."
    reply_plain = f"Hi {user.first_name}! Bot initialized and locked to authorized users. Send /bash to run commands."
    
    print(f"bot : {reply_plain}")
    await update.message.reply_html(reply_html)

# Lock the bot when /stop is issued
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global bot_started
    bot_started = False
    user = update.effective_user
    username = get_username(user)

    print(f"{username} : {update.message.text}")

    reply = "Bot locked. You will not be able to run commands until you send /start again."
    print(f"bot : {reply}")
    await update.message.reply_text(reply)

# Send instructions when /help is issued
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    username = get_username(user)
    
    print(f"{username} : {update.message.text}")
    
    if not bot_started:
        reply = "Please send /start first to unlock the bot."
        print(f"bot : {reply}")
        await update.message.reply_text(reply)
        return
        
    reply = "Use /bash <command> to execute commands securely.\nUse /stop to lock the bot."
    print(f"bot : {reply}")
    await update.message.reply_text(reply)

# Execute bash commands with a 10-second timeout to prevent freezing
async def bash_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    username = get_username(user)
    
    print(f"{username} : {update.message.text}")
    
    if not bot_started:
        reply = "Please send /start first to unlock the bot."
        print(f"bot : {reply}")
        await update.message.reply_text(reply)
        return

    command = update.message.text[6:].strip()
    
    if not command:
        reply = "Please provide a command. Usage: /bash <command>"
        print(f"bot : {reply}")
        await update.message.reply_text("Please provide a command\\. Usage: `/bash <command>`", parse_mode=ParseMode.MARKDOWN_V2)
        return

    try:
        command_args = shlex.split(command)
        subproc = subprocess.run(command_args, capture_output=True, text=True, timeout=10)
        
        stdout_text = subproc.stdout.strip()
        stderr_text = subproc.stderr.strip()
        
        response_msg = ""
        
        if stdout_text:
            response_msg += "Output:\n```bash\n" + stdout_text + "\n```\n"
        
        if stderr_text:
            response_msg += "Errors/Warnings:\n```bash\n" + stderr_text + "\n```\n"
            
        if not stdout_text and not stderr_text:
            response_msg = "Command executed successfully with no output\\."

    except subprocess.TimeoutExpired:
        response_msg = "Error: Command timed out after 10 seconds\\.\n```bash\n" + command + "\n```"
    except FileNotFoundError:
        response_msg = f"Error: Command not found\\.\n```bash\n{command_args[0]}\n```"
    except Exception as e:
        response_msg = f"Exception occurred:\n```bash\n{str(e)}\n```"

    if len(response_msg) > 4000:
        response_msg = response_msg[:4000] + "\n```\n[Output truncated due to length limits]"

    # Print the raw text version to terminal so it's readable
    print(f"bot : \n{response_msg.replace('```bash', '').replace('```', '').replace('\\.', '.')}")
    await update.message.reply_text(response_msg, parse_mode=ParseMode.MARKDOWN_V2)

# Handle regular text messages that aren't commands
async def handle_unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    username = get_username(user)
    
    print(f"{username} : {update.message.text}")
    
    reply = "I only understand /start, /help, /stop, and /bash commands."
    print(f"bot : {reply}")
    await update.message.reply_text(reply)

# Start the bot application and attach handlers
def main() -> None:
    print("Starting Telegram Bot... Waiting for messages.")
    application = Application.builder().token(BOT_TOKEN).build()
    user_only_filter = filters.User(user_id=ALLOWED_IDS)

    application.add_handler(CommandHandler("start", start, filters=user_only_filter))
    application.add_handler(CommandHandler("stop", stop_command, filters=user_only_filter))
    application.add_handler(CommandHandler("help", help_command, filters=user_only_filter))
    application.add_handler(CommandHandler("bash", bash_command, filters=user_only_filter))
    
    # Add a handler for standard text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & user_only_filter, handle_unknown_message))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
