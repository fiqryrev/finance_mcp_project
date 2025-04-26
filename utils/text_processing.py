"""
Utility functions for text processing and extraction
"""
import re
import datetime
from typing import Dict, List, Any, Optional

def extract_date(text: str) -> Optional[str]:
    """
    Extract a date from text in various formats
    
    Args:
        text: Text to extract date from
        
    Returns:
        Standardized date string (YYYY-MM-DD) or None if no date found
    """
    # Try various date patterns
    patterns = [
        # YYYY-MM-DD
        r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})',
        # MM/DD/YYYY
        r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})',
        # DD/MM/YYYY
        r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})',
        # Month names
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{1,2})[\s,]*(\d{4})',
        r'(\d{1,2})[\s,]*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]*(\d{4})'
    ]
    
    for pattern in patterns:
        matches = re.search(pattern, text, re.IGNORECASE)
        if matches:
            groups = matches.groups()
            
            # Handle YYYY-MM-DD format
            if len(groups[0]) == 4:
                year, month, day = groups
            
            # Handle MM/DD/YYYY format (common in US)
            elif pattern == r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})' and len(groups) == 3:
                month, day, year = groups
            
            # Handle DD/MM/YYYY format (common in Europe)
            elif pattern == r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})' and len(groups) == 3:
                day, month, year = groups
            
            # Handle month names
            elif 'Jan|Feb' in pattern and len(groups) == 3:
                # Month first format
                if len(groups[0]) <= 3:
                    month_name, day, year = groups
                    month = convert_month_name_to_number(month_name)
                # Day first format
                else:
                    day, month_name, year = groups
                    month = convert_month_name_to_number(month_name)
                    
            else:
                # If we can't determine the format, skip this match
                continue
            
            # Convert to integers
            try:
                year = int(year)
                month = int(month)
                day = int(day)
                
                # Validate date
                if 1 <= month <= 12 and 1 <= day <= 31:
                    # Handle two-digit years
                    if year < 100:
                        current_year = datetime.datetime.now().year
                        century = current_year // 100 * 100
                        year = century + year
                    
                    # Format as YYYY-MM-DD
                    return f"{year:04d}-{month:02d}-{day:02d}"
            except (ValueError, NameError):
                continue
    
    return None

def convert_month_name_to_number(month_name: str) -> int:
    """
    Convert a month name to its number
    
    Args:
        month_name: Month name (Jan, February, etc.)
        
    Returns:
        Month number (1-12)
    """
    month_dict = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }
    
    return month_dict.get(month_name.lower()[:3], 0)

def extract_total_amount(text: str) -> Optional[str]:
    """
    Extract a total amount from text
    
    Args:
        text: Text to extract amount from
        
    Returns:
        Total amount string or None if no amount found
    """
    # Common patterns for total amounts
    patterns = [
        r'total[\s:]*[$€£]?\s*(\d+[.,]\d{2})',
        r'total[\s:]*[$€£]?\s*(\d+)',
        r'amount[\s:]*[$€£]?\s*(\d+[.,]\d{2})',
        r'amount[\s:]*[$€£]?\s*(\d+)',
        r'sum[\s:]*[$€£]?\s*(\d+[.,]\d{2})',
        r'sum[\s:]*[$€£]?\s*(\d+)',
        r'[$€£]\s*(\d+[.,]\d{2})\s*$'  # Amount at the end of a line
    ]
    
    for pattern in patterns:
        matches = re.search(pattern, text, re.IGNORECASE)
        if matches:
            amount = matches.group(1)
            # Standardize the format (replace comma with period for decimal)
            amount = re.sub(r',', '.', amount)
            return amount
    
    return None

def extract_merchant(text: str) -> Optional[str]:
    """
    Extract merchant or vendor name from text
    
    Args:
        text: Text to extract merchant from
        
    Returns:
        Merchant name or None if not found
    """
    # Patterns for merchant identification
    patterns = [
        r'merchant[\s:]*([A-Za-z0-9\s&]+)',
        r'vendor[\s:]*([A-Za-z0-9\s&]+)',
        r'payee[\s:]*([A-Za-z0-9\s&]+)',
        r'store[\s:]*([A-Za-z0-9\s&]+)',
        r'from[\s:]*([A-Za-z0-9\s&]+)'
    ]
    
    # First, try explicit patterns
    for pattern in patterns:
        matches = re.search(pattern, text, re.IGNORECASE)
        if matches:
            merchant = matches.group(1).strip()
            return merchant
    
    # If explicit patterns fail, try to extract the first non-numeric line
    # (often the store name is at the top of receipts)
    lines = text.split('\n')
    for line in lines[:5]:  # Check first 5 lines
        line = line.strip()
        if line and not re.match(r'^[\d\s.,$/\\]+$', line):
            return line
    
    return None

def extract_items(text: str) -> List[Dict[str, str]]:
    """
    Extract items/products from receipt text
    
    Args:
        text: Receipt text
        
    Returns:
        List of item dictionaries with name and price
    """
    items = []
    
    # Look for patterns like:
    # 1. Item name followed by price: "Product name $10.99"
    # 2. Item with quantity: "2 x Product name $21.98"
    # 3. Tabular format: "Product name ... $10.99"
    
    # Try to find a block of lines that likely contains items
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and lines that are likely headers or totals
        if not line or re.search(r'total|subtotal|tax|amount|sum', line, re.IGNORECASE):
            continue
        
        # Pattern 1: Product name followed by price at the end
        pattern1 = r'([\w\s\-&\'\"]+)\s+\$?\s?(\d+[.,]\d{2})$'
        match1 = re.search(pattern1, line)
        
        # Pattern 2: Product with quantity
        pattern2 = r'(\d+)\s*[xX]\s*([\w\s\-&\'\"]+)\s+\$?\s?(\d+[.,]\d{2})'
        match2 = re.search(pattern2, line)
        
        # Pattern 3: Tabular format with dots or spaces
        pattern3 = r'([\w\s\-&\'\"]+)\.{2,}|[\s]{2,}\$?\s?(\d+[.,]\d{2})'
        match3 = re.search(pattern3, line)
        
        if match1:
            # Simple product name and price
            name = match1.group(1).strip()
            price = match1.group(2).strip()
            items.append({
                'name': name,
                'price': price,
                'quantity': '1'
            })
        elif match2:
            # Product with quantity
            quantity = match2.group(1).strip()
            name = match2.group(2).strip()
            price = match2.group(3).strip()
            items.append({
                'name': name,
                'price': price,
                'quantity': quantity
            })
        elif match3:
            # Tabular format
            try:
                name = match3.group(1).strip()
                price = match3.group(2).strip()
                items.append({
                    'name': name,
                    'price': price,
                    'quantity': '1'
                })
            except (IndexError, AttributeError):
                # Handle case where regex doesn't capture all groups
                pass
        else:
            # Try a more generic pattern
            price_match = re.search(r'\$?\s?(\d+[.,]\d{2})', line)
            if price_match:
                # If we find a price, assume everything before it is the item name
                price = price_match.group(1)
                name = line[:line.rfind(price)].strip()
                if name:
                    items.append({
                        'name': name,
                        'price': price,
                        'quantity': '1'
                    })
    
    return items

def extract_tax(text: str) -> Optional[str]:
    """
    Extract tax amount from text
    
    Args:
        text: Text to extract tax from
        
    Returns:
        Tax amount string or None if not found
    """
    # Common patterns for tax amounts
    patterns = [
        r'tax[\s:]*[$€£]?\s*(\d+[.,]\d{2})',
        r'vat[\s:]*[$€£]?\s*(\d+[.,]\d{2})',
        r'gst[\s:]*[$€£]?\s*(\d+[.,]\d{2})',
        r'hst[\s:]*[$€£]?\s*(\d+[.,]\d{2})',
        r'sales tax[\s:]*[$€£]?\s*(\d+[.,]\d{2})'
    ]
    
    for pattern in patterns:
        matches = re.search(pattern, text, re.IGNORECASE)
        if matches:
            tax = matches.group(1)
            # Standardize the format
            tax = re.sub(r',', '.', tax)
            return tax
    
    return None

def extract_payment_method(text: str) -> Optional[str]:
    """
    Extract payment method from text
    
    Args:
        text: Text to extract payment method from
        
    Returns:
        Payment method string or None if not found
    """
    # Look for common payment methods
    payment_methods = {
        'credit': 'Credit Card',
        'debit': 'Debit Card',
        'visa': 'Visa',
        'mastercard': 'Mastercard',
        'amex': 'American Express',
        'american express': 'American Express',
        'discover': 'Discover',
        'cash': 'Cash',
        'check': 'Check',
        'cheque': 'Check',
        'paypal': 'PayPal',
        'venmo': 'Venmo',
        'apple pay': 'Apple Pay',
        'google pay': 'Google Pay',
        'samsung pay': 'Samsung Pay'
    }
    
    # Check for payment method mentions
    for keyword, method in payment_methods.items():
        if re.search(r'\b' + keyword + r'\b', text, re.IGNORECASE):
            return method
    
    return None

def categorize_merchant(merchant_name: str) -> str:
    """
    Categorize a merchant based on their name
    
    Args:
        merchant_name: Name of the merchant
        
    Returns:
        Category string
    """
    if not merchant_name:
        return "Uncategorized"
    
    # Lowercase the merchant name for better matching
    merchant_lower = merchant_name.lower()
    
    # Define categories and keywords
    categories = {
        'Groceries': ['grocery', 'market', 'food', 'supermarket', 'mart', 'trader', 'whole foods', 'safeway', 'kroger', 'aldi'],
        'Dining': ['restaurant', 'cafe', 'coffee', 'diner', 'bistro', 'starbucks', 'mcdonalds', 'wendys', 'chipotle', 'taco', 'burger', 'pizza'],
        'Transportation': ['gas', 'fuel', 'auto', 'car', 'uber', 'lyft', 'taxi', 'transport', 'subway', 'metro', 'bus', 'train'],
        'Entertainment': ['cinema', 'movie', 'theater', 'theatre', 'concert', 'event', 'netflix', 'spotify', 'hulu', 'disney+'],
        'Retail': ['store', 'shop', 'mall', 'outlet', 'target', 'walmart', 'costco', 'amazon', 'best buy', 'clothing'],
        'Health': ['pharmacy', 'drug', 'medical', 'doctor', 'clinic', 'hospital', 'cvs', 'walgreens'],
        'Utilities': ['electric', 'water', 'gas', 'power', 'utility', 'phone', 'mobile', 'internet', 'cable', 'service']
    }
    
    # Check each category for keyword matches
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in merchant_lower:
                return category
    
    return "Uncategorized"

def preprocess_text(text: str) -> str:
    """
    Preprocess text for better extraction
    
    Args:
        text: Raw text from OCR
        
    Returns:
        Preprocessed text
    """
    # Convert to lowercase
    text = text.lower()
    
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters that might interfere with parsing
    text = re.sub(r'[^\w\s.,:\-$/\\%&]', '', text)
    
    # Normalize line endings
    text = text.replace('\r', '\n')
    text = re.sub(r'\n+', '\n', text)
    
    return text

def parse_receipt_text(text: str) -> Dict[str, Any]:
    """
    Parse raw receipt text into structured data
    
    Args:
        text: Raw text from OCR
        
    Returns:
        Dictionary with structured receipt data
    """
    # Preprocess the text
    processed_text = preprocess_text(text)
    
    # Extract various fields
    date = extract_date(processed_text)
    merchant = extract_merchant(processed_text)
    total = extract_total_amount(processed_text)
    tax = extract_tax(processed_text)
    payment_method = extract_payment_method(processed_text)
    items = extract_items(processed_text)
    
    # Categorize the merchant
    category = categorize_merchant(merchant)
    
    # Create result dictionary
    result = {
        'date': date,
        'merchant': merchant,
        'total': total,
        'tax': tax,
        'payment_method': payment_method,
        'items': items,
        'category': category
    }
    
    return result