import logging
import subprocess
import shlex
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters
from telegram.constants import ParseMode

load_dotenv()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in .env file!")

allowed_ids_string = os.getenv("ALLOWED_IDS", "")
ALLOWED_IDS = [int(user_id.strip()) for user_id in allowed_ids_string.split(",") if user_id.strip().isdigit()]

if not ALLOWED_IDS:
    raise ValueError("No valid ALLOWED_IDS found in .env file! Please add them.")

bot_started = False

# Send a welcome message when /start is issued
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global bot_started
    bot_started = True  
    user = update.effective_user
    await update.message.reply_html(rf"Hi {user.mention_html()}! Bot initialized and locked to authorized users. Send /bash to run commands.")

# Send instructions when /help is issued
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not bot_started:
        await update.message.reply_text("Please send /start first to unlock the bot.")
        return
    await update.message.reply_text("Use /bash <command> to execute commands securely.")

# Execute bash commands with a 10-second timeout to prevent freezing
async def bash_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not bot_started:
        await update.message.reply_text("Please send /start first to unlock the bot.")
        return

    command = update.message.text[6:].strip()
    
    if not command:
        await update.message.reply_text("Please provide a command\\. Usage: `/bash <command>`", parse_mode=ParseMode.MARKDOWN_V2)
        return

    try:
        command_args = shlex.split(command)
        # Added timeout=10 to kill the process if it runs longer than 10 seconds
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

    await update.message.reply_text(response_msg, parse_mode=ParseMode.MARKDOWN_V2)

# Start the bot application and attach handlers
def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    user_only_filter = filters.User(user_id=ALLOWED_IDS)

    application.add_handler(CommandHandler("start", start, filters=user_only_filter))
    application.add_handler(CommandHandler("help", help_command, filters=user_only_filter))
    application.add_handler(CommandHandler("bash", bash_command, filters=user_only_filter))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()