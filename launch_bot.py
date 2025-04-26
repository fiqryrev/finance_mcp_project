#!/usr/bin/env python3
"""
Launch script for the MCP Financial Document Bot
This script handles the initial setup and starts the Telegram bot
"""

import os
import sys
import logging
import time
from dotenv import load_dotenv

def check_environment():
    """Check if environment is properly set up"""
    # Load environment variables
    load_dotenv()
    
    # Check for required variables
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'GOOGLE_APPLICATION_CREDENTIALS',
        'PROJECT_ID',
        'MODEL_ID'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in a .env file. See .env.template for an example.")
        return False
    
    # Check if Google credentials file exists
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not os.path.exists(credentials_path):
        print(f"❌ Error: Google credentials file not found at {credentials_path}")
        print("Please ensure your credentials file is in the correct location.")
        return False
    
    return True

def setup_logging():
    """Configure logging for the application"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully")
    return logger

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import telegram
        import vertexai
        import PIL
        import pandas
        import matplotlib
        return True
    except ImportError as e:
        print(f"❌ Error: Missing required dependency: {e}")
        print("Please install all dependencies with: pip install -r requirements.txt")
        return False

def main():
    """Main launch function"""
    print("🤖 MCP Financial Document Bot - Startup")
    print("=======================================")
    
    # Check environment and dependencies
    if not check_environment() or not check_dependencies():
        sys.exit(1)
    
    # Set up logging
    logger = setup_logging()
    
    try:
        # Import the actual bot code only after checks pass
        from main import main as start_bot
        
        logger.info("Starting the bot...")
        print("\n✅ Environment checks passed. Starting the bot...")
        print("Press Ctrl+C to stop the bot")
        
        # Start the bot
        start_bot()
        
    except Exception as e:
        logger.error(f"Error starting the bot: {str(e)}", exc_info=True)
        print(f"\n❌ Error starting the bot: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user. Goodbye!")
        sys.exit(0)