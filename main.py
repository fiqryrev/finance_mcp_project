#!/usr/bin/env python3
"""
MCP Financial Bot for Telegram
"""
import logging
from telegram.ext import ApplicationBuilder, CommandHandler

from config.secrets import TELEGRAM_TOKEN
from bot.handlers import start_handler, help_handler, process_document_handler

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def main():
    """Initialize and start the Telegram bot"""
    # Create application
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    
    # Start the Bot
    application.run_polling()
    
if __name__ == "__main__":
    main()
