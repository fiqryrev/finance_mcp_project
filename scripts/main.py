#!/usr/bin/env python3
"""
Script utama untuk Model Context Protocol terintegrasi

Penggunaan:
    python main.py "permintaan pengguna"

Contoh:
    python main.py "buatkan data transaksi dummy untuk tim finance lalu kirim ke john@example.com"
    python main.py "tarikan data dari gsheet URL di worksheet BNI simpan datanya di local"
    python main.py "cek email yang belum dibaca hari ini"
    python main.py "cari email dari finance@example.com minggu ini"
    python main.py "ambil data invoice yang sudah dicairkan dari arango"
"""

import sys
import time
import json
import textwrap
import os
from typing import Dict, Any, List
from utils.integrated_mcp import IntegratedMCP

class MCPInterface:
    """Interface untuk berinteraksi dengan Model Context Protocol"""
    
    def __init__(self):
        """Inisialisasi interface"""
        self.mcp = IntegratedMCP()
        
    def process_request(self, user_request: str) -> Dict[str, Any]:
        """
        Memproses permintaan dari pengguna
        
        Args:
            user_request: Permintaan pengguna dalam bahasa natural
            
        Returns:
            Hasil proses dari MCP
        """
        self._print_request(user_request)
        
        start_time = time.time()
        result = None
        
        try:
            # Jalankan MCP
            result = self.mcp.process_request(user_request)
            
            # Tampilkan hasil
            self._print_result(result)
            
        except Exception as e:
            self._print_error(str(e))
            import traceback
            traceback.print_exc()
            result = {"status": "error", "message": str(e)}
            
        # Tampilkan waktu eksekusi
        elapsed_time = time.time() - start_time
        print(f"\n⏱️  Waktu eksekusi: {elapsed_time:.2f} detik")
        
        # Cek apakah ada pesan kesalahan yang perlu ditangani khusus
        if result and result.get("status") == "error":
            error_msg = result.get("message", "")
            # Jika error berkaitan dengan kredensial Google Sheet
            if "credentials" in error_msg.lower() and "google" in error_msg.lower():
                print("\n⚠️ SOLUSI:")
                print("Pastikan file kredensial Google Sheet (gsheet_creds.json) sudah tersedia dan valid.")
                print("Cek apakah file kredensial sudah memiliki akses yang diperlukan.")
            # Jika error berkaitan dengan koneksi ArangoDB
            elif "arango" in error_msg.lower() and ("connection" in error_msg.lower() or "credential" in error_msg.lower()):
                print("\n⚠️ SOLUSI:")
                print("Pastikan kredensial ArangoDB sudah benar di file .env")
                print("Cek koneksi ke server ArangoDB dan pastikan server tersedia.")
            # Jika error berkaitan dengan email
            elif "email" in error_msg.lower() and ("authentication" in error_msg.lower() or "login" in error_msg.lower()):
                print("\n⚠️ SOLUSI:")
                print("Pastikan kredensial email sudah benar di file .env")
                print("Untuk Gmail, pastikan 'Less secure app access' diaktifkan atau gunakan App Password.")
        
        # Check if there are unhandled combined requests
        if (("gsheet" in user_request.lower() and "arango" in user_request.lower()) or 
                ("sheet" in user_request.lower() and "arango" in user_request.lower())):
            if not (result and result.get("gsheet_result")):
                print("\n⚠️ CATATAN:")
                print("Permintaan Anda sepertinya melibatkan data ArangoDB dan Google Sheet.")
                print("Jika ada operasi gsheet yang belum dilakukan, coba gunakan format:")
                print("- \"Ambil data X dari Arango dan simpan ke Google Sheet\"")
                print("- \"Buat spreadsheet dari data arango dengan kriteria Y\"")
        
        return result

    def _print_banner(self):
        """Menampilkan banner aplikasi"""
        banner = """
    ___  ___           _        _    _____                _               _   
    |  \/  |          | |      | |  /  __ \              | |             | |  
    | .  . | ___    __| |  ___ | | | /  \/ ___  _ __  ___| |_ _____  __ _| |_ 
    | |\/| |/ _ \  / _` | / _ \| | | |    / _ \| '_ \/ __| __/ _ \ \/ _` | __|
    | |  | | (_) || (_| ||  __/| | | \__/\ (_) | | | \__ \ ||  __/  | (_| | |_ 
    \_|  |_/\___/  \__,_| \___||_|  \____/\___/|_| |_|___/\__\___|   \__,_|\__|
    ______           _                     _
    | ___ \         | |                   | |
    | |_/ / __ ___ | |_ ___   ___ ___  | |
    |  __/ '_ ` _ \| __/ _ \ / __/ _ \ | |
    | |  | | | | | | || (_) | (_| (_) || |
    \_|  |_| |_| |_|\__\___/ \___\___/ |_|
            """
        print(banner)
        print("=" * 80)
        print("🤖 Model Context Protocol (MCP) Terintegrasi 🤖")
        print("=" * 80)
        print("\n📋 Contoh perintah yang dapat Anda gunakan:")
        print("  • buatkan data transaksi dummy untuk tim finance lalu kirim ke john@example.com")
        print("  • tarikan data dari gsheet URL di worksheet Sheet1 simpan datanya di local")
        print("  • ambil data invoice yang sudah dicairkan dari arango")
        print("  • buatin gsheet dari data arango yang sedang di ajukan hari ini")
        print("  • cek email yang belum dibaca hari ini")
        print("  • cari email dari finance@example.com minggu ini")
        print("=" * 80)

    
    def _print_request(self, request: str):
        """Menampilkan permintaan pengguna"""
        print("\n📝 PERMINTAAN PENGGUNA")
        print("-" * 80)
        print(f"➤ {request}")
        print("-" * 80)
        print("\n⏳ Memproses permintaan...\n")
    
    def _print_result(self, result: Dict[str, Any]):
        """Menampilkan hasil eksekusi"""
        print("\n✅ HASIL EKSEKUSI")
        print("=" * 80)
        
        # Tampilkan status
        status = result.get("status", "unknown")
        status_icon = "✓" if status == "success" else "⚠️" if status == "partial_success" else "✗"
        print(f"{status_icon} Status: {status.upper()}")
        print(f"📄 Pesan: {result.get('message', 'Tidak ada pesan')}")
        print("-" * 80)
        
        # Tampilkan informasi spreadsheet jika ada
        if "spreadsheet_info" in result:
            print("\n📊 INFORMASI GOOGLE SHEET")
            info = result["spreadsheet_info"]
            print(f"  Nama: {info.get('spreadsheet_name', 'Unknown')}")
            print(f"  Worksheet: {info.get('worksheet_name', 'Unknown')}")
            if "spreadsheet_url" in info and info["spreadsheet_url"]:
                print(f"  URL: {info['spreadsheet_url']}")
            print("-" * 80)
        
        # Tampilkan hasil Google Sheet jika ada
        if "gsheet_result" in result:
            print("\n📊 HASIL GOOGLE SHEET")
            
            # Ambil gsheet_result
            gsheet_result = result["gsheet_result"]
            
            # Tampilkan status
            gsheet_status = gsheet_result.get("status", "unknown")
            gsheet_status_icon = "✓" if gsheet_status == "success" else "⚠️" if gsheet_status == "partial_success" else "✗"
            print(f"{gsheet_status_icon} Status: {gsheet_status.upper()}")
            print(f"Pesan: {gsheet_result.get('message', 'Tidak ada pesan')}")
            
            # Tampilkan langkah-langkah
            if "steps_summary" in gsheet_result:
                print("\nLangkah yang dilakukan:")
                for i, step in enumerate(gsheet_result["steps_summary"], 1):
                    print(f"  {i}. {step}")
            
            # Tampilkan info spreadsheet jika ada
            if "spreadsheet_info" in gsheet_result:
                info = gsheet_result["spreadsheet_info"]
                print("\nInformasi Spreadsheet:")
                print(f"  Nama: {info.get('spreadsheet_name', 'Unknown')}")
                print(f"  Worksheet: {info.get('worksheet_name', 'Unknown')}")
                if "spreadsheet_url" in info and info["spreadsheet_url"]:
                    print(f"  URL: {info['spreadsheet_url']}")
                    # Highlight the URL for better visibility
                    print(f"\n  🔗 LINK GOOGLE SHEET: {info['spreadsheet_url']}")
            
            # Tampilkan path file local jika ada
            for result_item in gsheet_result.get("results", []):
                if "local_path" in result_item:
                    print(f"\nFile lokal: {result_item['local_path']}")
            
            print("-" * 80)
        # Tampilkan hasil Google Sheet dari core result jika ada
        elif "steps_summary" in result:
            print("\n📊 HASIL GOOGLE SHEET")
            
            # Tampilkan langkah-langkah
            print("\nLangkah yang dilakukan:")
            for i, step in enumerate(result["steps_summary"], 1):
                print(f"  {i}. {step}")
            
            # Tampilkan info spreadsheet jika ada
            if "spreadsheet_info" in result:
                info = result["spreadsheet_info"]
                print("\nInformasi Spreadsheet:")
                print(f"  Nama: {info.get('spreadsheet_name', 'Unknown')}")
                print(f"  Worksheet: {info.get('worksheet_name', 'Unknown')}")
                if "spreadsheet_url" in info and info["spreadsheet_url"]:
                    print(f"  URL: {info['spreadsheet_url']}")
                    # Highlight the URL for better visibility
                    print(f"\n  🔗 LINK GOOGLE SHEET: {info['spreadsheet_url']}")
            
            # Tampilkan path file local jika ada
            for result_item in result.get("results", []):
                if "local_path" in result_item:
                    print(f"\nFile lokal: {result_item['local_path']}")
            
            print("-" * 80)
        
        # Tampilkan hasil ArangoDB jika ada
        if "arango_result" in result:
            print("\n🗃️ HASIL ARANGODB")
            
            # Ambil result ArangoDB
            arango_result = result["arango_result"]
            
            # Tampilkan status
            arango_status = arango_result.get("status", "unknown")
            arango_status_icon = "✓" if arango_status == "success" else "⚠️" if arango_status == "partial_success" else "✗"
            print(f"{arango_status_icon} Status: {arango_status.upper()}")
            print(f"Pesan: {arango_result.get('message', 'Tidak ada pesan')}")
            
            # Tampilkan detail query
            query_details = arango_result.get("query_details", {})
            if query_details:
                print(f"\nDeskripsi: {query_details.get('description', 'Tidak ada deskripsi')}")
                print(f"Collection: {query_details.get('collection', 'paper_payment')}")
                print(f"Tabel: {query_details.get('table', 'purchase_invoice_disbursements')}")
                print("\nQuery AQL:")
                print(f"  {query_details.get('query', 'Tidak ada query')}")
                
                if "filters" in query_details and query_details["filters"]:
                    print("\nFilter yang digunakan:")
                    for filter_desc in query_details["filters"]:
                        print(f"  - {filter_desc}")
                
                if "sort" in query_details and query_details["sort"]:
                    print("\nSorting:")
                    for sort_desc in query_details["sort"]:
                        print(f"  - {sort_desc}")
            
            # Tampilkan jumlah data yang didapatkan
            print(f"\nJumlah data: {arango_result.get('row_count', 0)} baris")
            
            # Tampilkan ringkasan
            if "summary" in arango_result and arango_result["summary"]:
                print("\nRingkasan Data:")
                self._print_wrapped_text(arango_result["summary"])
                
            # Tampilkan preview data jika tersedia
            if "data" in arango_result and arango_result["data"] is not None:
                data = arango_result["data"]
                if len(data) > 0:
                    print("\nPreview Data (5 baris pertama):")
                    try:
                        # Jika data lebih dari 5 baris, ambil 5 baris pertama saja
                        preview_data = data[:5] if len(data) > 5 else data
                        max_field_length = 40  # Batasi panjang nilai field untuk tampilan
                        
                        # Check if data is a DataFrame or a list of dictionaries
                        if hasattr(preview_data, 'iterrows'):  # It's a DataFrame
                            for i, (_, row) in enumerate(preview_data.iterrows(), 1):
                                print(f"\nBaris {i}:")
                                # Get all columns from DataFrame
                                important_fields = ["_key", "status", "disbursement_request_no", 
                                                "disbursement_amount", "partner_name", 
                                                "invoice_number", "payment_method"]
                                
                                for field in important_fields:
                                    if field in row:
                                        value = str(row[field])
                                        if len(value) > max_field_length:
                                            value = value[:max_field_length] + "..."
                                        print(f"  {field}: {value}")
                                
                                # Tambahkan '...' untuk menunjukkan ada field lain
                                print(f"  ... ({len(row)} fields total)")
                        else:  # It's a list of dictionaries
                            for i, row in enumerate(preview_data, 1):
                                print(f"\nBaris {i}:")
                                # Tampilkan beberapa field penting saja untuk keterbacaan
                                important_fields = ["_key", "status", "disbursement_request_no", 
                                                "disbursement_amount", "partner_name", 
                                                "invoice_number", "payment_method"]
                                
                                for field in important_fields:
                                    if isinstance(row, dict) and field in row:
                                        value = str(row[field])
                                        if len(value) > max_field_length:
                                            value = value[:max_field_length] + "..."
                                        print(f"  {field}: {value}")
                                
                                # Tambahkan '...' untuk menunjukkan ada field lain
                                num_fields = len(row) if isinstance(row, dict) else "unknown"
                                print(f"  ... ({num_fields} fields total)")
                    except Exception as e:
                        print(f"Error saat menampilkan preview data: {str(e)}")
            
            # Tampilkan path file local jika data di-export ke Excel
            if "excel_path" in arango_result:
                print(f"\nData disimpan ke file Excel: {arango_result['excel_path']}")
            
            print("-" * 80)
        elif "query_details" in result:
            print("\n🗃️ HASIL ARANGODB")
            
            # Tampilkan detail query
            query_details = result.get("query_details", {})
            if query_details:
                print(f"\nDeskripsi: {query_details.get('description', 'Tidak ada deskripsi')}")
                print(f"Collection: {query_details.get('collection', 'paper_payment')}")
                print(f"Tabel: {query_details.get('table', 'purchase_invoice_disbursements')}")
                print("\nQuery AQL:")
                print(f"  {query_details.get('query', 'Tidak ada query')}")
                
                if "filters" in query_details and query_details["filters"]:
                    print("\nFilter yang digunakan:")
                    for filter_desc in query_details["filters"]:
                        print(f"  - {filter_desc}")
                
                if "sort" in query_details and query_details["sort"]:
                    print("\nSorting:")
                    for sort_desc in query_details["sort"]:
                        print(f"  - {sort_desc}")
            
            # Tampilkan jumlah data yang didapatkan
            print(f"\nJumlah data: {result.get('row_count', 0)} baris")
            
            # Tampilkan ringkasan
            if "summary" in result and result["summary"]:
                print("\nRingkasan Data:")
                self._print_wrapped_text(result["summary"])
                
            # Tampilkan preview data jika tersedia
            if "data" in result and result["data"] is not None:
                data = result["data"]
                if len(data) > 0:
                    print("\nPreview Data (5 baris pertama):")
                    try:
                        # Jika data lebih dari 5 baris, ambil 5 baris pertama saja
                        preview_data = data[:5] if len(data) > 5 else data
                        max_field_length = 40  # Batasi panjang nilai field untuk tampilan
                        
                        # Check if data is a DataFrame or a list of dictionaries
                        if hasattr(preview_data, 'iterrows'):  # It's a DataFrame
                            for i, (_, row) in enumerate(preview_data.iterrows(), 1):
                                print(f"\nBaris {i}:")
                                # Get important fields
                                important_fields = ["_key", "status", "disbursement_request_no", 
                                                "disbursement_amount", "partner_name", 
                                                "invoice_number", "payment_method"]
                                
                                for field in important_fields:
                                    if field in row:
                                        value = str(row[field])
                                        if len(value) > max_field_length:
                                            value = value[:max_field_length] + "..."
                                        print(f"  {field}: {value}")
                                
                                # Tambahkan '...' untuk menunjukkan ada field lain
                                print(f"  ... ({len(row)} fields total)")
                        else:  # It's a list of dictionaries
                            for i, row in enumerate(preview_data, 1):
                                print(f"\nBaris {i}:")
                                # Tampilkan beberapa field penting saja untuk keterbacaan
                                important_fields = ["_key", "status", "disbursement_request_no", 
                                                "disbursement_amount", "partner_name", 
                                                "invoice_number", "payment_method"]
                                
                                for field in important_fields:
                                    if isinstance(row, dict) and field in row:
                                        value = str(row[field])
                                        if len(value) > max_field_length:
                                            value = value[:max_field_length] + "..."
                                        print(f"  {field}: {value}")
                                
                                # Tambahkan '...' untuk menunjukkan ada field lain
                                num_fields = len(row) if isinstance(row, dict) else "unknown"
                                print(f"  ... ({num_fields} fields total)")
                    except Exception as e:
                        print(f"Error saat menampilkan preview data: {str(e)}")
            
            # Tampilkan path file local jika data di-export ke Excel
            if "excel_path" in result:
                print(f"\nData disimpan ke file Excel: {result['excel_path']}")
            
            print("-" * 80)
        
        # Tampilkan hasil Email jika ada
        if "email_result" in result:
            print("\n📧 HASIL EMAIL")
            email_result = result["email_result"]
            email_status = email_result.get("status", "unknown")
            email_status_icon = "✓" if email_status == "success" else "⚠️" if email_status == "partial_success" else "✗"
            print(f"{email_status_icon} Status: {email_status.upper()}")
            print(f"Pesan: {email_result.get('message', 'Tidak ada pesan')}")
            
            if "details" in email_result:
                print("\nDetail:")
                details = email_result["details"]
                for key, value in details.items():
                    print(f"  {key}: {value}")
                    
                # Highlight if there is attachment
                if 'has_attachment' in details and details['has_attachment']:
                    print("  📎 Email terkirim dengan lampiran Excel")
                    
                # Highlight if there is GSheet link
                if 'has_gsheet_link' in details and details['has_gsheet_link']:
                    print("  🔗 Email terkirim dengan link Google Sheet")
            
            print("-" * 80)
        
        # Tampilkan hasil Email Reader jika ada
        if "result_type" in result and result.get("result_type") in ["unread_emails", "email_summary", "search_emails", "email_trends", "reply_all_from_sender"]:
            print("\n📨 HASIL EMAIL READER")
            result_type = result.get("result_type")
            data = result.get("data", {})
            
            if result_type == "unread_emails":
                print(f"\nEmail yang belum dibaca: {data.get('count', 0)}")
                self._print_email_list(data.get("emails", []))
                
            elif result_type == "email_summary":
                print(f"\nRingkasan Email untuk {data.get('period_days', 1)} hari terakhir:")
                print(f"Total email: {data.get('total_emails', 0)}")
                print(f"Email belum dibaca: {data.get('unread_emails', 0)}")
                
                if "top_senders" in data:
                    print("\nTop pengirim:")
                    for sender, count in data["top_senders"][:5]:
                        print(f"  - {sender}: {count} email")
                
                if "summary" in data:
                    print("\nRingkasan:")
                    self._print_wrapped_text(data["summary"])
                
                print("\nEmail terbaru:")
                self._print_email_list(data.get("emails", [])[:5])
                
            elif result_type == "search_emails":
                criteria = data.get("search_criteria", {})
                print(f"\nHasil pencarian email:")
                print(f"Kriteria: " + ", ".join([f"{k}='{v}'" for k, v in criteria.items() if v]))
                print(f"Ditemukan: {data.get('count', 0)} email")
                self._print_email_list(data.get("emails", []))
                
            elif result_type == "email_trends":
                print(f"\nAnalisis tren email untuk {data.get('period_days', 7)} hari terakhir:")
                print(f"Total email: {data.get('total_emails', 0)}")
                
                if "top_senders" in data:
                    print("\nTop pengirim:")
                    for sender, count in list(data["top_senders"].items())[:5]:
                        print(f"  - {sender}: {count} email")
                
                if "top_domains" in data:
                    print("\nTop domain:")
                    for domain, count in list(data["top_domains"].items())[:5]:
                        print(f"  - {domain}: {count} email")
                
                if "analysis" in data:
                    print("\nAnalisis:")
                    self._print_wrapped_text(data["analysis"])
                    
            # Tambahan untuk menampilkan hasil reply_all_from_sender
            elif result_type == "reply_all_from_sender":
                print(f"\nHasil membalas email dari {data.get('sender', 'Unknown')}:")
                print(f"Jumlah email ditemukan: {data.get('emails_found', 0)}")
                print(f"Jumlah email dibalas: {data.get('emails_replied', 0)}")
                
                # Tampilkan detail email yang dibalas
                if "replied_emails" in data and data["replied_emails"]:
                    print("\nEmail yang dibalas:")
                    for i, reply_data in enumerate(data["replied_emails"], 1):
                        email = reply_data.get("email", {})
                        reply_result = reply_data.get("reply_result", {})
                        
                        subject = email.get("subject", "No Subject")
                        date = email.get("date", "Unknown date")
                        
                        print(f"\n  {i}. Subjek: {subject}")
                        print(f"     Tanggal: {date}")
                        
                        if "suggested_reply" in reply_result:
                            preview = reply_result["suggested_reply"].strip().replace("\n", " ")
                            if len(preview) > 100:
                                preview = preview[:100] + "..."
                            print(f"     Balasan: {preview}")
                
            print("-" * 80)
    def _print_email_list(self, emails: List[Dict[str, Any]]):
        """Mencetak daftar email"""
        if not emails:
            print("  Tidak ada email.")
            return
        
        for i, email in enumerate(emails, 1):
            read_status = "📖" if email.get("read") else "🆕"
            sender = email.get("sender", "Unknown")
            subject = email.get("subject", "No Subject")
            date = email.get("date", "Unknown date")
            
            print(f"\n  {i}. {read_status} Dari: {sender}")
            print(f"     Subjek: {subject}")
            print(f"     Tanggal: {date}")
            
            # Tampilkan preview body jika ada
            if "body_preview" in email and email["body_preview"]:
                preview = email["body_preview"].strip().replace("\n", " ")
                if len(preview) > 100:
                    preview = preview[:100] + "..."
                print(f"     Preview: {preview}")
            
            # Tampilkan info lampiran jika ada
            if email.get("has_attachments"):
                attachments = email.get("attachments", [])
                print(f"     Lampiran: {len(attachments)} file")
    
    def _print_wrapped_text(self, text: str, width: int = 70):
        """Mencetak teks dengan wrapping"""
        if not text:
            return
        
        wrapped_text = textwrap.fill(text, width=width)
        print(wrapped_text)
    
    def _print_error(self, error_message: str):
        """Menampilkan pesan error"""
        print("\n❌ ERROR")
        print("-" * 80)
        print(f"Terjadi kesalahan: {error_message}")
        print("-" * 80)

def main():
    """Fungsi utama program"""
    # Jalankan interface
    interface = MCPInterface()
    interface._print_banner()
    # Ambil permintaan dari argumen
    while True:
        try:
            user_request = input("your requests: ")
            # Check for exit command
            if user_request.lower() in ["exit", "quit", "keluar", "q"]:
                print("👋 Terima kasih telah menggunakan MCP. Sampai jumpa!")
                break
                
            # Check for help command
            if user_request.lower() in ["help", "bantuan", "tolong", "?"]:
                print("\n📚 BANTUAN")
                print("-" * 80)
                print("Contoh perintah yang dapat Anda gunakan:")
                print("  1. Operasi ArangoDB:")
                print("     • ambil data invoice yang sudah dicairkan dari arango")
                print("     • cari transaksi dengan status pending di arango")
                print("     • ambil data pencairan yang diajukan hari ini")
                print("  2. Operasi Google Sheet:")
                print("     • buat spreadsheet dengan data transaksi dummy")
                print("     • ambil data dari spreadsheet URL")
                print("     • simpan data ke google sheet")
                print("  3. Operasi Email:")
                print("     • kirim data transaksi ke finance@example.com")
                print("     • cek email yang belum dibaca")
                print("     • cari email dari supplier@example.com")
                print("     • balas email dari finance@example.com")
                print("  4. Operasi Gabungan:")
                print("     • ambil data dari arango dan simpan ke spreadsheet")
                print("     • ambil data dari gsheet dan kirim ke john@example.com")
                print("     • ambil data invoice yang sudah cair dan kirim ke finance@company.com")
                print("-" * 80)
                continue
            
            interface.process_request(user_request)
            
        except KeyboardInterrupt:
            print("\n👋 Program dihentikan. Terima kasih telah menggunakan MCP.")
            break
        except Exception as e:
            print(f"\n⚠️ Error tidak terduga: {str(e)}")
            print("Silakan coba lagi dengan permintaan yang berbeda.")
            # Print the full exception for debugging
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Program dihentikan. Terima kasih telah menggunakan MCP.")
    except Exception as e:
        print(f"\n⚠️ Terjadi kesalahan fatal: {str(e)}")
        print("Program akan dimatikan.")
        import traceback
        traceback.print_exc()