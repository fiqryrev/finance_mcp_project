"""
Telegram bot handlers for data management
"""
import os
import re
import datetime
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.gcs_manager import GCSManager

# Initialize GCS Manager
gcs_manager = GCSManager()

# Define conversation states
AWAITING_DELETE_CONFIRMATION = 1
AWAITING_DATE_RANGE = 2
AWAITING_FILE_SELECTION = 3
AWAITING_DUPLICATE_CONFIRMATION = 4

async def my_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /mydata command - show a list of user's stored documents."""
    # Get user ID
    user_id = str(update.effective_user.id)
    
    # Send initial processing message
    message = await update.message.reply_text("🔍 Fetching your stored documents...")
    
    try:
        # Get list of user's files
        files = gcs_manager.list_user_files(user_id)
        
        if not files:
            await message.edit_text("📭 You don't have any stored documents yet.\n\nTo upload a document, send me a photo of a receipt or invoice, or upload a PDF document.")
            return
        
        # Create message with file list
        response = f"📁 *Your Stored Documents*\n\nYou have {len(files)} document(s) stored:\n\n"
        
        # Group files by date
        files_by_date = {}
        for file in files:
            date = file["timestamp"].split(" ")[0]  # Extract date part only
            if date not in files_by_date:
                files_by_date[date] = []
            files_by_date[date].append(file)
        
        # Create a formatted list, grouped by date
        for date, date_files in sorted(files_by_date.items(), reverse=True):
            response += f"📅 *{date}*\n"
            for i, file in enumerate(date_files, 1):
                file_name = file["original_name"]
                file_size = file["size"]
                file_time = file["timestamp"].split(" ")[1]  # Extract time part
                response += f"{i}. `{file_name}`\n   Size: {file_size} | Time: {file_time}\n"
            response += "\n"
        
        # Add instructions for data management
        response += "*Data Management Commands:*\n"
        response += "• /deletedata - Delete specific documents\n"
        response += "• /deletedatarange - Delete documents within a date range\n"
        response += "• /deletealldata - Delete all your stored documents\n"
        response += "• /datalocation - View where your data is stored\n"
        response += "• /deleteduplicates - Find and remove duplicate files\n"
        
        # Send the response
        await message.edit_text(response, parse_mode='Markdown')
        
    except Exception as e:
        await message.edit_text(f"❌ Error retrieving your documents: {str(e)}")

async def delete_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the /deletedata command - delete specific file."""
    # Get user ID
    user_id = str(update.effective_user.id)
    
    # Reset any existing context data
    context.user_data.clear()
    context.user_data["user_id"] = user_id
    
    # Send initial processing message
    message = await update.message.reply_text("🔍 Fetching your stored documents...")
    
    try:
        # Get list of user's files
        files = gcs_manager.list_user_files(user_id)
        
        if not files:
            await message.edit_text("📭 You don't have any stored documents yet.")
            return ConversationHandler.END
        
        # Save files to context
        context.user_data["files"] = files
        
        # Create inline keyboard with file options
        keyboard = []
        for i, file in enumerate(files[:10], 1):  # Limit to 10 files to avoid huge keyboards
            file_name = file["original_name"]
            # Truncate long filenames
            if len(file_name) > 30:
                file_name = file_name[:27] + "..."
            keyboard.append([InlineKeyboardButton(f"{i}. {file_name}", callback_data=f"delete_file_{i-1}")])
        
        # Add a cancel button
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="delete_cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update message with file selection keyboard
        await message.edit_text(
            "🗑️ Select a document to delete:", 
            reply_markup=reply_markup
        )
        
        return AWAITING_FILE_SELECTION
        
    except Exception as e:
        await message.edit_text(f"❌ Error retrieving your documents: {str(e)}")
        return ConversationHandler.END

async def delete_data_range_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the /deletedatarange command - delete files within a date range."""
    # Get user ID
    user_id = str(update.effective_user.id)
    
    # Reset any existing context data
    context.user_data.clear()
    context.user_data["user_id"] = user_id
    
    # Create inline keyboard with date range options
    keyboard = [
        [InlineKeyboardButton("Today", callback_data="date_range_today")],
        [InlineKeyboardButton("Yesterday", callback_data="date_range_yesterday")],
        [InlineKeyboardButton("Last 7 days", callback_data="date_range_7days")],
        [InlineKeyboardButton("Last 30 days", callback_data="date_range_30days")],
        [InlineKeyboardButton("Custom range", callback_data="date_range_custom")],
        [InlineKeyboardButton("❌ Cancel", callback_data="date_range_cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📅 Select a date range for documents to delete:", 
        reply_markup=reply_markup
    )
    
    return AWAITING_DATE_RANGE

async def delete_all_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the /deletealldata command - delete all user data."""
    # Get user ID
    user_id = str(update.effective_user.id)
    
    # Reset any existing context data
    context.user_data.clear()
    context.user_data["user_id"] = user_id
    
    # Create confirmation keyboard
    keyboard = [
        [
            InlineKeyboardButton("Yes, delete all", callback_data="confirm_delete_all"),
            InlineKeyboardButton("No, cancel", callback_data="cancel_delete_all")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ *WARNING: This will delete ALL your stored documents*\n\n"
        "Are you sure you want to continue? This action cannot be undone.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return AWAITING_DELETE_CONFIRMATION

async def data_location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /datalocation command - show where data is stored."""
    # Get user ID
    user_id = str(update.effective_user.id)
    
    # Get the directory URL
    directory_url = gcs_manager.get_user_directory_url(user_id)
    
    # Get list of user's files
    files = gcs_manager.list_user_files(user_id)
    file_count = len(files)
    
    # Calculate total size
    total_size_bytes = sum(file.get("size_bytes", 0) for file in files)
    
    # Create response message
    response = f"📂 *Your Data Storage Information*\n\n"
    response += f"• Number of documents: {file_count}\n"
    
    # Add location info
    response += f"\nYour documents are stored securely in Google Cloud Storage."
    response += f"\nStorage pattern: `documents/{user_id}/[timestamp]__[filename]`"
    
    # Add privacy note
    response += f"\n\n🔒 *Privacy Note*\n"
    response += f"Your data is accessible only to you and authorized system administrators. "
    response += f"We do not share your documents with third parties."
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_file_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle file selection for deletion."""
    query = update.callback_query
    await query.answer()
    
    # Check if user cancelled
    if query.data == "delete_cancel":
        await query.edit_message_text("❌ File deletion cancelled.")
        return ConversationHandler.END
    
    # Get the selected file index
    index = int(query.data.split("_")[-1])
    files = context.user_data.get("files", [])
    
    if 0 <= index < len(files):
        selected_file = files[index]
        context.user_data["selected_file"] = selected_file
        
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("Yes, delete", callback_data="confirm_delete"),
                InlineKeyboardButton("No, cancel", callback_data="cancel_delete")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Are you sure you want to delete `{selected_file['original_name']}`?\n\n"
            f"Uploaded on: {selected_file['timestamp']}\n"
            f"Size: {selected_file['size']}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return AWAITING_DELETE_CONFIRMATION
    else:
        await query.edit_message_text("❌ Invalid selection. Please try again.")
        return ConversationHandler.END

async def handle_date_range_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle date range selection for deletion."""
    query = update.callback_query
    await query.answer()
    
    # Check if user cancelled
    if query.data == "date_range_cancel":
        await query.edit_message_text("❌ Date range deletion cancelled.")
        return ConversationHandler.END
    
    # Get today's date
    today = datetime.datetime.now().date()
    
    # Process the selected date range
    if query.data == "date_range_today":
        after_date = today.strftime("%Y-%m-%d")
        before_date = None
        date_desc = "today"
    
    elif query.data == "date_range_yesterday":
        yesterday = today - datetime.timedelta(days=1)
        after_date = yesterday.strftime("%Y-%m-%d")
        before_date = yesterday.strftime("%Y-%m-%d")
        date_desc = "yesterday"
    
    elif query.data == "date_range_7days":
        week_ago = today - datetime.timedelta(days=7)
        after_date = week_ago.strftime("%Y-%m-%d")
        before_date = None
        date_desc = "the last 7 days"
    
    elif query.data == "date_range_30days":
        month_ago = today - datetime.timedelta(days=30)
        after_date = month_ago.strftime("%Y-%m-%d")
        before_date = None
        date_desc = "the last 30 days"
    
    elif query.data == "date_range_custom":
        await query.edit_message_text(
            "📅 Please enter a date range in the format:\n\n"
            "`YYYY-MM-DD YYYY-MM-DD`\n\n"
            "The first date is the start date and the second is the end date.\n"
            "Example: `2023-01-01 2023-01-31` for January 2023.\n\n"
            "Type 'cancel' to abort."
        )
        return AWAITING_DATE_RANGE
    
    else:
        await query.edit_message_text("❌ Invalid selection. Please try again.")
        return ConversationHandler.END
    
    # Store date range in context
    context.user_data["date_range"] = {
        "after_date": after_date,
        "before_date": before_date,
        "description": date_desc
    }
    
    # Create confirmation keyboard
    keyboard = [
        [
            InlineKeyboardButton("Yes, delete files", callback_data="confirm_date_range"),
            InlineKeyboardButton("No, cancel", callback_data="cancel_date_range")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚠️ Are you sure you want to delete all files from {date_desc}?\n\n"
        f"This action cannot be undone.",
        reply_markup=reply_markup
    )
    
    return AWAITING_DELETE_CONFIRMATION

async def handle_delete_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation for file deletion."""
    query = update.callback_query
    await query.answer()
    
    user_id = context.user_data.get("user_id")
    
    # Handle single file deletion
    if query.data == "confirm_delete":
        # Get the selected file
        selected_file = context.user_data.get("selected_file")
        
        if selected_file:
            # Delete the file
            success = gcs_manager.delete_file(selected_file["blob_name"])
            
            if success:
                await query.edit_message_text(f"✅ Successfully deleted `{selected_file['original_name']}`.", parse_mode='Markdown')
            else:
                await query.edit_message_text(f"❌ Failed to delete `{selected_file['original_name']}`. Please try again later.", parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ Error: File information not found.")
    
    # Handle date range deletion
    elif query.data == "confirm_date_range":
        # Get the date range
        date_range = context.user_data.get("date_range", {})
        
        if date_range:
            # Delete files in the date range
            result = gcs_manager.delete_user_files(user_id, {
                "after_date": date_range.get("after_date"),
                "before_date": date_range.get("before_date")
            })
            
            if result["status"] == "success":
                await query.edit_message_text(
                    f"✅ Successfully deleted {result['deleted_count']} files from {date_range.get('description', 'the specified date range')}."
                )
            else:
                await query.edit_message_text(
                    f"❌ Error deleting files: {result['message']}"
                )
        else:
            await query.edit_message_text("❌ Error: Date range information not found.")
    
    # Handle delete all confirmation
    elif query.data == "confirm_delete_all":
        # Delete all files
        result = gcs_manager.delete_user_files(user_id, {"all": True})
        
        if result["status"] == "success":
            await query.edit_message_text(
                f"✅ Successfully deleted all {result['deleted_count']} of your stored documents."
            )
        else:
            await query.edit_message_text(
                f"❌ Error deleting all files: {result['message']}"
            )
    
    # Handle cancellation
    elif query.data in ["cancel_delete", "cancel_date_range", "cancel_delete_all"]:
        await query.edit_message_text("❌ Deletion cancelled.")
    
    return ConversationHandler.END

async def handle_custom_date_range(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom date range input."""
    user_input = update.message.text.strip()
    
    # Check if user cancelled
    if user_input.lower() == 'cancel':
        await update.message.reply_text("❌ Date range deletion cancelled.")
        return ConversationHandler.END
    
    # Try to parse the date range
    date_pattern = r'(\d{4}-\d{2}-\d{2})\s+(\d{4}-\d{2}-\d{2})'
    match = re.match(date_pattern, user_input)
    
    if match:
        start_date = match.group(1)
        end_date = match.group(2)
        
        # Validate dates
        try:
            start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            
            if start_date_obj > end_date_obj:
                await update.message.reply_text(
                    "❌ Error: Start date must be before or equal to end date. Please try again."
                )
                return AWAITING_DATE_RANGE
            
            # Store date range in context
            context.user_data["date_range"] = {
                "after_date": start_date,
                "before_date": end_date,
                "description": f"{start_date} to {end_date}"
            }
            
            # Create confirmation keyboard
            keyboard = [
                [
                    InlineKeyboardButton("Yes, delete files", callback_data="confirm_date_range"),
                    InlineKeyboardButton("No, cancel", callback_data="cancel_date_range")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⚠️ Are you sure you want to delete all files from {start_date} to {end_date}?\n\n"
                f"This action cannot be undone.",
                reply_markup=reply_markup
            )
            
            return AWAITING_DELETE_CONFIRMATION
            
        except ValueError:
            await update.message.reply_text(
                "❌ Error: Invalid date format. Please use YYYY-MM-DD YYYY-MM-DD format."
            )
            return AWAITING_DATE_RANGE
    else:
        await update.message.reply_text(
            "❌ Error: Invalid date format. Please use YYYY-MM-DD YYYY-MM-DD format.\n\n"
            "Example: `2023-01-01 2023-01-31` for January 2023.\n\n"
            "Type 'cancel' to abort."
        )
        return AWAITING_DATE_RANGE

async def delete_duplicates_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the /deleteduplicates command - find and delete duplicate files."""
    # Get user ID
    user_id = str(update.effective_user.id)
    
    # Reset any existing context data
    context.user_data.clear()
    context.user_data["user_id"] = user_id
    
    # Send initial processing message
    message = await update.message.reply_text("🔍 Scanning your files for duplicates...")
    
    try:
        # Get list of user's files
        files = gcs_manager.list_user_files(user_id)
        
        if not files:
            await message.edit_text("📭 You don't have any stored documents yet.")
            return ConversationHandler.END
        
        # Find duplicates based on original filenames only (ignoring timestamps)
        filename_groups = {}
        
        for file in files:
            original_name = file["original_name"]
            filename_groups.setdefault(original_name, []).append(file)
        
        # Filter out non-duplicates
        duplicates = {name: files for name, files in filename_groups.items() if len(files) > 1}
        
        if not duplicates:
            await message.edit_text("✅ No duplicate files found! Each of your files has a unique name.")
            return ConversationHandler.END
        
        # Save duplicates to context
        context.user_data["duplicates"] = duplicates
        
        # Create a message with duplicate info
        response = f"🔍 *Found {sum(len(files) - 1 for files in duplicates.values())} duplicate files*\n\n"
        
        # Create inline keyboard for each duplicate set
        keyboard = []
        
        # Limit to 10 duplicate sets in the keyboard to avoid huge messages
        for i, (filename, file_list) in enumerate(list(duplicates.items())[:10], 1):
            # Sort by timestamp (newest first)
            file_list.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Truncate long filenames for display
            display_name = filename
            if len(display_name) > 25:
                display_name = display_name[:22] + "..."
                
            # Show count of duplicates
            keyboard.append([
                InlineKeyboardButton(
                    f"{i}. {display_name} ({len(file_list)} copies)",
                    callback_data=f"dup_{i-1}"
                )
            ])
            
            # Add info to response text
            response += f"{i}. `{filename}` - {len(file_list)} copies\n"
            response += f"   Latest: {file_list[0]['timestamp']}\n\n"
        
        # Add controls to keyboard
        keyboard.append([
            InlineKeyboardButton("🗑️ Clean All Duplicates", callback_data="clean_all_duplicates")
        ])
        keyboard.append([
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_duplicates")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Add instructions
        response += "\nSelect a file to manage its duplicates, or use the Clean All button to keep only the most recent version of each file."
        
        await message.edit_text(
            response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return AWAITING_FILE_SELECTION
        
    except Exception as e:
        await message.edit_text(f"❌ Error scanning for duplicates: {str(e)}")
        return ConversationHandler.END

async def handle_duplicate_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle duplicate file selection for deletion."""
    query = update.callback_query
    await query.answer()
    
    # Check if user cancelled
    if query.data == "cancel_duplicates":
        await query.edit_message_text("❌ Duplicate cleanup cancelled.")
        return ConversationHandler.END
    
    # Handle clean all duplicates
    if query.data == "clean_all_duplicates":
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("Yes, keep only the newest", callback_data="confirm_clean_all_duplicates"),
                InlineKeyboardButton("No, cancel", callback_data="cancel_duplicates")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Get duplicates count
        duplicates = context.user_data.get("duplicates", {})
        total_duplicates = sum(len(files) - 1 for files in duplicates.values())
        
        await query.edit_message_text(
            f"⚠️ This will delete {total_duplicates} duplicate files, keeping only the most recent version of each file.\n\n"
            f"Are you sure you want to continue? This action cannot be undone.",
            reply_markup=reply_markup
        )
        
        return AWAITING_DELETE_CONFIRMATION
    
    # Handle specific duplicate set selection
    if query.data.startswith("dup_"):
        # Get the selected duplicate index
        index = int(query.data.split("_")[1])
        duplicates = context.user_data.get("duplicates", {})
        
        # Get the duplicate set
        duplicate_keys = list(duplicates.keys())
        if 0 <= index < len(duplicate_keys):
            filename = duplicate_keys[index]
            file_list = duplicates[filename]
            
            # Sort by timestamp (newest first)
            file_list.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Save to context
            context.user_data["duplicate_files"] = file_list
            context.user_data["keep_file"] = file_list[0]  # Default to keeping the newest
            
            # Create keyboard to select which file to keep
            keyboard = []
            
            for i, file in enumerate(file_list):
                timestamp = file["timestamp"]
                keep_text = " (Will Keep)" if i == 0 else ""
                keyboard.append([
                    InlineKeyboardButton(
                        f"{timestamp}{keep_text}",
                        callback_data=f"keep_{i}"
                    )
                ])
            
            # Add confirm and cancel buttons
            keyboard.append([
                InlineKeyboardButton("Confirm", callback_data="confirm_delete_duplicates")
            ])
            keyboard.append([
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_duplicates")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"🗑️ *Manage duplicates for:* `{filename}`\n\n"
                f"Found {len(file_list)} copies. By default, the most recent version will be kept (marked above) and others will be deleted.\n\n"
                f"Click on a different timestamp to keep that version instead, then click Confirm.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return AWAITING_DUPLICATE_CONFIRMATION
    
    return AWAITING_FILE_SELECTION

async def handle_duplicate_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle which duplicate file to keep."""
    query = update.callback_query
    await query.answer()
    
    # Check if user cancelled
    if query.data == "cancel_duplicates":
        await query.edit_message_text("❌ Duplicate cleanup cancelled.")
        return ConversationHandler.END
    
    # Handle keep selection
    if query.data.startswith("keep_"):
        # Get the selected file index
        index = int(query.data.split("_")[1])
        file_list = context.user_data.get("duplicate_files", [])
        
        if 0 <= index < len(file_list):
            # Update the file to keep
            keep_file = file_list[index]
            context.user_data["keep_file"] = keep_file
            
            # Recreate keyboard with updated selection
            keyboard = []
            
            for i, file in enumerate(file_list):
                timestamp = file["timestamp"]
                keep_text = " (Will Keep)" if i == index else ""
                keyboard.append([
                    InlineKeyboardButton(
                        f"{timestamp}{keep_text}",
                        callback_data=f"keep_{i}"
                    )
                ])
            
            # Add confirm and cancel buttons
            keyboard.append([
                InlineKeyboardButton("Confirm", callback_data="confirm_delete_duplicates")
            ])
            keyboard.append([
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_duplicates")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                query.message.text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return AWAITING_DUPLICATE_CONFIRMATION
    
    # Handle confirmation
    elif query.data == "confirm_delete_duplicates":
        # Get the selected duplicates
        duplicate_files = context.user_data.get("duplicate_files", [])
        keep_file = context.user_data.get("keep_file")
        
        if duplicate_files and keep_file:
            # Delete all duplicates except the one to keep
            deleted_count = 0
            for file in duplicate_files:
                if file["blob_name"] != keep_file["blob_name"]:
                    if gcs_manager.delete_file(file["blob_name"]):
                        deleted_count += 1
            
            if deleted_count > 0:
                await query.edit_message_text(
                    f"✅ Successfully deleted {deleted_count} duplicates of `{keep_file['original_name']}`.\n\n"
                    f"Kept the version from {keep_file['timestamp']}.",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ No duplicates were deleted. The file `{keep_file['original_name']}` remains unchanged.",
                    parse_mode='Markdown'
                )
            
            return ConversationHandler.END
    
    # Handle clean all duplicates confirmation
    elif query.data == "confirm_clean_all_duplicates":
        # Get all duplicates
        duplicates = context.user_data.get("duplicates", {})
        user_id = context.user_data.get("user_id")
        
        if duplicates and user_id:
            total_deleted = 0
            kept_files = []
            
            # Process each set of duplicates
            for filename, file_list in duplicates.items():
                # Sort by timestamp (newest first)
                file_list.sort(key=lambda x: x["timestamp"], reverse=True)
                
                # Keep the newest file, delete the rest
                keep_file = file_list[0]
                kept_files.append(keep_file["original_name"])
                
                for file in file_list[1:]:
                    if gcs_manager.delete_file(file["blob_name"]):
                        total_deleted += 1
            
            if total_deleted > 0:
                await query.edit_message_text(
                    f"✅ Successfully cleaned up {total_deleted} duplicate files.\n\n"
                    f"Kept the most recent version of each file.",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ No duplicates were deleted. Your files remain unchanged.",
                    parse_mode='Markdown'
                )
            
            return ConversationHandler.END
    
    return AWAITING_DUPLICATE_CONFIRMATION