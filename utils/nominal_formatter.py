"""
Utility for formatting nominal values into international number format
"""
import re

class NominalFormatter:
    """
    A class for formatting nominal values into international number format
    with comma (,) as thousand separator and period (.) as decimal separator.
    """
    
    @staticmethod
    def format_nominal_to_international_format(nominal):
        """
        Formats a nominal string to international numbering system format.
        Uses comma (,) as thousand separator and period (.) as decimal separator.
        
        Args:
            nominal (str): The nominal string to format
            
        Returns:
            str: The formatted nominal string in international format
        """
        # Handle empty input
        if not nominal or nominal.strip() == '':
            return ''
        
        # Check for negative sign before cleaning
        is_negative = '-' in nominal
        
        # Handle scientific notation first
        if 'e' in nominal.lower() or 'E' in nominal:
            try:
                # Convert scientific notation to float directly
                num = float(nominal)
                # Format with 2 decimal places and add thousand separators
                formatted = f"{num:.2f}"
                parts = formatted.split('.')
                parts[0] = re.sub(r'\B(?=(\d{3})+(?!\d))', ',', parts[0])
                return '.'.join(parts)
            except ValueError:
                # Not valid scientific notation, continue with regular parsing
                pass
        
        # Clean the string keeping only digits, period, comma, and minus sign
        cleaned = re.sub(r'[^\d.,-]', '', nominal)
        
        # Handle negative sign - remove temporarily and add back later
        if cleaned.startswith('-'):
            cleaned = cleaned[1:]
            is_negative = True
        
        # Determine if the input uses period as decimal or thousand separator
        using_period_as_decimal = False
        using_comma_as_decimal = False
        
        # Check pattern like "1,000.00" (period is decimal)
        if re.search(r'\d+,\d{3}.*\.\d+', nominal):
            using_period_as_decimal = True
        # Check pattern like "1.000,00" (comma is decimal)
        elif re.search(r'\d+\.\d{3}.*,\d+', nominal):
            using_comma_as_decimal = True
        # If format isn't clearly identified, make a best guess
        else:
            # Count periods and commas
            period_count = cleaned.count('.')
            comma_count = cleaned.count(',')
            
            if period_count > 0 and comma_count > 0:
                # If both separators exist, last one is likely decimal
                last_period_index = cleaned.rfind('.')
                last_comma_index = cleaned.rfind(',')
                
                using_period_as_decimal = last_period_index > last_comma_index
                using_comma_as_decimal = last_comma_index > last_period_index
            elif period_count > 0:
                # Check if period is used as thousands (e.g., 1.000)
                if re.search(r'\d+\.\d{3}', cleaned) and not re.search(r'\d+\.\d{1,2}$', cleaned):
                    using_comma_as_decimal = True
                else:
                    using_period_as_decimal = True
            elif comma_count > 0:
                # Check if comma is used as thousands (e.g., 1,000)
                if re.search(r'\d+,\d{3}', cleaned) and not re.search(r'\d+,\d{1,2}$', cleaned):
                    using_period_as_decimal = True
                else:
                    using_comma_as_decimal = True
            else:
                # No separators found
                using_period_as_decimal = True  # Default to period as decimal
        
        # Handle multiple decimals - keep only the last one
        if using_period_as_decimal and cleaned.count('.') > 1:
            # Keep only the last period as decimal
            last_period = cleaned.rfind('.')
            cleaned = cleaned[:last_period].replace('.', '') + cleaned[last_period:]
        
        if using_comma_as_decimal and cleaned.count(',') > 1:
            # Keep only the last comma as decimal
            last_comma = cleaned.rfind(',')
            cleaned = cleaned[:last_comma].replace(',', '') + cleaned[last_comma:]
        
        # Convert to a standard format first (using dot as decimal)
        standardized = cleaned
        
        if using_comma_as_decimal:
            # Replace dots with empty string (they're thousand separators)
            standardized = standardized.replace('.', '')
            # Replace comma with dot for decimal
            standardized = standardized.replace(',', '.')
        else:
            # Remove all commas (they're thousand separators)
            standardized = standardized.replace(',', '')
        
        # Convert to float
        try:
            num = float(standardized)
            if is_negative:
                num = -num
        except ValueError:
            return '0.00'  # Handle cases where parsing fails
        
        # Format with 2 decimal places
        formatted = f"{num:.2f}"
        
        # Add commas as thousand separators
        parts = formatted.split('.')
        parts[0] = re.sub(r'\B(?=(\d{3})+(?!\d))', ',', parts[0])
        
        return '.'.join(parts)
    
    @staticmethod
    def format_all_nominal_fields(data_dict, nominal_fields=None):
        """
        Format all nominal fields in a dictionary to international format
        
        Args:
            data_dict (dict): Dictionary containing data with nominal fields
            nominal_fields (list): List of field names that should be formatted as nominal values
                                  If None, uses default list of common nominal field names
        
        Returns:
            dict: Dictionary with all nominal values formatted
        """
        # Default nominal fields to check if none provided
        if nominal_fields is None:
            nominal_fields = [
                'price', 'amount', 'total', 'subtotal', 'tax', 'discount',
                'grand_total', 'shipping', 'fee', 'cost', 'value', 'rate',
                'balance', 'payment', 'due', 'paid'
            ]
        
        # Create a copy of the input dictionary
        formatted_dict = data_dict.copy()
        
        # Recursive function to process nested dictionaries and lists
        def process_item(item):
            if isinstance(item, dict):
                # Process dictionary
                for key, value in item.items():
                    if isinstance(value, (dict, list)):
                        # Recursively process nested structures
                        item[key] = process_item(value)
                    elif isinstance(value, str) and any(nominal_field in key.lower() for nominal_field in nominal_fields):
                        # Format value if key contains a nominal field name
                        item[key] = NominalFormatter.format_nominal_to_international_format(value)
                return item
            elif isinstance(item, list):
                # Process list
                return [process_item(element) for element in item]
            else:
                # Return non-container items unchanged
                return item
        
        # Process the dictionary
        return process_item(formatted_dict)