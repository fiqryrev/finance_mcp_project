
from dotenv import load_dotenv

load_dotenv()
import re
import json
import os
from typing import Dict, Any, List, Optional, Union
import pandas as pd
from utils.gemini import call_gemini
from utils.gsheet_mcp import GSheetModelContextProtocol
from utils.email_mcp import EmailModelContextProtocol
from utils.email_reader_mcp import EmailReaderMCP
from utils.arango_mcp import ArangoModelContextProtocol  # Import the new ArangoDB MCP

class IntegratedMCP:
    """
    Model Context Protocol terintegrasi yang dapat menangani berbagai jenis permintaan.
    MCP ini menganalisis permintaan pengguna dan mengarahkannya ke MCP yang sesuai.
    """
    
    def __init__(self):
        """Inisialisasi Integrated MCP dengan sub-MCP"""
        self.gsheet_mcp = GSheetModelContextProtocol()
        self.email_mcp = EmailModelContextProtocol()
        self.email_reader_mcp = EmailReaderMCP()
        # Initialize ArangoDB MCP with empty credentials (should be filled from env variables)
        self.arango_mcp = ArangoModelContextProtocol(
            arango_url=os.getenv('ARANGO_URL', ''),
            username=os.getenv('ARANGO_USERNAME', ''),
            password=os.getenv('ARANGO_PASSWORD', '')
        )
    
    def _has_email_request(self, request: str) -> bool:
        """
        Memeriksa apakah permintaan menyebutkan tentang pengiriman email
        """
        email_keywords = ["email", "kirim", "send", "mail", "pesan", "message"]
        return any(keyword in request.lower() for keyword in email_keywords)
    
    def _prepare_file_info_for_email(self, gsheet_result: Dict[str, Any]) -> Union[Dict[str, Any], pd.DataFrame, str, None]:
        """
        Menyiapkan informasi file untuk pengiriman email
        berdasarkan hasil operasi Google Sheet
        
        Dapat mengembalikan:
        - Dictionary dengan informasi spreadsheet (termasuk link)
        - DataFrame data yang perlu disimpan sebagai file Excel
        - Path file Excel yang sudah diekspor
        - None jika tidak ada data yang relevan
        """
        # Cek apakah ada spreadsheet_info di hasil utama
        if "spreadsheet_info" in gsheet_result:
            return gsheet_result["spreadsheet_info"]
        
        # Cek apakah ada excel_path yang sudah disiapkan
        if "excel_path" in gsheet_result:
            return gsheet_result["excel_path"]
        
        # Jika ada results, cek tiap hasil untuk spreadsheet_info
        for step_result in gsheet_result.get("results", []):
            if "spreadsheet_info" in step_result:
                return step_result["spreadsheet_info"]
        
        # Jika tidak ada info sheet tapi ada data terakhir, gunakan itu
        last_data = self.gsheet_mcp.get_last_data()
        if last_data is not None and isinstance(last_data, pd.DataFrame):
            return last_data
        
        # Jika tetap tidak ada, coba dapatkan link saja
        sheet_link = self.gsheet_mcp.get_spreadsheet_link()
        if sheet_link:
            return {"spreadsheet_url": sheet_link}
        
        return None
    
    def analyze_request_intent(self, user_request: str) -> Dict[str, Any]:
        """
        Menganalisis lebih dalam tentang maksud permintaan pengguna
        
        Returns:
            Dictionary dengan informasi detail tentang maksud pengguna
        """
        # Gunakan LLM untuk analisis lebih mendalam
        prompt = f"""
        Analisis permintaan pengguna berikut dan ekstrak informasi penting:
        
        Permintaan pengguna: "{user_request}"
        
        Ekstrak informasi berikut dalam format JSON:
        1. Tipe operasi utama ("gsheet", "arango", "email_send", "email_read", "email_reply", "combined")
        2. Subtipe operasi yang lebih spesifik
           - Untuk gsheet: "create", "read", "save_local", "update"
           - Untuk arango: "query", "search", "analyze"
           - Untuk email_send: "send_message", "send_attachment"
           - Untuk email_read: "check_unread", "search", "summarize", "analyze_trends"
           - Untuk email_reply: "reply", "suggest_reply"
        3. Entitas penting yang disebutkan (email, nama file, URL, collection, dll)
        4. Parameter tambahan (jumlah data, periode waktu, dll)
        5. Format yang diinginkan untuk hasil (link, file Excel, dsb)
        
        Contoh output:
        {{
            "operation_type": "arango",
            "operation_subtype": "query",
            "entities": {{
                "collection": "purchase_invoice_disbursements",
                "filter_field": "status"
            }},
            "parameters": {{
                "status_value": "sudah_dicairkan",
                "limit": 100
            }},
            "format_preference": "excel"
        }}
        """
        
        # Panggil Gemini LLM
        llm_response = call_gemini(prompt)
        
        # Parse JSON dari respons
        try:
            # Coba ekstrak JSON dari respons
            json_match = re.search(r'{.*}', llm_response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group(0))
                return analysis
            
        except Exception as e:
            print(f"Error menganalisis niat permintaan: {e}")
        
        # Fallback jika gagal
        return {
            "operation_type": self._identify_request_type(user_request),
            "operation_subtype": "unspecified",
            "entities": {},
            "parameters": {},
            "format_preference": "default"
        }
    """
    Model Context Protocol terintegrasi yang dapat menangani berbagai jenis permintaan.
    MCP ini menganalisis permintaan pengguna dan mengarahkannya ke MCP yang sesuai.
    """
    
    def __init__(self):
        """Inisialisasi Integrated MCP dengan sub-MCP"""
        self.gsheet_mcp = GSheetModelContextProtocol()
        self.email_mcp = EmailModelContextProtocol()
        self.email_reader_mcp = EmailReaderMCP()
        # Initialize ArangoDB MCP with empty credentials (should be filled from env variables)
        self.arango_mcp = ArangoModelContextProtocol(
            arango_url=os.getenv('ARANGO_URL', ''),
            username=os.getenv('ARANGO_USERNAME', ''),
            password=os.getenv('ARANGO_PASSWORD', '')
        )
    

    def _identify_request_type(self, request: str) -> str:
        """
        Mengidentifikasi jenis permintaan pengguna
        
        Returns:
            String: "gsheet", "arango", "email_send", "email_read", "email_reply", 
                "combined_gsheet_email", "combined_arango_email", "combined_arango_gsheet_email", 
                "combined_arango_gsheet", atau "unknown"
        """
        # Gunakan LLM untuk mengklasifikasikan jenis permintaan
        prompt = f"""
        Kamu adalah asisten yang menganalisis jenis permintaan pengguna.
        
        Permintaan pengguna: "{request}"
        
        Klasifikasikan permintaan pengguna ke dalam salah satu kategori berikut:
        1. "gsheet" - jika permintaan terkait operasi Google Sheet seperti membuat, membaca, atau 
        memperbarui data di spreadsheet, menyimpan data ke lokal
        2. "arango" - jika permintaan terkait operasi ArangoDB seperti query data dari Arango, 
        mencari data di database Arango, atau analisis data dari Arango
        3. "email_send" - jika permintaan terkait MENGIRIM email baru
        4. "email_read" - jika permintaan terkait MEMBACA email (melihat email masuk, membuat ringkasan, mencari email)
        5. "email_reply" - jika permintaan terkait MEMBALAS email yang ada (termasuk membalas banyak email sekaligus)
        6. "combined_gsheet_email" - jika permintaan melibatkan operasi Google Sheet DAN mengirim email
        7. "combined_arango_email" - jika permintaan melibatkan operasi ArangoDB DAN mengirim email
        8. "combined_arango_gsheet" - jika permintaan melibatkan operasi ArangoDB DAN operasi Google Sheet
        9. "combined_arango_gsheet_email" - jika permintaan melibatkan ArangoDB, Google Sheet, DAN email
        10. "unknown" - jika permintaan tidak jelas atau tidak terkait dengan Google Sheet, ArangoDB, atau email
        
        Berikan respons hanya dengan satu kata kategori.
        """
        
        # Panggil Gemini LLM
        llm_response = call_gemini(prompt).strip().lower()
        
        # Manual keyword checking for the triple combination case
        has_arango = any(word in request.lower() for word in ["arango", "arangodb", "database"])
        has_gsheet = any(word in request.lower() for word in ["gsheet", "google sheet", "spreadsheet", "sheet"])
        has_email = any(word in request.lower() for word in ["email", "kirim", "send"]) and re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', request)
        
        # If all three components are present, override to the triple combination
        if has_arango and has_gsheet and has_email:
            return "combined_arango_gsheet_email"
        
        # Ekstrak kategori dari respons
        if "arango" in llm_response and "gsheet" in llm_response and "email" in llm_response:
            return "combined_arango_gsheet_email"
        elif "arango" in llm_response and "email" in llm_response:
            # Double-check for gsheet mentions that might have been missed
            if has_gsheet:
                return "combined_arango_gsheet_email"
            return "combined_arango_email"
        elif "arango" in llm_response and "gsheet" in llm_response:
            # Double-check for email mentions that might have been missed
            if has_email:
                return "combined_arango_gsheet_email"
            return "combined_arango_gsheet"
        elif "gsheet" in llm_response and "email" in llm_response:
            return "combined_gsheet_email"
        elif "arango" in llm_response:
            # Check if the arango request mentions gsheet/spreadsheet/sheet
            if has_gsheet:
                if has_email:
                    return "combined_arango_gsheet_email"
                return "combined_arango_gsheet"
            elif has_email:
                return "combined_arango_email"
            return "arango"
        elif "gsheet" in llm_response:
            return "gsheet"
        elif "email_send" in llm_response:
            return "email_send"
        elif "email_read" in llm_response:
            return "email_read"
        elif "email_reply" in llm_response:
            return "email_reply"
        elif "reply" in llm_response:
            return "email_reply"
        elif "combined" in llm_response:
            if "arango" in llm_response and "gsheet" in llm_response and "email" in llm_response:
                return "combined_arango_gsheet_email"
            elif "arango" in llm_response and "gsheet" in llm_response:
                return "combined_arango_gsheet"
            elif "arango" in llm_response and "email" in llm_response:
                return "combined_arango_email"
            elif "gsheet" in llm_response and "email" in llm_response:
                return "combined_gsheet_email"
        else:
            # Periksa beberapa kata kunci umum untuk kombinasi Arango, GSheet, dan Email
            if has_arango and has_gsheet and has_email:
                return "combined_arango_gsheet_email"
            
            # Periksa beberapa kata kunci umum untuk kombinasi Arango dan GSheet
            elif has_arango and has_gsheet:
                return "combined_arango_gsheet"
                
            # Periksa beberapa kata kunci umum untuk ArangoDB
            elif has_arango:
                return "arango"
                
            # Periksa beberapa kata kunci umum untuk permintaan email reply
            elif any(phrase in request.lower() for phrase in ["balas semua", "reply all", "balas email dari", "reply to all"]):
                return "email_reply"
            
            elif any(word in request.lower() for word in ["balas", "reply", "tanggapi", "jawab"]):
                return "email_reply"
            
        return "unknown"

    def process_request(self, user_request: str) -> Dict[str, Any]:
        """
        Memproses permintaan pengguna berdasarkan jenisnya
        
        Args:
            user_request: Permintaan pengguna dalam bahasa natural
            
        Returns:
            Dictionary berisi hasil proses dan status
        """
        print(f"🔍 Menganalisis permintaan: '{user_request}'")
        
        # Langkah 1: Identifikasi jenis permintaan
        request_type = self._identify_request_type(user_request)
        print(f"🏷️ Jenis permintaan teridentifikasi: {request_type}")
        
        # Langkah 2: Arahkan ke MCP yang sesuai
        result = None
        
        if request_type == "gsheet":
            print("🔀 Mengarahkan ke Google Sheet MCP...")
            result = self.gsheet_mcp.process_request(user_request)
            
            # Cek apakah ada permintaan email setelah operasi gsheet
            if self._has_email_request(user_request):
                print("📧 Permintaan email terdeteksi setelah operasi Google Sheet...")
                # Persiapkan informasi untuk email
                file_info = self._prepare_file_info_for_email(result)
                email_result = self.email_mcp.process_request(user_request, file_info)
                
                # Gabungkan hasil
                result["email_result"] = email_result
        
        elif request_type == "email_send":
            print("🔀 Mengarahkan ke Email Sender MCP...")
            result = self.email_mcp.process_request(user_request)
            
        elif request_type == "email_read":
            print("🔀 Mengarahkan ke Email Reader MCP...")
            result = self.email_reader_mcp.process_request(user_request)
            
        elif request_type == "email_reply":
            print("🔀 Mengarahkan ke Email Reply MCP...")
            result = self.email_reader_mcp.process_request(user_request)
        
        elif request_type == "combined_arango_gsheet_email":
            print("🔀 Menjalankan operasi gabungan ArangoDB, Google Sheet, dan Email...")
            # Step 1: First get data from ArangoDB
            arango_result = self.arango_mcp.process_request(user_request)
            
            # Step 2: Get the data from arango and convert if needed
            data = self.arango_mcp.get_last_data()
            if data is not None:
                # Ensure data is a DataFrame
                if not isinstance(data, pd.DataFrame):
                    try:
                        # Convert to DataFrame if it's a list of dictionaries
                        data = pd.DataFrame(data)
                    except Exception as e:
                        print(f"Warning: Could not convert data to DataFrame: {e}")
                
                # Generate a descriptive name for the spreadsheet
                timestamp = pd.Timestamp.now().strftime('%Y%m%d')
                # Extract description from arango result if available
                description = "data_arango"
                if "query_details" in arango_result and "description" in arango_result["query_details"]:
                    # Get a short version of the description
                    desc = arango_result["query_details"]["description"]
                    # Clean and shorten description for filename
                    clean_desc = re.sub(r'[^\w\s-]', '', desc).strip().lower()
                    clean_desc = re.sub(r'[\s]+', '_', clean_desc)
                    # Take first few words
                    desc_words = clean_desc.split('_')[:3]
                    description = '_'.join(desc_words)
                
                spreadsheet_name = f"{description}_{timestamp}"
                worksheet_name = "Data"
                
                print(f"📊 Menyimpan {len(data)} baris data ke Google Sheet '{spreadsheet_name}'...")
                
                # Create a new GSheet MCP instance to avoid data issues
                gsheet_mcp = GSheetModelContextProtocol()
                
                # Explicitly set the data in the new GSheet MCP
                gsheet_mcp.last_data = data.copy()
                
                # Create gsheet mini-request
                gsheet_request = f"Simpan data ke Google Sheet dengan nama {spreadsheet_name}"
                
                # Process the request with GSheet MCP
                try:
                    gsheet_result = gsheet_mcp.process_request(gsheet_request)
                    
                    # Step 3: Now send the email with Google Sheet link
                    sheet_link = None
                    if "spreadsheet_info" in gsheet_result and "spreadsheet_url" in gsheet_result["spreadsheet_info"]:
                        sheet_link = gsheet_result["spreadsheet_info"]["spreadsheet_url"]
                    
                    # Extract recipient email from request
                    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', user_request)
                    recipient_email = email_match.group(1) if email_match else ""
                    
                    # Prepare rich file info with both sheet link and data context
                    if sheet_link:
                        file_info = {
                            "data_source": "ArangoDB",
                            "query_description": arango_result.get("query_details", {}).get("description", "Data dari ArangoDB"),
                            "row_count": len(data),
                            "recipient_email": recipient_email,
                            "spreadsheet_url": sheet_link,
                            "spreadsheet_name": spreadsheet_name,
                            "worksheet_name": worksheet_name
                        }
                    else:
                        # Fallback to Excel if Google Sheet link not available
                        # Save data as Excel for attachment
                        os.makedirs("./temp", exist_ok=True)
                        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
                        excel_path = f"./temp/arango_data_{timestamp}.xlsx"
                        data.to_excel(excel_path, index=False)
                        
                        file_info = {
                            "file_path": excel_path,
                            "data_source": "ArangoDB",
                            "query_description": arango_result.get("query_details", {}).get("description", "Data dari ArangoDB"),
                            "row_count": len(data),
                            "recipient_email": recipient_email
                        }
                    
                    # Send email with Google Sheet link and/or Excel attachment
                    email_result = self.email_mcp.process_request(user_request, file_info)
                    
                    # Combine results
                    result = {
                        "status": "success" if arango_result["status"] == "success" and 
                                            gsheet_result["status"] == "success" and 
                                            email_result["status"] == "success" else "partial_success",
                        "message": "Operasi gabungan ArangoDB, Google Sheet, dan Email selesai",
                        "arango_result": arango_result,
                        "gsheet_result": gsheet_result,
                        "email_result": email_result
                    }
                    
                    # Add spreadsheet info for easier access
                    if "spreadsheet_info" in gsheet_result:
                        result["spreadsheet_info"] = gsheet_result["spreadsheet_info"]
                    
                except Exception as e:
                    print(f"❌ Error saat menyimpan data ke Google Sheet: {e}")
                    # Fallback to just sending the Excel file by email
                    
                    # Save data as Excel for attachment
                    os.makedirs("./temp", exist_ok=True)
                    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
                    excel_path = f"./temp/arango_data_{timestamp}.xlsx"
                    data.to_excel(excel_path, index=False)
                    
                    # Extract recipient email from request
                    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', user_request)
                    recipient_email = email_match.group(1) if email_match else ""
                    
                    # Prepare file info
                    file_info = {
                        "file_path": excel_path,
                        "data_source": "ArangoDB",
                        "query_description": arango_result.get("query_details", {}).get("description", "Data dari ArangoDB"),
                        "row_count": len(data),
                        "recipient_email": recipient_email
                    }
                    
                    # Send email with attachment
                    email_result = self.email_mcp.process_request(user_request, file_info)
                    
                    result = {
                        "status": "partial_success",
                        "message": f"Operasi ArangoDB selesai, tetapi gagal menyimpan data ke Google Sheet: {e}. Data dikirim sebagai lampiran Excel.",
                        "arango_result": arango_result,
                        "email_result": email_result,
                        "excel_path": excel_path
                    }
            else:
                result = {
                    "status": "partial_success",
                    "message": "Operasi ArangoDB selesai tetapi tidak ada data untuk dikirim",
                    "arango_result": arango_result
                }
            
        elif request_type == "combined_arango_gsheet":
            print("🔀 Menjalankan operasi gabungan ArangoDB dan Google Sheet...")
            # Pertama jalankan operasi arango
            arango_result = self.arango_mcp.process_request(user_request)
            
            # Kemudian simpan hasilnya ke Google Sheet
            data = self.arango_mcp.get_last_data()
            if data is not None:
                # Ensure data is a DataFrame
                if not isinstance(data, pd.DataFrame):
                    try:
                        # Convert to DataFrame if it's a list of dictionaries
                        data = pd.DataFrame(data)
                        print(f"ℹ️ Data berhasil dikonversi ke DataFrame dengan {len(data)} baris dan {len(data.columns)} kolom")
                    except Exception as e:
                        print(f"⚠️ Warning: Could not convert data to DataFrame: {e}")
                        # Try to inspect the data
                        print(f"ℹ️ Tipe data: {type(data)}")
                        if isinstance(data, list) and len(data) > 0:
                            print(f"ℹ️ Tipe elemen pertama: {type(data[0])}")
                            if isinstance(data[0], dict):
                                print(f"ℹ️ Keys dari elemen pertama: {list(data[0].keys())}")
                
                # Generate a descriptive name for the spreadsheet
                timestamp = pd.Timestamp.now().strftime('%Y%m%d')
                # Extract description from arango result if available
                description = "data_arango"
                if "query_details" in arango_result and "description" in arango_result["query_details"]:
                    # Get a short version of the description
                    desc = arango_result["query_details"]["description"]
                    # Clean and shorten description for filename
                    clean_desc = re.sub(r'[^\w\s-]', '', desc).strip().lower()
                    clean_desc = re.sub(r'[\s]+', '_', clean_desc)
                    # Take first few words
                    desc_words = clean_desc.split('_')[:3]
                    description = '_'.join(desc_words)
                
                spreadsheet_name = f"{description}_{timestamp}"
                worksheet_name = "Data"
                
                print(f"📊 Menyimpan {len(data)} baris data ke Google Sheet '{spreadsheet_name}'...")
                
                # Create a new GSheet MCP instance to avoid data issues
                gsheet_mcp = GSheetModelContextProtocol()
                
                # Explicitly set the data in the new GSheet MCP
                gsheet_mcp.last_data = data.copy()
                
                # Create direct parameters for push to Google Sheet
                try:
                    # Directly use the gsheet_mcp's to_push_data method for more control
                    spreadsheet_url = gsheet_mcp.gsheet.to_push_data(
                        data,
                        spreadsheet_name,
                        worksheet_name,
                        append=False
                    )
                    
                    print(f"✅ Data berhasil disimpan ke Google Sheet: {spreadsheet_url}")
                    
                    # Create spreadsheet info
                    spreadsheet_info = {
                        "spreadsheet_name": spreadsheet_name,
                        "worksheet_name": worksheet_name,
                        "spreadsheet_url": spreadsheet_url if spreadsheet_url else ""
                    }
                    
                    # Create gsheet result
                    gsheet_result = {
                        "status": "success",
                        "message": f"Data berhasil disimpan ke Google Sheet '{spreadsheet_name}'",
                        "spreadsheet_info": spreadsheet_info,
                        "steps_summary": [f"Menyimpan {len(data)} baris data ke Google Sheet '{spreadsheet_name}'"]
                    }
                    
                    # Combine results
                    result = {
                        "status": "success",
                        "message": "Operasi gabungan ArangoDB dan Google Sheet selesai",
                        "arango_result": arango_result,
                        "gsheet_result": gsheet_result,
                        "spreadsheet_info": spreadsheet_info
                    }
                    
                except Exception as e:
                    print(f"❌ Error saat menyimpan data ke Google Sheet: {e}")
                    
                    # Try alternative approach - create a mini-request
                    try:
                        print("🔄 Mencoba pendekatan alternatif untuk menyimpan data...")
                        # Create a mini-request for GSheet MCP
                        gsheet_request = f"Simpan data ke Google Sheet dengan nama {spreadsheet_name}"
                        
                        # Process the request with GSheet MCP
                        gsheet_result = gsheet_mcp.process_request(gsheet_request)
                        
                        # Combine results
                        result = {
                            "status": "success" if arango_result["status"] == "success" and gsheet_result["status"] == "success" else "partial_success",
                            "message": "Operasi gabungan ArangoDB dan Google Sheet selesai",
                            "arango_result": arango_result,
                            "gsheet_result": gsheet_result
                        }
                        
                        # Add spreadsheet info for easier access
                        if "spreadsheet_info" in gsheet_result:
                            result["spreadsheet_info"] = gsheet_result["spreadsheet_info"]
                            
                    except Exception as e2:
                        print(f"❌ Error saat mencoba pendekatan alternatif: {e2}")
                        # Save to Excel as a fallback
                        os.makedirs("./temp", exist_ok=True)
                        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
                        excel_path = f"./temp/arango_data_{timestamp}.xlsx"
                        
                        try:
                            data.to_excel(excel_path, index=False)
                            print(f"✅ Data disimpan ke file Excel sebagai fallback: {excel_path}")
                            
                            result = {
                                "status": "partial_success",
                                "message": f"Operasi ArangoDB selesai tetapi gagal menyimpan data ke Google Sheet. Data disimpan ke Excel: {excel_path}",
                                "arango_result": arango_result,
                                "excel_path": excel_path
                            }
                        except Exception as e3:
                            print(f"❌ Error saat menyimpan ke Excel: {e3}")
                            result = {
                                "status": "partial_success",
                                "message": f"Operasi ArangoDB selesai tetapi gagal menyimpan data ke Google Sheet dan Excel: {e3}",
                                "arango_result": arango_result
                            }
            else:
                print("⚠️ Tidak ada data yang tersedia dari ArangoDB")
                result = {
                    "status": "partial_success",
                    "message": "Operasi ArangoDB selesai tetapi tidak ada data untuk disimpan ke Google Sheet",
                    "arango_result": arango_result
                }
            
        elif request_type == "arango":
            print("🔀 Mengarahkan ke ArangoDB MCP...")
            result = self.arango_mcp.process_request(user_request)
            
            # Cek apakah ada permintaan email setelah operasi arango
            if self._has_email_request(user_request):
                print("📧 Permintaan email terdeteksi setelah operasi ArangoDB...")
                # Persiapkan data untuk email
                data = self.arango_mcp.get_last_data()
                if data is not None and isinstance(data, pd.DataFrame):
                    # Simpan data sebagai Excel untuk attachment
                    os.makedirs("./temp", exist_ok=True)
                    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
                    excel_path = f"./temp/arango_data_{timestamp}.xlsx"
                    data.to_excel(excel_path, index=False)
                    
                    # Kirim email dengan attachment
                    email_result = self.email_mcp.process_request(user_request, excel_path)
                    result["email_result"] = email_result
        
        elif request_type == "combined_gsheet_email":
            print("🔀 Menjalankan operasi gabungan GSheet dan Email...")
            # Pertama jalankan operasi gsheet
            gsheet_result = self.gsheet_mcp.process_request(user_request)
            
            # Kemudian kirim email dengan hasil dari gsheet
            file_info = self._prepare_file_info_for_email(gsheet_result)
            email_result = self.email_mcp.process_request(user_request, file_info)
            
            # Gabungkan hasil
            result = {
                "status": "success" if gsheet_result["status"] == "success" and email_result["status"] == "success" else "partial_success",
                "message": "Operasi gabungan GSheet dan Email selesai",
                "gsheet_result": gsheet_result,
                "email_result": email_result
            }
            
        elif request_type == "combined_arango_email":
            print("🔀 Menjalankan operasi gabungan ArangoDB dan Email...")
            # Pertama jalankan operasi arango
            arango_result = self.arango_mcp.process_request(user_request)
            
            # Kemudian kirim email dengan hasil dari arango
            data = self.arango_mcp.get_last_data()
            
            # Ensure data is a DataFrame or convert it
            if data is not None:
                if not isinstance(data, pd.DataFrame):
                    try:
                        # Convert to DataFrame if it's a list of dictionaries
                        data = pd.DataFrame(data)
                    except Exception as e:
                        print(f"Warning: Could not convert data to DataFrame: {e}")
                
                # Simpan data sebagai Excel untuk attachment
                os.makedirs("./temp", exist_ok=True)
                timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
                excel_path = f"./temp/arango_data_{timestamp}.xlsx"
                
                try:
                    data.to_excel(excel_path, index=False)
                    print(f"💾 Data disimpan ke file Excel: {excel_path}")
                    
                    # Extract recipient email from request
                    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', user_request)
                    recipient_email = email_match.group(1) if email_match else ""
                    
                    # Prepare file info with additional context
                    file_info = {
                        "file_path": excel_path,
                        "data_source": "ArangoDB",
                        "query_description": arango_result.get("query_details", {}).get("description", "Data dari ArangoDB"),
                        "row_count": len(data),
                        "recipient_email": recipient_email
                    }
                    
                    # Kirim email dengan attachment dan context
                    email_result = self.email_mcp.process_request(user_request, file_info)
                    
                    # Gabungkan hasil
                    result = {
                        "status": "success" if arango_result["status"] == "success" and email_result["status"] == "success" else "partial_success",
                        "message": "Operasi gabungan ArangoDB dan Email selesai",
                        "arango_result": arango_result,
                        "email_result": email_result,
                        "excel_path": excel_path
                    }
                except Exception as e:
                    print(f"❌ Error saat menyimpan data ke Excel: {e}")
                    result = {
                        "status": "partial_success",
                        "message": f"Operasi ArangoDB selesai tetapi gagal menyimpan data ke Excel: {e}",
                        "arango_result": arango_result
                    }
            else:
                result = {
                    "status": "partial_success",
                    "message": "Operasi ArangoDB selesai tetapi tidak ada data untuk dikirim via email",
                    "arango_result": arango_result
                }
        
        else:  # unknown
            print("❓ Jenis permintaan tidak dikenali")
            result = {
                "status": "error",
                "message": "Jenis permintaan tidak dikenali. Saya dapat membantu Anda dengan operasi Google Sheet, ArangoDB, mengirim email, membaca email, atau membalas email."
            }
        
        return result
        
    def _has_email_request(self, request: str) -> bool:
        """
        Memeriksa apakah permintaan menyebutkan tentang pengiriman email
        """
        email_keywords = ["email", "kirim", "send", "mail", "pesan", "message"]
        return any(keyword in request.lower() for keyword in email_keywords)
    
    def _prepare_file_info_for_email(self, gsheet_result: Dict[str, Any]) -> Union[Dict[str, Any], pd.DataFrame, str, None]:
        """
        Menyiapkan informasi file untuk pengiriman email
        berdasarkan hasil operasi Google Sheet
        
        Dapat mengembalikan:
        - Dictionary dengan informasi spreadsheet (termasuk link)
        - DataFrame data yang perlu disimpan sebagai file Excel
        - Path file Excel yang sudah diekspor
        - None jika tidak ada data yang relevan
        """
        # Cek apakah ada spreadsheet_info di hasil utama
        if "spreadsheet_info" in gsheet_result:
            return gsheet_result["spreadsheet_info"]
        
        # Cek apakah ada excel_path yang sudah disiapkan
        if "excel_path" in gsheet_result:
            return gsheet_result["excel_path"]
        
        # Jika ada results, cek tiap hasil untuk spreadsheet_info
        for step_result in gsheet_result.get("results", []):
            if "spreadsheet_info" in step_result:
                return step_result["spreadsheet_info"]
        
        # Jika tidak ada info sheet tapi ada data terakhir, gunakan itu
        last_data = self.gsheet_mcp.get_last_data()
        if last_data is not None and isinstance(last_data, pd.DataFrame):
            return last_data
        
        # Jika tetap tidak ada, coba dapatkan link saja
        sheet_link = self.gsheet_mcp.get_spreadsheet_link()
        if sheet_link:
            return {"spreadsheet_url": sheet_link}
        
        return None
    
    def analyze_request_intent(self, user_request: str) -> Dict[str, Any]:
        """
        Menganalisis lebih dalam tentang maksud permintaan pengguna
        
        Returns:
            Dictionary dengan informasi detail tentang maksud pengguna
        """
        # Gunakan LLM untuk analisis lebih mendalam
        prompt = f"""
        Analisis permintaan pengguna berikut dan ekstrak informasi penting:
        
        Permintaan pengguna: "{user_request}"
        
        Ekstrak informasi berikut dalam format JSON:
        1. Tipe operasi utama ("gsheet", "arango", "email_send", "email_read", "email_reply", "combined")
        2. Subtipe operasi yang lebih spesifik
           - Untuk gsheet: "create", "read", "save_local", "update"
           - Untuk arango: "query", "search", "analyze"
           - Untuk email_send: "send_message", "send_attachment"
           - Untuk email_read: "check_unread", "search", "summarize", "analyze_trends"
           - Untuk email_reply: "reply", "suggest_reply"
        3. Entitas penting yang disebutkan (email, nama file, URL, collection, dll)
        4. Parameter tambahan (jumlah data, periode waktu, dll)
        5. Format yang diinginkan untuk hasil (link, file Excel, dsb)
        
        Contoh output:
        {{
            "operation_type": "arango",
            "operation_subtype": "query",
            "entities": {{
                "collection": "purchase_invoice_disbursements",
                "filter_field": "status"
            }},
            "parameters": {{
                "status_value": "sudah_dicairkan",
                "limit": 100
            }},
            "format_preference": "excel"
        }}
        """
        
        # Panggil Gemini LLM
        llm_response = call_gemini(prompt)
        
        # Parse JSON dari respons
        try:
            # Coba ekstrak JSON dari respons
            json_match = re.search(r'{.*}', llm_response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group(0))
                return analysis
            
        except Exception as e:
            print(f"Error menganalisis niat permintaan: {e}")
        
        # Fallback jika gagal
        return {
            "operation_type": self._identify_request_type(user_request),
            "operation_subtype": "unspecified",
            "entities": {},
            "parameters": {},
            "format_preference": "default"
        }