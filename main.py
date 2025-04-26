#!/usr/bin/env python3
"""
MCP Financial Bot for Telegram
"""
import logging
import os
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    filters,
    ConversationHandler
)

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

# Import data management handlers
from bot.data_handlers import (
    my_data_handler,
    delete_data_handler,
    delete_data_range_handler,
    delete_all_data_handler,
    delete_duplicates_handler,
    data_location_handler,
    handle_file_selection,
    handle_date_range_selection,
    handle_delete_confirmation,
    handle_duplicate_selection,
    handle_duplicate_confirmation,
    handle_custom_date_range,
    AWAITING_DELETE_CONFIRMATION,
    AWAITING_DATE_RANGE,
    AWAITING_FILE_SELECTION,
    AWAITING_DUPLICATE_CONFIRMATION
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Set up file logging
file_handler = logging.FileHandler('logs/bot.log')
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

# Get logger
logger = logging.getLogger(__name__)
logger.addHandler(file_handler)

def main():
    """Initialize and start the Telegram bot"""
    # Create application
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("report", report_handler))
    application.add_handler(CommandHandler("analyze", analyze_handler))
    
    # Add data management command handlers
    application.add_handler(CommandHandler("mydata", my_data_handler))
    application.add_handler(CommandHandler("datalocation", data_location_handler))
    
    # Add conversation handlers for data deletion
    
    # Handler for deleting individual files
    delete_data_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("deletedata", delete_data_handler)],
        states={
            AWAITING_FILE_SELECTION: [CallbackQueryHandler(handle_file_selection)],
            AWAITING_DELETE_CONFIRMATION: [CallbackQueryHandler(handle_delete_confirmation)]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
    application.add_handler(delete_data_conv_handler)
    
    # Handler for deleting by date range
    delete_range_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("deletedatarange", delete_data_range_handler)],
        states={
            AWAITING_DATE_RANGE: [
                CallbackQueryHandler(handle_date_range_selection),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_date_range)
            ],
            AWAITING_DELETE_CONFIRMATION: [CallbackQueryHandler(handle_delete_confirmation)]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
    application.add_handler(delete_range_conv_handler)
    
    # Handler for deleting all data
    delete_all_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("deletealldata", delete_all_data_handler)],
        states={
            AWAITING_DELETE_CONFIRMATION: [CallbackQueryHandler(handle_delete_confirmation)]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
    application.add_handler(delete_all_conv_handler)
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    
    # Add callback query handler for inline keyboards
    # Note: Since we're using CallbackQueryHandler in conversation handlers,
    # we need to make sure this general handler doesn't conflict
    # This handler will process callback queries not handled by conversation handlers
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Log that the bot is starting
    logger.info("Starting bot...")
    
    # Start the Bot
    application.run_polling()
    
if __name__ == "__main__":
    main()