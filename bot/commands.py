"""
Command definitions for the Telegram bot
"""
from typing import Dict, List, Tuple

# Define available commands and their descriptions
COMMANDS = [
    ('start', 'Start the bot and get a welcome message'),
    ('help', 'Show help information and available commands'),
    ('report', 'Generate a financial report'),
    ('analyze', 'Analyze your financial data'),
    ('budget', 'View and manage your budget'),
    ('settings', 'Configure your preferences'),
    ('mydata', 'View a list of your stored documents'),
    ('deletedata', 'Delete a specific document'),
    ('deletedatarange', 'Delete documents in a date range'),
    ('deletealldata', 'Delete all your stored documents'),
    ('deleteduplicates', 'Find and remove duplicate files'),
    ('datalocation', 'View where your data is stored'),
    ('cancel', 'Cancel the current operation')
]

def get_command_list() -> List[Tuple[str, str]]:
    """
    Get the list of available commands
    
    Returns:
        List of (command, description) tuples
    """
    return COMMANDS

def get_command_descriptions() -> Dict[str, str]:
    """
    Get a dictionary of command descriptions
    
    Returns:
        Dictionary mapping command names to descriptions
    """
    return {command: description for command, description in COMMANDS}

def format_commands_for_help() -> str:
    """
    Format commands for help message
    
    Returns:
        Formatted string with commands and descriptions
    """
    command_text = ""
    for command, description in COMMANDS:
        command_text += f"/{command} - {description}\n"
    return command_text

def get_bot_commands_for_telegram() -> List[Tuple[str, str]]:
    """
    Get commands formatted for BotFather's /setcommands
    
    Returns:
        List of (command, description) tuples without the leading slash
    """
    # BotFather expects commands without the leading slash
    return COMMANDS

def register_bot_commands(bot):
    """
    Register command handlers with the bot
    
    Args:
        bot: Telegram bot object
    """
    # This function can be used to programmatically set up command handlers
    from bot.handlers import (
        start_handler, 
        help_handler, 
        report_handler, 
        analyze_handler
    )
    
    from bot.data_handlers import (
        my_data_handler,
        delete_data_handler,
        delete_data_range_handler,
        delete_all_data_handler,
        delete_duplicates_handler,
        data_location_handler
    )
    
    # Map commands to handlers
    command_handlers = {
        'start': start_handler,
        'help': help_handler,
        'report': report_handler,
        'analyze': analyze_handler,
        'mydata': my_data_handler,
        'deletedata': delete_data_handler,
        'deletedatarange': delete_data_range_handler,
        'deletealldata': delete_all_data_handler,
        'deleteduplicates': delete_duplicates_handler,
        'datalocation': data_location_handler,
    }
    
    # Register all command handlers
    for command, handler in command_handlers.items():
        bot.add_handler(command, handler)