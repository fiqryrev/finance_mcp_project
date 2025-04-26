"""
Service for interacting with Google Sheets
"""
import os
import datetime
from typing import Dict, List, Any, Optional, Union
import asyncio
import pandas as pd

# Google API imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.config import SERVICE_ACCOUNT_PATH, SPREADSHEET_ID

class SheetsService:
    """Service for working with Google Sheets"""
    
    def __init__(self, spreadsheet_id: Optional[str] = None):
        """Initialize the Sheets service"""
        self.spreadsheet_id = spreadsheet_id or SPREADSHEET_ID
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        self.service = self._create_sheets_service()
        
        # Define the sheets for different data types
        self.sheets = {
            'receipts': 'Receipts',
            'invoices': 'Invoices',
            'reports': 'Reports',
            'categories': 'Categories'
        }
    
    def _create_sheets_service(self):
        """Create and return a Google Sheets service"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_PATH, scopes=self.scopes
            )
            service = build('sheets', 'v4', credentials=credentials)
            return service
        except Exception as e:
            print(f"Error creating Sheets service: {e}")
            # Return None or raise exception depending on your error handling strategy
            return None
    
    async def save_receipt_data(self, receipt_data: Dict[str, Any]) -> Optional[str]:
        """
        Save receipt data to Google Sheets
        
        Args:
            receipt_data: Dictionary with receipt information
            
        Returns:
            URL to the spreadsheet or None if failed
        """
        # Handle synchronous Google API calls in an async function
        return await asyncio.to_thread(self._save_receipt_data_sync, receipt_data)
    
    def _save_receipt_data_sync(self, receipt_data: Dict[str, Any]) -> Optional[str]:
        """Synchronous version of save_receipt_data for use with asyncio.to_thread"""
        try:
            # Determine if this is a receipt or invoice based on data
            sheet_name = self.sheets['receipts']  # Default to receipts
            if receipt_data.get('document_type') == 'invoice':
                sheet_name = self.sheets['invoices']
            
            # Prepare the data row
            row_data = self._format_receipt_for_sheet(receipt_data)
            
            # Get the next empty row in the sheet
            range_name = f"{sheet_name}!A:A"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            # Calculate the next row index
            values = result.get('values', [])
            next_row = len(values) + 1 if values else 2  # Assuming row 1 is header
            
            # Define the range for the new row
            update_range = f"{sheet_name}!A{next_row}"
            
            # Prepare the values for update
            value_input_option = 'USER_ENTERED'
            value_range_body = {
                'values': [row_data]
            }
            
            # Update the sheet
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=update_range,
                valueInputOption=value_input_option,
                body=value_range_body
            ).execute()
            
            # Return the URL to the spreadsheet
            return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit"
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None
        except Exception as e:
            print(f"Error saving to Google Sheets: {e}")
            return None
    
    def _format_receipt_for_sheet(self, receipt_data: Dict[str, Any]) -> List[Any]:
        """
        Format receipt data for insertion into a spreadsheet
        
        Args:
            receipt_data: Dictionary with receipt information
            
        Returns:
            List of values for a spreadsheet row
        """
        # Extract data with defaults for missing fields
        date = receipt_data.get('date', '')
        merchant = receipt_data.get('merchant', '')
        total = receipt_data.get('total', '')
        subtotal = receipt_data.get('subtotal', '')
        tax = receipt_data.get('tax', '')
        payment_method = receipt_data.get('payment_method', '')
        
        # Format items as a string
        items_str = ""
        if 'items' in receipt_data and receipt_data['items']:
            for item in receipt_data['items']:
                item_name = item.get('name', '')
                item_price = item.get('price', '')
                item_quantity = item.get('quantity', '1')
                items_str += f"{item_name} ({item_quantity}) - {item_price}\n"
        
        # Add timestamp for when the data was processed
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create a list representing a row in the spreadsheet
        row = [
            timestamp,           # Processing timestamp
            date,                # Receipt date
            merchant,            # Merchant/vendor
            total,               # Total amount
            subtotal,            # Subtotal
            tax,                 # Tax amount
            payment_method,      # Payment method
            items_str.strip()    # Items description
        ]
        
        # You might want to add more fields like category, notes, etc.
        
        return row
    
    async def generate_report(self, report_type: str) -> Dict[str, Any]:
        """
        Generate a financial report based on the receipts and invoices data
        
        Args:
            report_type: Type of report (daily, weekly, monthly, custom)
            
        Returns:
            Dictionary with report data
        """
        # Handle synchronous Google API calls in an async function
        return await asyncio.to_thread(self._generate_report_sync, report_type)
    
    def _generate_report_sync(self, report_type: str) -> Dict[str, Any]:
        """Synchronous version of generate_report for use with asyncio.to_thread"""
        try:
            # Determine date range based on report type
            today = datetime.datetime.now().date()
            
            if report_type == 'daily':
                start_date = today
                end_date = today
                period_str = f"{today.strftime('%Y-%m-%d')}"
            elif report_type == 'weekly':
                start_date = today - datetime.timedelta(days=today.weekday())  # Monday
                end_date = start_date + datetime.timedelta(days=6)  # Sunday
                period_str = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            elif report_type == 'monthly':
                start_date = today.replace(day=1)
                # Last day of month calculation
                if today.month == 12:
                    end_date = today.replace(year=today.year + 1, month=1, day=1) - datetime.timedelta(days=1)
                else:
                    end_date = today.replace(month=today.month + 1, day=1) - datetime.timedelta(days=1)
                period_str = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            else:  # custom or fallback
                # Default to last 30 days for custom or unknown types
                start_date = today - datetime.timedelta(days=30)
                end_date = today
                period_str = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            
            # Fetch receipt data from the sheet
            receipts_data = self._get_sheet_data(self.sheets['receipts'])
            
            # Convert to DataFrame for easier analysis
            if not receipts_data or len(receipts_data) <= 1:  # Only header or empty
                return {
                    "total_expenses": "0.00",
                    "period": period_str,
                    "categories": {},
                    "report_url": f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit"
                }
            
            # Convert to DataFrame for easier analysis
            headers = receipts_data[0]
            df = pd.DataFrame(receipts_data[1:], columns=headers)
            
            # Assuming date is in column 1 (index 1) and formatted as YYYY-MM-DD
            # Convert date strings to datetime objects for filtering
            date_col_index = 1  # Adjust based on your actual sheet structure
            
            # Filter by date range
            filtered_data = []
            for row in receipts_data[1:]:  # Skip header
                try:
                    row_date = datetime.datetime.strptime(row[date_col_index], "%Y-%m-%d").date()
                    if start_date <= row_date <= end_date:
                        filtered_data.append(row)
                except (ValueError, IndexError):
                    # Skip rows with invalid dates
                    continue
            
            # Calculate total expenses
            total_col_index = 3  # Adjust based on your actual sheet structure
            total_expenses = 0.0
            for row in filtered_data:
                try:
                    # Handle different formats of total amount
                    total_str = row[total_col_index].replace('$', '').replace(',', '')
                    total_expenses += float(total_str)
                except (ValueError, IndexError):
                    # Skip rows with invalid totals
                    continue
            
            # Mock category breakdown - in a real implementation, 
            # you would categorize expenses based on merchant or item types
            categories = {
                "Groceries": f"${total_expenses * 0.25:.2f}",
                "Dining": f"${total_expenses * 0.20:.2f}",
                "Entertainment": f"${total_expenses * 0.15:.2f}",
                "Transportation": f"${total_expenses * 0.10:.2f}",
                "Other": f"${total_expenses * 0.30:.2f}"
            }
            
            # Prepare and return the report data
            return {
                "total_expenses": f"${total_expenses:.2f}",
                "period": period_str,
                "categories": categories,
                "report_url": f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit"
            }
            
        except Exception as e:
            print(f"Error generating report: {e}")
            return {
                "total_expenses": "Error",
                "period": report_type,
                "categories": {},
                "error": str(e)
            }
    
    def _get_sheet_data(self, sheet_name: str) -> List[List[Any]]:
        """
        Get all data from a specific sheet
        
        Args:
            sheet_name: Name of the sheet to retrieve
            
        Returns:
            List of rows, where each row is a list of cell values
        """
        try:
            range_name = f"{sheet_name}!A:Z"  # Get all columns
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            return result.get('values', [])
            
        except Exception as e:
            print(f"Error getting sheet data: {e}")
            return []