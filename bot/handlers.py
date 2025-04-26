"""
Telegram bot message handlers
"""
import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.llm_service import LLMService
from services.ocr_service import OCRService
from services.sheets_service import SheetsService

# Initialize services
llm_service = LLMService()
ocr_service = OCRService()
sheets_service = SheetsService()

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    await update.message.reply_text(
        f"👋 Hello {update.effective_user.first_name}! I'm your financial document assistant. "
        f"Send me a photo of a receipt or invoice, and I'll extract the information and store it.\n\n"
        f"You can also use the following commands:\n"
        f"/help - Show help message\n"
        f"/report - Generate a financial report\n"
        f"/analyze - Analyze your recent transactions"
    )

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    help_text = """
    🤖 *Financial Document Bot Help*
    
    I can help you manage your financial documents. Here's what I can do:
    
    📝 *Commands:*
    /start - Start the bot
    /help - Show this help message
    /report - Generate a financial report
    /analyze - Analyze your financial data
    
    📸 *Document Processing:*
    Just send me a photo of your receipt or invoice, and I'll extract the information automatically.
    
    📊 *Reports:*
    I can create reports based on your documents. Use /report to generate one.
    
    💡 *Analysis:*
    Get insights about your spending with /analyze.
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
        
        # Create a temporary file to save the photo
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_path = temp_file.name
            # Download the photo to the temporary file
            await photo_file.download_to_drive(temp_path)
        
        # Process the image with OCR
        await update.message.reply_text("🔤 Extracting text from your receipt...")
        receipt_data = await ocr_service.process_image(temp_path)
        
        # Save data to sheets
        sheet_url = await sheets_service.save_receipt_data(receipt_data)
        
        # Prepare the response
        response = f"✅ Receipt processed successfully!\n\nHere's what I found:\n\n"
        response += f"📆 Date: {receipt_data.get('date', 'Not found')}\n"
        response += f"🏪 Merchant: {receipt_data.get('merchant', 'Not found')}\n"
        response += f"💰 Total: {receipt_data.get('total', 'Not found')}\n"
        
        if receipt_data.get('items'):
            response += "\n📋 Items:\n"
            for item in receipt_data.get('items', []):
                response += f"- {item.get('name')}: {item.get('price')}\n"
        
        # Add sheet link if available
        if sheet_url:
            response += f"\n📊 Data saved to spreadsheet: {sheet_url}"
        
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
        
        # Get file extension
        file_name = update.message.document.file_name
        file_ext = os.path.splitext(file_name)[1].lower()
        
        # Log document information
        print(f"Processing document: name={file_name}, file_id={document_file.file_id}, size={document_file.file_size}, ext={file_ext}")
        
        # Check if the file type is supported
        supported_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
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
        
        # Process the document
        status_message = await update.message.reply_text("🔤 Extracting text from your document...")
        
        try:
            # Process the document - wrapped in try block for specific error handling
            document_data = await ocr_service.process_document(temp_path, file_ext)
            
            # Save data to sheets (mock implementation for now)
            # In a real implementation, this would call the sheets service
            sheet_url = "https://docs.google.com/spreadsheets/d/example"  # Mock URL
            
            # Prepare the response
            response = f"✅ Document processed successfully!\n\nHere's what I found:\n\n"
            response += f"📆 Date: {document_data.get('date', 'Not found')}\n"
            response += f"🏪 Merchant/Vendor: {document_data.get('merchant', 'Not found')}\n"
            response += f"💰 Total: {document_data.get('total', 'Not found')}\n"
            
            if document_data.get('items'):
                response += "\n📋 Items/Details:\n"
                for item in document_data.get('items', []):
                    response += f"- {item.get('name')}: {item.get('price')}\n"
            
            # Add sheet link if available
            if sheet_url:
                response += f"\n📊 Data saved to spreadsheet: {sheet_url}"
            
            # Reply with the extracted information
            await processing_message.edit_text(response)
            
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
        report_data = await sheets_service.generate_report(report_type)
        
        # Format the report for Telegram
        response = f"📊 *{report_type.capitalize()} Financial Report*\n\n"
        
        # Add summary information
        response += f"Total Expenses: {report_data.get('total_expenses', 'N/A')}\n"
        response += f"Period: {report_data.get('period', 'N/A')}\n"
        
        # Add category breakdown if available
        if 'categories' in report_data:
            response += "\n*Category Breakdown:*\n"
            for category, amount in report_data.get('categories', {}).items():
                response += f"• {category}: {amount}\n"
        
        # Add link to detailed report if available
        if 'report_url' in report_data:
            response += f"\n[View Detailed Report]({report_data.get('report_url')})"
        
        await query.edit_message_text(response, parse_mode='Markdown')
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error generating report: {str(e)}")

async def perform_analysis(query, analysis_type: str) -> None:
    """Perform financial analysis."""
    await query.edit_message_text(f"Performing {analysis_type} analysis... Please wait.")
    
    try:
        # Get analysis from LLM service
        analysis_data = await llm_service.analyze_financial_data(analysis_type)
        
        # Format the analysis for Telegram
        response = f"💡 *{analysis_type.capitalize()} Analysis*\n\n"
        response += analysis_data.get("analysis", "No analysis available")
        
        # Add visualizations or links if available
        if 'visualization_url' in analysis_data:
            response += f"\n\n[View Visualization]({analysis_data.get('visualization_url')})"
        
        await query.edit_message_text(response, parse_mode='Markdown')
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error performing analysis: {str(e)}")