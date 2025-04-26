"""
Utility functions for formatting responses and data for the Telegram bot
"""
import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

def format_currency(amount: str) -> str:
    """
    Format a numeric amount as currency
    
    Args:
        amount: Amount as string or float
        
    Returns:
        Formatted currency string
    """
    try:
        # Convert to float
        value = float(amount.replace('$', '').replace(',', '').strip())
        # Format with 2 decimal places and comma separator
        return f"${value:,.2f}"
    except (ValueError, AttributeError):
        return amount

def format_date(date_str: str, output_format: str = "%Y-%m-%d") -> str:
    """
    Format a date string into a specified format
    
    Args:
        date_str: Date string in ISO format (YYYY-MM-DD)
        output_format: Desired output format
        
    Returns:
        Formatted date string
    """
    try:
        # Parse the date string
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        # Format according to output_format
        return date_obj.strftime(output_format)
    except (ValueError, TypeError):
        return date_str

def format_receipt_for_telegram(receipt_data: Dict[str, Any]) -> str:
    """
    Format receipt data for display in Telegram
    
    Args:
        receipt_data: Dictionary with receipt information
        
    Returns:
        Formatted string for Telegram message
    """
    # Extract fields with defaults
    date = receipt_data.get('date', 'Not detected')
    merchant = receipt_data.get('merchant', 'Not detected')
    total = receipt_data.get('total', 'Not detected')
    tax = receipt_data.get('tax', 'Not detected')
    payment_method = receipt_data.get('payment_method', 'Not detected')
    category = receipt_data.get('category', 'Uncategorized')
    
    # Format currency values
    if total and total != 'Not detected':
        total = format_currency(total)
    if tax and tax != 'Not detected':
        tax = format_currency(tax)
    
    # Format date
    if date and date != 'Not detected':
        date = format_date(date, "%B %d, %Y")
    
    # Create the formatted message
    message = [
        "📝 *Receipt Details*",
        f"📅 *Date:* {date}",
        f"🏪 *Merchant:* {merchant}",
        f"🔖 *Category:* {category}",
        f"💰 *Total:* {total}",
        f"💲 *Tax:* {tax}",
        f"💳 *Payment Method:* {payment_method}"
    ]
    
    # Add items if available
    items = receipt_data.get('items', [])
    if items:
        message.append("\n📋 *Items:*")
        for i, item in enumerate(items, 1):
            name = item.get('name', 'Unknown Item')
            price = format_currency(item.get('price', '0.00'))
            quantity = item.get('quantity', '1')
            message.append(f"  {i}. {name} x{quantity} - {price}")
    
    return "\n".join(message)

def format_report_for_telegram(report_data: Dict[str, Any]) -> str:
    """
    Format financial report data for display in Telegram
    
    Args:
        report_data: Dictionary with report information
        
    Returns:
        Formatted string for Telegram message
    """
    # Extract fields
    report_type = report_data.get('report_type', 'Financial')
    period = report_data.get('period', 'Not specified')
    total_expenses = report_data.get('total_expenses', '$0.00')
    
    # Format the message header
    message = [
        f"📊 *{report_type.capitalize()} Report*",
        f"⏱️ *Period:* {period}",
        f"💰 *Total Expenses:* {total_expenses}",
    ]
    
    # Add category breakdown if available
    categories = report_data.get('categories', {})
    if categories:
        message.append("\n📋 *Expenses by Category:*")
        for category, amount in categories.items():
            message.append(f"  • {category}: {amount}")
    
    # Add top merchants if available
    merchants = report_data.get('merchants', {})
    if merchants:
        message.append("\n🏪 *Top Merchants:*")
        for merchant, amount in merchants.items():
            message.append(f"  • {merchant}: {amount}")
    
    # Add insights if available
    insights = report_data.get('insights', [])
    if insights:
        message.append("\n💡 *Insights:*")
        for insight in insights:
            message.append(f"  • {insight}")
    
    # Add link to full report if available
    report_url = report_data.get('report_url')
    if report_url:
        message.append(f"\n🔗 [View Full Report]({report_url})")
    
    return "\n".join(message)

def create_expense_chart(categories: Dict[str, float], title: str = "Expenses by Category") -> bytes:
    """
    Create a pie chart of expenses by category
    
    Args:
        categories: Dictionary mapping categories to amounts
        title: Chart title
        
    Returns:
        PNG image as bytes
    """
    # Convert currency strings to float values
    values = []
    labels = []
    
    for category, amount in categories.items():
        labels.append(category)
        # Convert amount to float if it's a string
        if isinstance(amount, str):
            # Remove currency symbols and commas
            cleaned_amount = amount.replace('$', '').replace(',', '')
            values.append(float(cleaned_amount))
        else:
            values.append(amount)
    
    # Create figure and axis
    plt.figure(figsize=(10, 6))
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    plt.title(title)
    
    # Save the plot to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    
    # Get the image data
    buf.seek(0)
    return buf.getvalue()

def create_expense_trend_chart(data: Dict[str, float], title: str = "Monthly Expenses") -> bytes:
    """
    Create a bar chart of expenses over time
    
    Args:
        data: Dictionary mapping dates to amounts
        title: Chart title
        
    Returns:
        PNG image as bytes
    """
    # Convert data to pandas Series for easier manipulation
    series = pd.Series(data)
    
    # Create figure and axis
    plt.figure(figsize=(12, 6))
    ax = series.plot(kind='bar', color='skyblue')
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel('Amount ($)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Add dollar amounts on top of bars
    for i, v in enumerate(series):
        ax.text(i, v + 0.1, f'${v:.2f}', ha='center')
    
    # Save the plot to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    
    # Get the image data
    buf.seek(0)
    return buf.getvalue()

def format_analysis_for_telegram(analysis_data: Dict[str, Any]) -> str:
    """
    Format financial analysis for display in Telegram
    
    Args:
        analysis_data: Dictionary with analysis information
        
    Returns:
        Formatted string for Telegram message
    """
    # Extract fields
    analysis_type = analysis_data.get('analysis_type', 'Financial')
    analysis_text = analysis_data.get('analysis', 'No analysis available')
    
    # Format the message
    message = [
        f"💡 *{analysis_type.capitalize()} Analysis*",
        f"{analysis_text}"
    ]
    
    # Add recommendations if available
    recommendations = analysis_data.get('recommendations', [])
    if recommendations:
        message.append("\n🔍 *Recommendations:*")
        for recommendation in recommendations:
            message.append(f"  • {recommendation}")
    
    # Add link to visualization if available
    visualization_url = analysis_data.get('visualization_url')
    if visualization_url:
        message.append(f"\n📊 [View Visualization]({visualization_url})")
    
    return "\n".join(message)