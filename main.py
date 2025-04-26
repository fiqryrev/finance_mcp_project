#!/usr/bin/env python3
"""
MCP Financial Bot for Telegram
"""
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config.secrets import TELEGRAM_TOKEN
from bot.handlers import (
    start_handler,
    help_handler,
    report_handler,
    analyze_handler,
    photo_handler,
    document_handler,
    callback_query_handler
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def main():
    """Initialize and start the Telegram bot"""
    # Create application
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("report", report_handler))
    application.add_handler(CommandHandler("analyze", analyze_handler))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    
    # Add callback query handler for inline keyboards
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Log that the bot is starting
    logger.info("Starting bot...")
    
    # Start the Bot
    application.run_polling()
    
if __name__ == "__main__":
    main()