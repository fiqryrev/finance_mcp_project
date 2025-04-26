"""
Telegram bot message handlers
"""
from telegram import Update
from telegram.ext import ContextTypes

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    await update.message.reply_text(
        f"👋 Hello {update.effective_user.first_name}! I'm your financial document assistant. "
        f"Send me a photo of a receipt or invoice, and I'll extract the information and store it."
    )

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    help_text = """
    🤖 *Financial Document Bot Help*
    
    I can help you manage your financial documents. Here's what I can do:
    
    📝 *Commands:*
    /start - Start the bot
    /help - Show this help message
    /report - Generate a financial report
    /settings - Configure your preferences
    
    📸 *Document Processing:*
    Just send me a photo of your receipt or invoice, and I'll extract the information automatically.
    
    📊 *Reports:*
    I can create reports based on your documents. Use /report to generate one.
    """
    await update.message.reply_text(help_text)

async def process_document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document/photo processing."""
    # This will be implemented later
    await update.message.reply_text("Document processing will be implemented soon!")
