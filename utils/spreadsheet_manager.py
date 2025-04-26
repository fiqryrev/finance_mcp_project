"""
Utility for managing user-specific Google Spreadsheet operations
"""
import os
import re
import datetime
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

class SpreadsheetManager:
    """
    Service for managing user-specific Google Spreadsheets for financial data
    """
    
    def __init__(self, credentials_path=None):
        """
        Initialize the Spreadsheet Manager
        
        Args:
            credentials_path: Path to Google service account credentials file
        """
        # Get credentials path from env if not provided
        if not credentials_path:
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        self.credentials_path = credentials_path
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        
        # Initialize the sheets API client
        self.service = self._create_sheets_service()
        
        # Define the column structure for invoice data
        self.columns = [
            "invoice_id",             # GCS filename 
            "transaction_date",       # YYYY-MM-DD format
            "transaction_currency",   # USD/IDR/etc.
            "transaction_item_name",  # Name of item on transaction
            "transaction_amount",     # Amount of transaction
            "transaction_type"        # debit/credit/tax
        ]
        
        # Cache of user spreadsheet IDs
        self.user_spreadsheets = {}
    
    def _create_sheets_service(self):
        """Create and return a Google Sheets service"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.scopes
            )
            service = build('sheets', 'v4', credentials=credentials)
            return service
        except Exception as e:
            print(f"Error creating Sheets service: {e}")
            return None
    
    async def get_user_spreadsheet(self, user_id):
        """
        Get or create a spreadsheet for a specific user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Tuple of (spreadsheet_id, spreadsheet_url)
        """
        # Check cache first
        if user_id in self.user_spreadsheets:
            return self.user_spreadsheets[user_id]
        
        # Search for existing spreadsheet with this user's name
        spreadsheet_name = f"Finance Report - {user_id}"
        try:
            # Try to find the spreadsheet by name
            drive_service = build('drive', 'v3', credentials=self.service._credentials)
            response = drive_service.files().list(
                q=f"name='{spreadsheet_name}' and mimeType='application/vnd.google-apps.spreadsheet'",
                spaces='drive'
            ).execute()
            
            # If spreadsheet exists, use it
            if response.get('files', []):
                spreadsheet_id = response['files'][0]['id']
                spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
                
                # Cache for future use
                self.user_spreadsheets[user_id] = (spreadsheet_id, spreadsheet_url)
                
                # Check if it has the correct headers, add them if not
                self._ensure_headers(spreadsheet_id)
                
                return (spreadsheet_id, spreadsheet_url)
        except Exception as e:
            print(f"Error searching for spreadsheet: {e}")
        
        # Spreadsheet not found, create a new one
        return await self.create_user_spreadsheet(user_id)
    
    async def create_user_spreadsheet(self, user_id):
        """
        Create a new spreadsheet for a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Tuple of (spreadsheet_id, spreadsheet_url)
        """
        spreadsheet_name = f"Finance Report - {user_id}"
        
        try:
            # Create a new spreadsheet
            spreadsheet = {
                'properties': {
                    'title': spreadsheet_name
                },
                'sheets': [
                    {
                        'properties': {
                            'title': 'Transactions',
                            'gridProperties': {
                                'frozenRowCount': 1  # Freeze header row
                            }
                        }
                    }
                ]
            }
            
            # Create the spreadsheet
            spreadsheet = self.service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = spreadsheet['spreadsheetId']
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
            
            # Cache the ID and URL
            self.user_spreadsheets[user_id] = (spreadsheet_id, spreadsheet_url)
            
            # Add headers
            self._add_headers(spreadsheet_id)
            
            # Apply formatting
            self._apply_basic_formatting(spreadsheet_id)
            
            print(f"Created new spreadsheet for user {user_id}: {spreadsheet_url}")
            return (spreadsheet_id, spreadsheet_url)
            
        except Exception as e:
            print(f"Error creating spreadsheet for user {user_id}: {e}")
            return (None, None)
    
    def _add_headers(self, spreadsheet_id):
        """Add column headers to the spreadsheet"""
        sheet_range = "Transactions!A1:F1"
        body = {
            'values': [self.columns]
        }
        
        try:
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=sheet_range,
                valueInputOption="RAW",
                body=body
            ).execute()
        except Exception as e:
            print(f"Error adding headers: {e}")
    
    def _ensure_headers(self, spreadsheet_id):
        """Check if headers exist and are correct, add them if not"""
        try:
            # Get first row
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range="Transactions!A1:F1"
            ).execute()
            
            values = result.get('values', [])
            
            # Check if headers exist and match expected columns
            if not values or values[0] != self.columns:
                self._add_headers(spreadsheet_id)
                
        except Exception as e:
            print(f"Error checking headers: {e}")
            # Attempt to add headers anyway
            self._add_headers(spreadsheet_id)
    
    def _apply_basic_formatting(self, spreadsheet_id):
        """Apply basic formatting to the spreadsheet"""
        try:
            # Format headers as bold
            header_format_request = {
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.9,
                                'green': 0.9,
                                'blue': 0.9
                            },
                            'textFormat': {
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            }
            
            # Auto-resize columns
            auto_resize_request = {
                'autoResizeDimensions': {
                    'dimensions': {
                        'sheetId': 0,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 6
                    }
                }
            }
            
            # Execute formatting requests
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [header_format_request, auto_resize_request]}
            ).execute()
            
        except Exception as e:
            print(f"Error applying formatting: {e}")
    
    async def add_invoice_data(self, user_id, invoice_data):
        """
        Add invoice data to a user's spreadsheet
        
        Args:
            user_id: Telegram user ID
            invoice_data: List of dictionaries with invoice data, each containing:
                - invoice_id (GCS filename)
                - transaction_date
                - transaction_currency
                - transaction_item_name
                - transaction_amount
                - transaction_type
            
        Returns:
            Boolean success status
        """
        # Get user spreadsheet
        spreadsheet_id, _ = await self.get_user_spreadsheet(user_id)
        
        if not spreadsheet_id:
            print(f"Error: Could not get spreadsheet for user {user_id}")
            return False
        
        try:
            # Prepare data rows
            rows = []
            for item in invoice_data:
                row = [
                    item.get('invoice_id', ''),
                    item.get('transaction_date', ''),
                    item.get('transaction_currency', ''),
                    item.get('transaction_item_name', ''),
                    item.get('transaction_amount', ''),
                    item.get('transaction_type', '')
                ]
                rows.append(row)
            
            # Append data to spreadsheet
            body = {
                'values': rows
            }
            
            self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range="Transactions",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
            
            print(f"Added {len(rows)} rows of data to spreadsheet for user {user_id}")
            return True
            
        except Exception as e:
            print(f"Error adding invoice data to spreadsheet: {e}")
            return False
    
    async def delete_invoice_data(self, user_id, invoice_id):
        """
        Delete invoice data from a user's spreadsheet
        
        Args:
            user_id: Telegram user ID
            invoice_id: GCS filename to match for deletion
            
        Returns:
            Number of rows deleted
        """
        # Get user spreadsheet
        spreadsheet_id, _ = await self.get_user_spreadsheet(user_id)
        
        if not spreadsheet_id:
            print(f"Error: Could not get spreadsheet for user {user_id}")
            return 0
        
        try:
            # Get all data from spreadsheet
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range="Transactions"
            ).execute()
            
            values = result.get('values', [])
            
            if len(values) <= 1:  # Only header row or empty
                return 0
            
            # Find rows with matching invoice_id
            header = values[0]
            id_col_index = header.index("invoice_id") if "invoice_id" in header else 0
            
            # Track rows to delete
            rows_to_delete = []
            for i, row in enumerate(values[1:], 1):  # Skip header
                if row and len(row) > id_col_index and row[id_col_index] == invoice_id:
                    rows_to_delete.append(i)
            
            if not rows_to_delete:
                return 0
            
            # Delete rows (in reverse order to avoid shifting issues)
            for row_index in sorted(rows_to_delete, reverse=True):
                delete_request = {
                    'deleteDimension': {
                        'range': {
                            'sheetId': 0,
                            'dimension': 'ROWS',
                            'startIndex': row_index,
                            'endIndex': row_index + 1
                        }
                    }
                }
                
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': [delete_request]}
                ).execute()
            
            print(f"Deleted {len(rows_to_delete)} rows with invoice_id '{invoice_id}' for user {user_id}")
            return len(rows_to_delete)
            
        except Exception as e:
            print(f"Error deleting invoice data from spreadsheet: {e}")
            return 0
    
    async def delete_all_user_data(self, user_id):
        """
        Delete all data from a user's spreadsheet
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Boolean success status
        """
        # Get user spreadsheet
        spreadsheet_id, _ = await self.get_user_spreadsheet(user_id)
        
        if not spreadsheet_id:
            print(f"Error: Could not get spreadsheet for user {user_id}")
            return False
        
        try:
            # Clear all data except header row
            clear_request = {
                'deleteDimension': {
                    'range': {
                        'sheetId': 0,
                        'dimension': 'ROWS',
                        'startIndex': 1,  # Start after header row
                        'endIndex': 1000  # Arbitrary large number
                    }
                }
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [clear_request]}
            ).execute()
            
            print(f"Deleted all data for user {user_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting all data from spreadsheet: {e}")
            return False
            
    async def get_user_spreadsheet_url(self, user_id):
        """
        Get the URL for a user's spreadsheet
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Spreadsheet URL or None if not found
        """
        _, url = await self.get_user_spreadsheet(user_id)
        return url
    
    def extract_invoice_data(self, receipt_data, file_name):
        """
        Extract structured invoice data from OCR results
        
        Args:
            receipt_data: OCR result dictionary
            file_name: GCS filename (used as invoice_id)
            
        Returns:
            List of dictionaries with invoice data fields
        """
        invoice_data = []
        
        try:
            # Get basic invoice information
            transaction_date = receipt_data.get('invoice_date', receipt_data.get('date', ''))
            # Format date if needed to YYYY-MM-DD
            if transaction_date and not re.match(r'^\d{4}-\d{2}-\d{2}$', transaction_date):
                try:
                    # Try to parse various date formats
                    parsed_date = pd.to_datetime(transaction_date)
                    transaction_date = parsed_date.strftime('%Y-%m-%d')
                except:
                    # If parsing fails, keep original
                    pass
            
            # Get currency
            transaction_currency = receipt_data.get('currency', 'USD')
            if isinstance(transaction_currency, dict) and 'currency' in transaction_currency:
                transaction_currency = transaction_currency['currency']
                
            # Extract items
            items = receipt_data.get('items', [])
            
            if items:
                # Process each item
                for item in items:
                    item_name = item.get('item_product_name', item.get('name', 'Unknown Item'))
                    item_amount = item.get('item_total_amount', item.get('item_price_unit', item.get('price', '0.00')))
                    
                    # Clean amount (remove currency symbols, commas)
                    if isinstance(item_amount, str):
                        item_amount = re.sub(r'[^\d.]', '', item_amount)
                    
                    # Create entry for this item
                    invoice_data.append({
                        'invoice_id': file_name,
                        'transaction_date': transaction_date,
                        'transaction_currency': transaction_currency,
                        'transaction_item_name': item_name,
                        'transaction_amount': item_amount,
                        'transaction_type': 'debit'  # Default to debit for purchases
                    })
            else:
                # No items found, create a single entry for the total
                total_amount = receipt_data.get('grand_total', receipt_data.get('total_amount', receipt_data.get('total', '0.00')))
                
                # Clean amount (remove currency symbols, commas)
                if isinstance(total_amount, str):
                    total_amount = re.sub(r'[^\d.]', '', total_amount)
                
                invoice_data.append({
                    'invoice_id': file_name,
                    'transaction_date': transaction_date,
                    'transaction_currency': transaction_currency,
                    'transaction_item_name': f"Total purchase from {receipt_data.get('supplier_company_name', receipt_data.get('merchant', 'Unknown Merchant'))}",
                    'transaction_amount': total_amount,
                    'transaction_type': 'debit'  # Default to debit for purchases
                })
            
            return invoice_data
            
        except Exception as e:
            print(f"Error extracting invoice data: {e}")
            # Return a default entry if extraction fails
            return [{
                'invoice_id': file_name,
                'transaction_date': datetime.datetime.now().strftime('%Y-%m-%d'),
                'transaction_currency': 'IDR',
                'transaction_item_name': 'Unknown purchase',
                'transaction_amount': '0.00',
                'transaction_type': 'debit'
            }]