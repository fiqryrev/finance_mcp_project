import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.ocr_service import OCRService
from utils.gcs_manager import GCSManager

# Initialize GCS Manager
gcs_manager = GCSManager()


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    await update.message.reply_text(
        f"👋 Hello {update.effective_user.first_name}! I'm your financial document assistant. "
        f"Send me a photo of a receipt or invoice, and I'll extract the information and store it.\n\n"
        f"🔍 *Main Commands:*\n"
        f"• /help - Show detailed help\n"
        f"• /report - Generate a financial report\n"
        f"• /analyze - Analyze your transactions\n\n"
        f"📂 *Data Management:*\n"
        f"• /mydata - View your stored documents\n"
        f"• /deletedata - Delete specific documents\n"
        f"• /deleteduplicates - Find and remove duplicates\n"
        f"• /datalocation - See where your data is stored\n\n"
        f"Your data is stored securely and only accessible to you.",
        parse_mode='Markdown'
    )

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    help_text = """
    🤖 *Financial Document Bot Help*
    
    I can help you manage your financial documents. Here's what I can do:
    
    📝 *Basic Commands:*
    /start - Start the bot
    /help - Show this help message
    /report - Generate a financial report
    /analyze - Analyze your financial data
    
    📂 *Data Management:*
    /mydata - View a list of your stored documents
    /deletedata - Delete a specific document
    /deletedatarange - Delete documents within a date range
    /deletealldata - Delete all your stored documents
    /deleteduplicates - Find and remove duplicate files
    /datalocation - View where your data is stored
    
    📸 *Document Processing:*
    Just send me a photo of your receipt or invoice, and I'll extract the information automatically.
    You can also upload PDF documents for processing.
    
    📊 *Reports:*
    I can create reports based on your documents. Use /report to generate one.
    
    💡 *Analysis:*
    Get insights about your spending with /analyze.
    
    Your data is stored securely and is only accessible to you.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /report command."""
    # Create keyboard with report options
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
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📊 Which type of report would you like to generate?",
        reply_markup=reply_markup
    )

async def analyze_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /analyze command."""
    # Create keyboard with analysis options
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
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💡 What kind of analysis would you like to perform?",
        reply_markup=reply_markup
    )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle receipt photos."""
    # Notify user that processing has started
    processing_message = await update.message.reply_text("🔍 Processing your receipt... This may take a moment.")
    
    try:
        # Get the photo file
        photo_file = await update.message.photo[-1].get_file()  # Get the highest resolution photo
        
        # Get user ID for GCS folder name
        user_id = update.effective_user.id
        
        # Create a temporary file to save the photo
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_path = temp_file.name
            # Download the photo to the temporary file
            await photo_file.download_to_drive(temp_path)
            
            # Upload the file to GCS
            await processing_message.edit_text("📤 Uploading your receipt to secure storage...")
            
            # Read the file content
            with open(temp_path, 'rb') as file:
                file_content = file.read()
            
            # Upload to GCS
            file_name = f"photo_{photo_file.file_unique_id}.jpg"
            gcs_url = gcs_manager.upload_file(
                user_id=user_id,
                file_name=file_name,
                file_data=file_content,
                content_type="image/jpeg"
            )
            
            if not gcs_url:
                await processing_message.edit_text("❌ Error uploading your receipt. Please try again.")
                return
            
            # Continue with OCR processing
            await processing_message.edit_text("🔤 Extracting text from your receipt...")
            
            # Initialize OCR service and process the image
            ocr_service = OCRService()
            receipt_data = await ocr_service.process_image(temp_path)
            
            # Add GCS URL to the result
            if "error" not in receipt_data:
                receipt_data["document_url"] = gcs_url
            
            # Check for error in OCR result
            if "error" in receipt_data:
                await processing_message.edit_text(f"❌ Error processing the receipt: {receipt_data['error']}")
                return
            
            # Extract data based on document type
            document_type = receipt_data.get("document_type", "invoice")
            
            # Prepare response based on document type
            if document_type == "sales_invoice" and "sales_invoices" in receipt_data:
                invoice = receipt_data["sales_invoices"][0] if receipt_data["sales_invoices"] else {}
                response = format_sales_invoice(invoice)
            elif document_type == "purchase_invoice" and "purchase_invoices" in receipt_data:
                invoice = receipt_data["purchase_invoices"][0] if receipt_data["purchase_invoices"] else {}
                response = format_generic_invoice(invoice)
            else:
                # Default format for generic invoice
                response = format_generic_invoice(receipt_data)
            
            # Save data to Google Sheets if needed
            sheet_url = await save_to_gsheet(receipt_data)
            
            # Add sheet link if available
            if sheet_url:
                response += f"\n\n📊 Data saved to spreadsheet: {sheet_url}"
            
            # Add document storage info
            response += f"\n\n🔒 Document saved securely for future reference."
            
            # Reply with the extracted information
            await processing_message.edit_text(response)
        
        # Clean up the temporary file
        os.unlink(temp_path)
        
    except Exception as e:
        await processing_message.edit_text(f"❌ Error processing the receipt: {str(e)}")

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document uploads (PDFs, etc.)."""
    # Notify user that processing has started
    processing_message = await update.message.reply_text("🔍 Processing your document... This may take a moment.")
    
    temp_path = None
    try:
        # Get the document file
        document_file = await update.message.document.get_file()
        
        # Get user ID for GCS folder name
        user_id = update.effective_user.id
        
        # Get file name
        file_name = update.message.document.file_name
        file_ext = os.path.splitext(file_name)[1].lower()
        
        # Log document information
        print(f"Processing document: name={file_name}, file_id={document_file.file_id}, size={document_file.file_size}, ext={file_ext}")
        
        # Check if the file type is supported
        supported_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        if file_ext not in supported_extensions:
            await processing_message.edit_text(
                f"❌ Unsupported file type: {file_ext}\n\n"
                f"Supported file types are: PDF, JPG, JPEG, PNG"
            )
            return
        
        # Create a temporary file to save the document
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
            temp_path = temp_file.name
            # Download the document to the temporary file
            await document_file.download_to_drive(temp_path)
            print(f"Document saved to temporary file: {temp_path}")
            
            # Upload the file to GCS
            await processing_message.edit_text("📤 Uploading your document to secure storage...")
            
            # Read the file content
            with open(temp_path, 'rb') as file:
                file_content = file.read()
            
            # Determine content type
            content_type = None
            if file_ext == '.pdf':
                content_type = "application/pdf"
            elif file_ext in ['.jpg', '.jpeg']:
                content_type = "image/jpeg"
            elif file_ext == '.png':
                content_type = "image/png"
            elif file_ext in ['.tif', '.tiff']:
                content_type = "image/tiff"
            elif file_ext == '.bmp':
                content_type = "image/bmp"
            
            # Upload to GCS
            gcs_url = gcs_manager.upload_file(
                user_id=user_id,
                file_name=file_name,
                file_data=file_content,
                content_type=content_type
            )
            
            if not gcs_url:
                await processing_message.edit_text("❌ Error uploading your document. Please try again.")
                return
        
        # Process the document
        status_message = await update.message.reply_text("🔤 Extracting text from your document...")
        
        try:
            # Initialize OCR service and process the document
            ocr_service = OCRService()
            document_data = await ocr_service.process_document(temp_path, file_ext)
            
            # Add GCS URL to the result
            if "error" not in document_data:
                document_data["document_url"] = gcs_url
            
            # Check for error in OCR result
            if "error" in document_data:
                await status_message.edit_text(f"❌ Error extracting text: {document_data['error']}")
                await processing_message.edit_text(
                    "I'm having trouble processing this document. Please make sure the file is valid and try again."
                )
                return
            
            # Extract data based on document type
            document_type = document_data.get("document_type", "invoice")
            
            # Prepare response based on document type
            if document_type == "sales_invoice" and "sales_invoices" in document_data:
                invoice = document_data["sales_invoices"][0] if document_data["sales_invoices"] else {}
                response = format_generic_invoice(invoice)
            elif document_type == "purchase_invoice" and "purchase_invoices" in document_data:
                invoice = document_data["purchase_invoices"][0] if document_data["purchase_invoices"] else {}
                response = format_generic_invoice(invoice)
            else:
                # Default format for generic invoice
                response = format_generic_invoice(document_data)
            
            # Save data to Google Sheets if needed
            sheet_url = await save_to_gsheet(document_data)
            
            # Add sheet link if available
            if sheet_url:
                response += f"\n\n📊 Data saved to spreadsheet: {sheet_url}"
            
            # Add document storage info
            response += f"\n\n🔒 Document saved securely for future reference."
            
            # Reply with the extracted information
            await processing_message.edit_text(response)
            await status_message.delete()
            
        except Exception as ocr_error:
            print(f"Document processing error: {str(ocr_error)}")
            await status_message.edit_text(f"❌ Error extracting text: {str(ocr_error)}")
            await processing_message.edit_text(
                "I'm having trouble processing this document. Please make sure the file is valid and try again.\n\n"
                "Tips for better results:\n"
                "- PDF files should be text-based, not scanned images\n"
                "- Make sure the document is clearly legible\n"
                "- Try uploading a different format if possible"
            )
    
    except Exception as e:
        print(f"Error in document handler: {str(e)}")
        await processing_message.edit_text(
            f"❌ Error processing the document: {str(e)}\n\n"
            "Please check that the document is valid and try again."
        )
    
    finally:
        # Clean up the temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                print(f"Temporary file removed: {temp_path}")
            except Exception as cleanup_error:
                print(f"Error removing temporary file: {str(cleanup_error)}")

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()  # Answer the callback query to stop the loading animation
    
    # Get the callback data
    callback_data = query.data
    
    if callback_data.startswith("report_"):
        report_type = callback_data.split("_")[1]
        await generate_report(query, report_type)
    
    elif callback_data.startswith("analyze_"):
        analysis_type = callback_data.split("_")[1]
        await perform_analysis(query, analysis_type)

async def generate_report(query, report_type: str) -> None:
    """Generate and send a financial report."""
    await query.edit_message_text(f"Generating {report_type} report... Please wait.")
    
    try:
        # Call the sheets service to generate the report
        # In a real implementation, you would connect to your GSheet service here
        report_data = {}  # Mock data
        
        # For now, just send a placeholder message
        response = f"📊 *{report_type.capitalize()} Financial Report*\n\n"
        response += "This is a placeholder for the financial report. In a real implementation, this would show your financial data."
        
        await query.edit_message_text(response, parse_mode='Markdown')
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error generating report: {str(e)}")

async def perform_analysis(query, analysis_type: str) -> None:
    """Perform financial analysis."""
    await query.edit_message_text(f"Performing {analysis_type} analysis... Please wait.")
    
    try:
        # For now, just send a placeholder message
        response = f"💡 *{analysis_type.capitalize()} Analysis*\n\n"
        response += "This is a placeholder for the financial analysis. In a real implementation, this would show analysis of your financial data."
        
        await query.edit_message_text(response, parse_mode='Markdown')
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error performing analysis: {str(e)}")

def format_generic_invoice(receipt_data):
    """Format a generic invoice for display in Telegram."""
    response = f"✅ Receipt processed successfully!\n\n"
    response += f"📄 *Document Details*\n"
    response += f"📆 Date: {receipt_data.get('invoice_date', 'Not found')}\n"
    response += f"🏪 Merchant: {receipt_data.get('supplier_company_name', receipt_data.get('customer_name', 'Not found'))}\n"
    response += f"💰 Total: {receipt_data.get('grand_total', receipt_data.get('total_amount', 'Not found'))}\n"
    
    # Add items if available
    items = receipt_data.get('items', [])
    if items:
        response += "\n📋 Items:\n"
        for item in items:
            name = item.get('item_product_name', 'Unknown Item')
            price = item.get('item_total_amount', item.get('item_price_unit', '0.00'))
            quantity = item.get('item_quantity', '1')
            response += f"- {name} x{quantity}: {price}\n"
    
    return response

def format_sales_invoice(invoice):
    """Format a sales invoice for display in Telegram."""
    # Similar to format_generic_invoice but with sales-specific fields
    response = f"✅ Sales Invoice processed successfully!\n\n"
    response += f"📄 *Invoice Details*\n"
    response += f"📆 Date: {invoice.get('invoice_date', 'Not found')}\n"
    response += f"🔢 Invoice Number: {invoice.get('invoice_number', 'Not found')}\n"
    response += f"👤 Customer: {invoice.get('customer_name', 'Not found')}\n"
    response += f"💰 Total: {invoice.get('grand_total', 'Not found')}\n"
    
    # Add items if available
    items = invoice.get('items', [])
    if items:
        response += "\n📋 Items:\n"
        for item in items:
            name = item.get('item_product_name', 'Unknown Item')
            price = item.get('item_total_amount', item.get('item_price_unit', '0.00'))
            quantity = item.get('item_quantity', '1')
            response += f"- {name} x{quantity}: {price}\n"
    
    return response

def format_purchase_invoice(invoice):
    """Format a purchase invoice for display in Telegram."""
    # Similar to format_generic_invoice but with purchase-specific fields
    response = f"✅ Purchase Invoice processed successfully!\n\n"
    response += f"📄 *Invoice Details*\n"
    response += f"📆 Date: {invoice.get('invoice_date', 'Not found')}\n"
    response += f"🔢 Invoice Number: {invoice.get('invoice_number', 'Not found')}\n"
    response += f"🏢 Supplier: {invoice.get('supplier_company_name', 'Not found')}\n"
    response += f"💰 Total: {invoice.get('grand_total', 'Not found')}\n"
    
    # Add items if available
    items = invoice.get('items', [])
    if items:
        response += "\n📋 Items:\n"
        for item in items:
            name = item.get('item_product_name', 'Unknown Item')
            price = item.get('item_total_amount', item.get('item_price_unit', '0.00'))
            quantity = item.get('item_quantity', '1')
            response += f"- {name} x{quantity}: {price}\n"
    
    return response

async def save_to_gsheet(receipt_data):
    """
    Save receipt data to Google Sheets.
    
    In a real implementation, this would call the sheets service.
    For now, it returns a mock URL.
    
    Args:
        receipt_data: The extracted receipt data
        
    Returns:
        URL to the sheet (or None)
    """
    # This is a mock implementation - replace with actual GSheet integration
    # from utils.gsheet_mcp import GSheetModelContextProtocol
    # gsheet_mcp = GSheetModelContextProtocol()
    # result = await gsheet_mcp.process_request(f"Save receipt data for {receipt_data.get('document_type')}")
    # return result.get("spreadsheet_url")
    
    # Mock return for now
    return None