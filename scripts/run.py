from utils.telegram_bot import sendMessage, inbox
from dotenv import load_dotenv
import os, time
import traceback
from datetime import datetime
import re
from main import MCPInterface
from utils.integrated_mcp import IntegratedMCP

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

# Maximum length for a single Telegram message (slightly under the 4096 limit)
MAX_MESSAGE_LENGTH = 3900

def format_for_telegram(text):
    """Format text to escape special characters for Telegram MarkdownV2"""
    if not text:
        return ""
    
    # Convert text to string if it's not already
    text = str(text)
    
    # Escape special characters
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    
    return text

def send_long_message(chat_id, reply_id, message, TOKEN):
    """Send a message that might be too long for a single Telegram message
    by breaking it into multiple parts if necessary"""
    
    # Check if message needs to be split
    if len(message) <= MAX_MESSAGE_LENGTH:
        # Message is short enough to send as single message
        try:
            sendMessage(message, chat_id, reply_id, TOKEN=TOKEN)
        except Exception as e:
            print(f"Error sending message: {e}")
        return
    
    # Message is too long, split it into parts
    parts = []
    current_part = ""
    
    # Split by paragraphs (this approach respects content structure better)
    # Using re.split to keep the newline characters in the split
    paragraphs = re.split(r'(\n\n|\n)', message)
    
    for paragraph in paragraphs:
        # If adding this paragraph would make the part too long, save current part and start a new one
        if len(current_part + paragraph) > MAX_MESSAGE_LENGTH:
            if current_part:
                parts.append(current_part)
            current_part = paragraph
        else:
            current_part += paragraph
    
    # Add the last part if not empty
    if current_part:
        parts.append(current_part)
    
    # Fallback in case the above logic fails to split effectively
    if not parts or max(len(part) for part in parts) > MAX_MESSAGE_LENGTH:
        # Simpler approach: just split by character count
        parts = []
        for i in range(0, len(message), MAX_MESSAGE_LENGTH):
            parts.append(message[i:i + MAX_MESSAGE_LENGTH])
    
    # Send each part
    for i, part in enumerate(parts):
        part_header = f"*Bagian {i+1}/{len(parts)}*\n\n" if len(parts) > 1 else ""
        try:
            formatted_part = format_for_telegram(part_header) + part
            sendMessage(formatted_part, chat_id, reply_id, TOKEN=TOKEN)
            time.sleep(0.5)  # Small delay to ensure messages arrive in order
        except Exception as e:
            print(f"Error sending message part {i+1}: {e}")

def send_step_update(chat_id, reply_id, message, TOKEN):
    """Send incremental updates to user"""
    formatted_message = format_for_telegram(message)
    try:
        sendMessage(formatted_message, chat_id, reply_id, TOKEN=TOKEN)
    except Exception as e:
        print(f"Error sending step update: {e}")

def identify_request_type(request):
    """Simplified request type identification for the bot"""
    # Check for common keywords to determine request type
    has_arango = any(word in request.lower() for word in ["arango", "arangodb", "database"])
    has_gsheet = any(word in request.lower() for word in ["gsheet", "google sheet", "spreadsheet", "sheet"])
    has_email_send = any(word in request.lower() for word in ["email", "kirim", "send"]) and re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', request)
    has_email_read = any(word in request.lower() for word in ["cek email", "check email", "lihat email", "baca email", "email masuk", "belum dibaca"])
    has_email_reply = any(phrase in request.lower() for phrase in ["balas email", "reply email", "tanggapi email", "jawab email"])
    
    # Determine the request type based on keywords
    if has_arango and has_gsheet and has_email_send:
        return "combined_arango_gsheet_email"
    elif has_arango and has_gsheet:
        return "combined_arango_gsheet"
    elif has_arango and has_email_send:
        return "combined_arango_email"
    elif has_gsheet and has_email_send:
        return "combined_gsheet_email"
    elif has_arango:
        return "arango"
    elif has_gsheet:
        return "gsheet"
    elif has_email_send:
        return "email_send"
    elif has_email_read:
        return "email_read"
    elif has_email_reply:
        return "email_reply"
    else:
        return "unknown"

def process_mcp_result(result):
    """Convert MCP result to telegram-friendly message with detailed steps"""
    message_parts = []
    sheet_link = None
    
    # First, search for Google Sheet links in all possible locations
    # Check in top-level spreadsheet_info
    if "spreadsheet_info" in result:
        info = result["spreadsheet_info"]
        if "spreadsheet_url" in info and info["spreadsheet_url"]:
            sheet_link = info["spreadsheet_url"]
    
    # Check in gsheet_result
    if "gsheet_result" in result:
        gsheet_result = result["gsheet_result"]
        # Check in gsheet_result's spreadsheet_info
        if "spreadsheet_info" in gsheet_result:
            info = gsheet_result["spreadsheet_info"]
            if "spreadsheet_url" in info and info["spreadsheet_url"]:
                sheet_link = info["spreadsheet_url"]
                
        # Check in nested results of gsheet_result
        if "results" in gsheet_result:
            for step_result in gsheet_result["results"]:
                if "spreadsheet_info" in step_result:
                    info = step_result["spreadsheet_info"]
                    if "spreadsheet_url" in info and info["spreadsheet_url"]:
                        sheet_link = info["spreadsheet_url"]
    
    # Add status with icon
    status = result.get("status", "unknown")
    status_icon = "✅" if status == "success" else "⚠️" if status == "partial_success" else "❌"
    message_parts.append(f"{status_icon} *STATUS: {status.upper()}*")
    
    # Add main message
    if "message" in result:
        message_parts.append(f"📄 *Pesan:* {result['message']}")
    
    # Add spreadsheet info if present (from any source)
    if "spreadsheet_info" in result:
        info = result["spreadsheet_info"]
        message_parts.append("\n📊 *INFORMASI GOOGLE SHEET*")
        message_parts.append(f"  • Nama: {info.get('spreadsheet_name', 'Unknown')}")
        message_parts.append(f"  • Worksheet: {info.get('worksheet_name', 'Unknown')}")
    
    # Add Google Sheet results if present
    if "gsheet_result" in result:
        message_parts.append("\n📊 *HASIL GOOGLE SHEET*")
        gsheet_result = result["gsheet_result"]
        
        gsheet_status = gsheet_result.get("status", "unknown")
        gsheet_status_icon = "✅" if gsheet_status == "success" else "⚠️" if gsheet_status == "partial_success" else "❌"
        message_parts.append(f"{gsheet_status_icon} Status: {gsheet_status.upper()}")
        
        if "message" in gsheet_result:
            message_parts.append(f"Pesan: {gsheet_result['message']}")
        
        if "steps_summary" in gsheet_result:
            message_parts.append("\n*Langkah yang dilakukan:*")
            for i, step in enumerate(gsheet_result["steps_summary"], 1):
                message_parts.append(f"  {i}\\. {step}")
    
    # Add ArangoDB results summary
    if "arango_result" in result:
        message_parts.append("\n🗃️ *HASIL ARANGODB*")
        arango_result = result["arango_result"]
        
        arango_status = arango_result.get("status", "unknown")
        arango_status_icon = "✅" if arango_status == "success" else "⚠️" if arango_status == "partial_success" else "❌"
        message_parts.append(f"{arango_status_icon} Status: {arango_status.upper()}")
        
        if "message" in arango_result:
            message_parts.append(f"Pesan: {arango_result['message']}")
        
        # Add query details
        query_details = arango_result.get("query_details", {})
        if query_details:
            message_parts.append(f"\n*Deskripsi:* {query_details.get('description', 'Tidak ada deskripsi')}")
            message_parts.append(f"*Collection:* {query_details.get('collection', 'paper_payment')}")
            if "table" in query_details:
                message_parts.append(f"*Tabel:* {query_details.get('table', 'purchase_invoice_disbursements')}")
            
            if "query" in query_details:
                message_parts.append("\n*Query AQL:*")
                message_parts.append(f"  {query_details.get('query', 'Tidak ada query')}")
            
            if "filters" in query_details and query_details["filters"]:
                message_parts.append("\n*Filter yang digunakan:*")
                for filter_desc in query_details["filters"]:
                    message_parts.append(f"  • {filter_desc}")
                    
            if "sort" in query_details and query_details["sort"]:
                message_parts.append("\n*Sorting:*")
                for sort_desc in query_details["sort"]:
                    message_parts.append(f"  • {sort_desc}")
        
        # Add row count information
        message_parts.append(f"\n*Jumlah data:* {arango_result.get('row_count', 0)} baris")
        
        # Include summary if available - display full summary
        if "summary" in arango_result and arango_result["summary"]:
            message_parts.append(f"\n*Ringkasan Data:*")
            message_parts.append(arango_result["summary"])
            
        # Add preview data if available (limit to 5 rows)
        if "data" in arango_result and arango_result["data"]:
            data = arango_result["data"]
            if len(data) > 0:
                message_parts.append("\n*Preview Data (5 baris pertama):*")
                
                # Get up to 5 rows for preview
                preview_data = data[:5] if len(data) > 5 else data
                
                # Determine if data is a DataFrame or list of dictionaries
                if hasattr(preview_data, 'iterrows'):  # DataFrame
                    for i, (_, row) in enumerate(preview_data.iterrows(), 1):
                        message_parts.append(f"\n*Baris {i}:*")
                        # Get important fields or first few fields
                        important_fields = ["_key", "status", "disbursement_request_no", 
                                         "disbursement_amount", "partner_name", 
                                         "invoice_number", "payment_method"]
                        
                        # Display fields that exist in the data
                        field_count = 0
                        for field in important_fields:
                            if field in row:
                                message_parts.append(f"  • {field}: {row[field]}")
                                field_count += 1
                        
                        message_parts.append(f"  • \\.\\.\\. ({len(row)} fields total)")
                else:  # List of dictionaries
                    for i, row in enumerate(preview_data, 1):
                        if isinstance(row, dict):
                            message_parts.append(f"\n*Baris {i}:*")
                            # Display important fields
                            important_fields = ["_key", "status", "disbursement_request_no", 
                                             "disbursement_amount", "partner_name", 
                                             "invoice_number", "payment_method"]
                            
                            field_count = 0
                            for field in important_fields:
                                if field in row:
                                    message_parts.append(f"  • {field}: {row[field]}")
                                    field_count += 1
                            
                            message_parts.append(f"  • \\.\\.\\. ({len(row)} fields total)")
            
        # Add Excel path if available
        if "excel_path" in arango_result:
            message_parts.append(f"\n📊 Data disimpan ke file Excel: {arango_result['excel_path']}")
    
    # Add Email results if present
    if "email_result" in result:
        message_parts.append("\n📧 *HASIL EMAIL*")
        email_result = result["email_result"]
        email_status = email_result.get("status", "unknown")
        email_status_icon = "✅" if email_status == "success" else "⚠️" if email_status == "partial_success" else "❌"
        message_parts.append(f"{email_status_icon} Status: {email_status.upper()}")
        message_parts.append(f"Pesan: {email_result.get('message', 'Tidak ada pesan')}")
        
        # Add recipient info if available
        if "details" in email_result:
            details = email_result["details"]
            message_parts.append("\n*Detail:*")
            for key, value in details.items():
                message_parts.append(f"  • {key}: {value}")
                
            # Highlight special features
            if 'has_attachment' in details and details['has_attachment']:
                message_parts.append("  • 📎 Email terkirim dengan lampiran Excel")
                
            if 'has_gsheet_link' in details and details['has_gsheet_link']:
                message_parts.append("  • 🔗 Email terkirim dengan link Google Sheet")
    
    # Add Email Reader results if present - show all emails, not just first few
    if "result_type" in result and result.get("result_type") in ["unread_emails", "email_summary", "search_emails", "email_trends", "reply_all_from_sender"]:
        message_parts.append("\n📨 *HASIL EMAIL READER*")
        result_type = result.get("result_type")
        data = result.get("data", {})
        
        if result_type == "unread_emails":
            message_parts.append(f"\n*Email yang belum dibaca:* {data.get('count', 0)}")
            # Include all emails
            if "emails" in data and data["emails"]:
                message_parts.append("\n*Email terbaru:*")
                for i, email in enumerate(data["emails"], 1):
                    subject = email.get("subject", "No Subject")
                    sender = email.get("sender", "Unknown")
                    date = email.get("date", "Unknown date")
                    
                    message_parts.append(f"\n  {i}\\. Dari: {sender}")
                    message_parts.append(f"     Subjek: {subject}")
                    message_parts.append(f"     Tanggal: {date}")
                    
                    # Add body preview if available
                    if "body_preview" in email and email["body_preview"]:
                        preview = email["body_preview"].strip().replace("\n", " ")
                        message_parts.append(f"     Preview: {preview}")
                
        elif result_type == "email_summary":
            message_parts.append(f"\n*Ringkasan Email untuk {data.get('period_days', 1)} hari terakhir:*")
            message_parts.append(f"• Total email: {data.get('total_emails', 0)}")
            message_parts.append(f"• Email belum dibaca: {data.get('unread_emails', 0)}")
            
            if "top_senders" in data:
                message_parts.append("\n*Top pengirim:*")
                for sender, count in data["top_senders"]:  # Show all top senders
                    message_parts.append(f"  • {sender}: {count} email")
            
            if "summary" in data:
                message_parts.append("\n*Ringkasan:*")
                message_parts.append(data["summary"])
            
            # Show all emails in summary
            if "emails" in data and data["emails"]:
                message_parts.append("\n*Email terbaru:*")
                for i, email in enumerate(data["emails"], 1):
                    subject = email.get("subject", "No Subject")
                    sender = email.get("sender", "Unknown")
                    date = email.get("date", "Unknown date")
                    
                    message_parts.append(f"\n  {i}\\. Dari: {sender}")
                    message_parts.append(f"     Subjek: {subject}")
                    message_parts.append(f"     Tanggal: {date}")
                
        elif result_type == "search_emails":
            criteria = data.get("search_criteria", {})
            message_parts.append(f"\n*Hasil pencarian email:*")
            criteria_parts = []
            if "sender" in criteria and criteria["sender"]:
                criteria_parts.append(f"dari={criteria['sender']}")
            if "subject" in criteria and criteria["subject"]:
                criteria_parts.append(f"subjek='{criteria['subject']}'")
            if "days" in criteria:
                criteria_parts.append(f"{criteria['days']} hari terakhir")
            
            criteria_text = ", ".join(criteria_parts) if criteria_parts else "semua email"
            message_parts.append(f"• Kriteria: {criteria_text}")
            message_parts.append(f"• Ditemukan: {data.get('count', 0)} email")
            
            # Show all emails found
            if "emails" in data and data["emails"]:
                message_parts.append("\n*Email yang ditemukan:*")
                for i, email in enumerate(data["emails"], 1):
                    read_status = "📖" if email.get("read") else "🆕"
                    subject = email.get("subject", "No Subject")
                    sender = email.get("sender", "Unknown")
                    date = email.get("date", "Unknown date")
                    
                    message_parts.append(f"\n  {i}\\. {read_status} Dari: {sender}")
                    message_parts.append(f"     Subjek: {subject}")
                    message_parts.append(f"     Tanggal: {date}")
                    
                    # Add body preview if available
                    if "body_preview" in email and email["body_preview"]:
                        preview = email["body_preview"].strip().replace("\n", " ")
                        message_parts.append(f"     Preview: {preview}")
            
        elif result_type == "email_trends":
            message_parts.append(f"\n*Analisis tren email untuk {data.get('period_days', 7)} hari terakhir:*")
            message_parts.append(f"• Total email: {data.get('total_emails', 0)}")
            
            if "top_senders" in data:
                message_parts.append("\n*Top pengirim:*")
                for sender, count in list(data["top_senders"].items()):  # Show all senders
                    message_parts.append(f"  • {sender}: {count} email")
            
            if "top_domains" in data:
                message_parts.append("\n*Top domain:*")
                for domain, count in list(data["top_domains"].items()):  # Show all domains
                    message_parts.append(f"  • {domain}: {count} email")
            
            if "analysis" in data:
                message_parts.append("\n*Analisis:*")
                message_parts.append(data["analysis"])
            
        elif result_type == "reply_all_from_sender":
            message_parts.append(f"\n*Hasil membalas email dari {data.get('sender', 'Unknown')}:*")
            message_parts.append(f"• Jumlah email ditemukan: {data.get('emails_found', 0)}")
            message_parts.append(f"• Jumlah email dibalas: {data.get('emails_replied', 0)}")
            
            # Show all emails replied to
            if "replied_emails" in data and data["replied_emails"]:
                message_parts.append("\n*Email yang dibalas:*")
                for i, reply_data in enumerate(data["replied_emails"], 1):
                    email = reply_data.get("email", {})
                    reply_result = reply_data.get("reply_result", {})
                    
                    subject = email.get("subject", "No Subject")
                    date = email.get("date", "Unknown date")
                    
                    message_parts.append(f"\n  {i}\\. Subjek: {subject}")
                    message_parts.append(f"     Tanggal: {date}")
                    
                    if "suggested_reply" in reply_result:
                        reply_preview = reply_result["suggested_reply"].strip().replace("\n", " ")
                        message_parts.append(f"     Balasan: {reply_preview[:100]}...")
    
    # Join all parts
    message = "\n".join(message_parts)
    
    # Handle sheet link separately
    if sheet_link:
        link_message = f"\n\n🔗 *GOOGLE SHEET LINK*:\n{sheet_link}"
        link_message = format_for_telegram(link_message)
        return message, link_message
    else:
        return message, None

def handle_command(text, chat_id, reply_id):
    """Handle special commands"""
    if text.lower() in ["/start", "/help"]:
        help_message = """
*Model Context Protocol* 🤖

Saya dapat membantu Anda dengan:
- Mengakses data dari ArangoDB
- Membuat dan mengelola Google Sheet
- Mengirim dan membaca email

Contoh perintah:
- _buatkan google sheet dari data arango yang sedang di ajukan hari ini_
- _ambil data invoice yang sudah dicairkan dari arango_
- _cek email yang belum dibaca hari ini_
- _cari email dari finance@example.com minggu ini_

Gunakan /help untuk menampilkan panduan ini lagi.
        """
        return format_for_telegram(help_message)
    
    return None

# Initialize MCP Interface
mcp = MCPInterface()

replied = []
print("🤖 Bot Telegram - Model Context Protocol telah berjalan...")
print("Menunggu pesan...")

while True:
    print('---------------')
    try:
        all_message = inbox(TOKEN)
    except Exception as e:
        print(f"Error mengambil pesan: {e}")
        time.sleep(5)
        continue

    message_count = len(all_message.get('result', []))
    print(f"Jumlah pesan: {message_count}")
    
    for result in all_message.get('result', []):
        try:
            message = result['message']
            date = datetime.fromtimestamp(message['date'])
            reply_id = message['message_id'] 
            range_time = (datetime.now()-date).total_seconds()/60
            
            if reply_id in replied:
                continue

            if range_time > 10:
                continue
                
            chat_id = message['from']['id']
            try:
                username = message['from']['username']
            except:
                username = chat_id
                
            text = message.get('text', message.get('caption', ''))
            print(f'Pesan dari {username} ({chat_id}): {text}')
            print(f'ID pesan: {reply_id}, Waktu: {date}')

            # Check for commands first
            command_response = handle_command(text, chat_id, reply_id)
            if command_response:
                sendMessage(command_response, chat_id, reply_id, TOKEN=TOKEN)
                replied.append(reply_id)
                continue
            
            # Initial message to user
            initial_message = format_for_telegram("⏳ *Memproses permintaan...*")
            sendMessage(initial_message, chat_id, reply_id, TOKEN=TOKEN)
            
            # Send step-by-step updates
            send_step_update(chat_id, reply_id, "🔍 Menganalisis permintaan Anda...", TOKEN)
            
            # Record start time for performance tracking
            start_time = time.time()
            
            # Use our own simplified request type identification instead of accessing the internal method
            request_type = identify_request_type(text)
            send_step_update(chat_id, reply_id, f"🏷️ Tipe permintaan teridentifikasi: {request_type}", TOKEN)
            
            # Process based on request type with updates
            if "arango" in request_type:
                send_step_update(chat_id, reply_id, "🗃️ Menghubungi database ArangoDB...", TOKEN)
                if "gsheet" in request_type:
                    send_step_update(chat_id, reply_id, "📊 Bersiap menyimpan data ke Google Sheet setelah query selesai...", TOKEN)
                if "email" in request_type:
                    send_step_update(chat_id, reply_id, "📧 Email akan disiapkan setelah data diterima...", TOKEN)
            elif "gsheet" in request_type:
                send_step_update(chat_id, reply_id, "📊 Memproses operasi Google Sheet...", TOKEN)
                if "email" in request_type:
                    send_step_update(chat_id, reply_id, "📧 Email akan disiapkan setelah operasi sheet selesai...", TOKEN)
            elif "email" in request_type:
                if "read" in request_type:
                    send_step_update(chat_id, reply_id, "📨 Membaca email dari inbox...", TOKEN)
                elif "reply" in request_type:
                    send_step_update(chat_id, reply_id, "↩️ Menyiapkan balasan email...", TOKEN)
                else:
                    send_step_update(chat_id, reply_id, "📧 Menyiapkan email untuk dikirim...", TOKEN)
            
            # Process the request
            mcp_result = mcp.process_request(text)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Format the result
            main_message, sheet_link_message = process_mcp_result(mcp_result)
            
            # Add processing time info
            time_info = format_for_telegram(f"\n⏱️ Waktu eksekusi: {processing_time:.2f} detik")
            
            # Format and send the full message (potentially split into multiple parts)
            formatted_main_message = format_for_telegram(main_message) + time_info
            send_long_message(chat_id, reply_id, formatted_main_message, TOKEN)
            
            # Send sheet link as a separate message if it exists
            if sheet_link_message:
                time.sleep(0.5)  # Small delay to ensure messages arrive in order
                sendMessage(sheet_link_message, chat_id, reply_id, TOKEN=TOKEN)
            
        except Exception as e:
            error_message = f"❌ Terjadi kesalahan: {str(e)}"
            print(f"Error: {error_message}")
            print(traceback.format_exc())
            
            try:
                sendMessage(format_for_telegram(error_message), chat_id, reply_id, TOKEN=TOKEN)
            except:
                print("Failed to send error message to Telegram")
        
        # Mark as replied regardless of success or failure
        replied.append(reply_id)    

    # Clean up old message IDs to prevent list from growing too large
    if len(replied) > 1000:
        replied = replied[-500:]  # Keep only the most recent 500
        
    time.sleep(5)