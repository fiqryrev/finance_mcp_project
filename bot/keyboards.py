"""
Custom keyboards for the Telegram bot
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Create the main keyboard for the bot
    
    Returns:
        ReplyKeyboardMarkup for the main menu
    """
    keyboard = [
        [KeyboardButton("📷 Upload Receipt"), KeyboardButton("📊 Generate Report")],
        [KeyboardButton("💡 Analyze Spending"), KeyboardButton("💰 Budget Status")],
        [KeyboardButton("❓ Help")]
    ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_report_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for report options
    
    Returns:
        InlineKeyboardMarkup for report options
    """
    keyboard = [
        [
            InlineKeyboardButton("Daily Report", callback_data="report_daily"),
            InlineKeyboardButton("Weekly Report", callback_data="report_weekly")
        ],
        [
            InlineKeyboardButton("Monthly Report", callback_data="report_monthly"),
            InlineKeyboardButton("Custom Report", callback_data="report_custom")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_analysis_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for analysis options
    
    Returns:
        InlineKeyboardMarkup for analysis options
    """
    keyboard = [
        [
            InlineKeyboardButton("Spending Categories", callback_data="analyze_categories"),
            InlineKeyboardButton("Monthly Trends", callback_data="analyze_trends")
        ],
        [
            InlineKeyboardButton("Top Merchants", callback_data="analyze_merchants"),
            InlineKeyboardButton("Budget Status", callback_data="analyze_budget")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_budget_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for budget options
    
    Returns:
        InlineKeyboardMarkup for budget options
    """
    keyboard = [
        [
            InlineKeyboardButton("View Budget", callback_data="budget_view"),
            InlineKeyboardButton("Set Budget", callback_data="budget_set")
        ],
        [
            InlineKeyboardButton("Budget Categories", callback_data="budget_categories"),
            InlineKeyboardButton("Budget History", callback_data="budget_history")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Create a simple cancel keyboard
    
    Returns:
        InlineKeyboardMarkup with cancel button
    """
    keyboard = [
        [InlineKeyboardButton("Cancel", callback_data="cancel")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_yes_no_keyboard(action: str) -> InlineKeyboardMarkup:
    """
    Create a yes/no keyboard with custom action prefix
    
    Args:
        action: Action prefix for the callback data
        
    Returns:
        InlineKeyboardMarkup with yes/no buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data=f"{action}_yes"),
            InlineKeyboardButton("No", callback_data=f"{action}_no")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_date_range_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for selecting date ranges
    
    Returns:
        InlineKeyboardMarkup for date range options
    """
    keyboard = [
        [
            InlineKeyboardButton("Last 7 days", callback_data="date_range_7"),
            InlineKeyboardButton("Last 30 days", callback_data="date_range_30")
        ],
        [
            InlineKeyboardButton("Last 90 days", callback_data="date_range_90"),
            InlineKeyboardButton("This month", callback_data="date_range_this_month")
        ],
        [
            InlineKeyboardButton("Custom range", callback_data="date_range_custom"),
            InlineKeyboardButton("Cancel", callback_data="cancel")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_category_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for selecting expense categories
    
    Returns:
        InlineKeyboardMarkup for expense categories
    """
    # Using standard expense categories
    keyboard = [
        [
            InlineKeyboardButton("Groceries", callback_data="category_groceries"),
            InlineKeyboardButton("Dining", callback_data="category_dining")
        ],
        [
            InlineKeyboardButton("Entertainment", callback_data="category_entertainment"),
            InlineKeyboardButton("Transportation", callback_data="category_transportation")
        ],
        [
            InlineKeyboardButton("Utilities", callback_data="category_utilities"),
            InlineKeyboardButton("Healthcare", callback_data="category_healthcare")
        ],
        [
            InlineKeyboardButton("Shopping", callback_data="category_shopping"),
            InlineKeyboardButton("Travel", callback_data="category_travel")
        ],
        [
            InlineKeyboardButton("Other", callback_data="category_other"),
            InlineKeyboardButton("Cancel", callback_data="cancel")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)