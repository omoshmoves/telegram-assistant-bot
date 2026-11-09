import logging
import ast
import operator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "9271979456:AAF1WCHgaTM6xXEyH_iVjnBWjyvIoEyTrwc"

# Dictionary to track monitoring state per chat/user
monitoring_states = {}
message_logs = {}

# Safe evaluator for math expressions to prevent security risks
allowed_operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}

def safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    elif isinstance(node, ast.BinOp) and type(node.op) in allowed_operators:
        return allowed_operators[type(node.op)](safe_eval(node.left), safe_eval(node.right))
    elif isinstance(node, ast.UnaryOp) and type(node.op) in allowed_operators:
        return allowed_operators[type(node.op)](safe_eval(node.operand))
    else:
        raise TypeError("Unsupported or unsafe mathematical operation.")

def calculate_math(expression: str):
    try:
        node = ast.parse(expression, mode='eval')
        return safe_eval(node.body)
    except Exception as e:
        return f"Error: Invalid mathematical expression ({e})"

# 1. Start Command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Toggle Message Monitoring", callback_data="toggle_monitor")],
        [InlineKeyboardButton("📋 View Summary", callback_data="get_summary")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 **Assistant Bot Online!**\n\n"
        "I can monitor your chat messages, provide summaries, and compute math problems.\n\n"
        "• **Math:** Send `/math 25 * (4 + 2)`\n"
        "• **Monitoring:** Use the buttons below to control message logging.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# 2. Button Callback Handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "toggle_monitor":
        current_state = monitoring_states.get(chat_id, False)
        monitoring_states[chat_id] = not current_state
        status = "ENABLED 🟢" if monitoring_states[chat_id] else "DISABLED 🔴"
        await query.edit_message_text(f"📊 Message monitoring is now **{status}**.", parse_mode="Markdown")
    
    elif query.data == "get_summary":
        logs = message_logs.get(chat_id, [])
        if not logs:
            await query.edit_message_text("📋 No messages recorded yet while monitoring was active.")
        else:
            summary_text = f"📋 **Chat Summary ({len(logs)} messages logged):**\n\n" + "\n".join([f"- {msg}" for msg in logs[-10:]])
            await query.edit_message_text(summary_text, parse_mode="Markdown")

# 3. Math Command Handler (e.g., /math 150 / 3 + 20)
async def math_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Please provide an expression. Example: `/math 45 * 2 + 10`", parse_mode="Markdown")
        return
    
    expression = " ".join(context.args)
    result = calculate_math(expression)
    await update.message.reply_text(f"🔢 **Expression:** `{expression}`\n✅ **Result:** `{result}`", parse_mode="Markdown")

# 4. General Message Monitor & Handler
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text

    # If monitoring is active for this chat, save the message
    if monitoring_states.get(chat_id, False):
        if chat_id not in message_logs:
            message_logs[chat_id] = []
        message_logs[chat_id].append(text)
        
        # Optional: React or give a quiet confirmation
        logger.info(f"Monitored message in chat {chat_id}: {text}")
    
    # Regular fallback response if not a command
    await update.message.reply_text(f"I saw: *{text}*\n(Type `/math <expression>` to calculate numbers, or use `/start` for options).", parse_mode="Markdown")

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("math", math_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    print("🚀 Bot with Monitoring & Math capabilities is running...")
    app.run_polling()