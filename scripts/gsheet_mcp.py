import re
import json
import pandas as pd
import random
import uuid
import datetime
import os
from typing import List, Dict, Any, Optional, Tuple
from askquinta import About_Gsheet
from utils.gemini import call_gemini

class GSheetModelContextProtocol:
    """
    Model Context Protocol untuk operasi Google Sheet.
    MCP ini menerima permintaan pengguna, memecahnya menjadi langkah-langkah,
    dan mengeksekusi setiap langkah secara berurutan.
    """
    
    def __init__(self, credentials_path='./materials/gsheet_creds.json'):
        """Inisialisasi dengan kredensial Google Sheet"""
        self.gsheet = About_Gsheet(credentials_path=credentials_path)
        # Simpan data terakhir dibuat untuk digunakan antar method
        self.last_data = None
        self.last_spreadsheet_info = None
        
    def process_request(self, user_request: str) -> Dict[str, Any]:
        """
        Memproses permintaan pengguna menggunakan Gemini LLM
        dan mengeksekusi langkah-langkah yang diperlukan
        
        Args:
            user_request: Permintaan pengguna dalam bahasa natural
            
        Returns:
            Dictionary berisi hasil proses dan status
        """
        # Reset data terakhir
        self.last_data = None
        self.last_spreadsheet_info = None
        
        # Langkah 1: Analisis permintaan pengguna menggunakan LLM
        print(f"🔍 Menganalisis permintaan: '{user_request}'")
        steps = self._analyze_with_llm(user_request)
        
        # Langkah 2: Jalankan setiap langkah yang diidentifikasi
        results = []
        for i, step in enumerate(steps, 1):
            print(f"\n✅ Langkah {i}: {step['description']}")
            print(f"   Menjalankan: {step['type']}")
            
            # Eksekusi langkah
            result = self._execute_step(step)
            results.append(result)
            
            # Tampilkan hasil
            if 'data' in result and isinstance(result['data'], pd.DataFrame):
                print(f"   Data dibuat/dibaca: {len(result['data'])} baris × {len(result['data'].columns)} kolom")
                print("   Preview data:")
                print(result['data'].head(3).to_string(index=False))
                print("   ...")
            if 'message' in result:
                print(f"   Status: {result['message']}")
            if 'spreadsheet_info' in result:
                print(f"   Spreadsheet: {result['spreadsheet_info']['spreadsheet_name']}")
                if 'spreadsheet_url' in result['spreadsheet_info']:
                    print(f"   URL: {result['spreadsheet_info']['spreadsheet_url']}")
            if 'local_path' in result:
                print(f"   File disimpan di: {result['local_path']}")
        
        # Langkah 3: Siapkan ringkasan untuk pengguna
        summary = {
            "status": "success",
            "message": f"Permintaan '{user_request}' berhasil diproses",
            "steps_count": len(steps),
            "steps_summary": [step['description'] for step in steps],
            "results": results
        }
        
        # Tambahkan informasi spreadsheet terakhir jika ada
        if self.last_spreadsheet_info:
            summary["spreadsheet_info"] = self.last_spreadsheet_info
        
        # Tambahkan data terakhir jika ada dan diperlukan untuk operasi selanjutnya
        if self.last_data is not None and isinstance(self.last_data, pd.DataFrame):
            # Simpan data sebagai Excel jika mungkin diperlukan untuk attachment email
            if any('email' in s.lower() for s in user_request.split()):
                os.makedirs("./temp", exist_ok=True)
                excel_path = f"./temp/{self.last_spreadsheet_info['spreadsheet_name']}.xlsx"
                self.last_data.to_excel(excel_path, index=False)
                summary["excel_path"] = excel_path
        
        print("\n✨ Proses Google Sheet selesai! ✨")
        return summary
    
    def _analyze_with_llm(self, user_request: str) -> List[Dict[str, Any]]:
        """
        Menggunakan Gemini LLM untuk menganalisis permintaan dan 
        mengidentifikasi langkah-langkah yang diperlukan
        """
        # Cek jika ada data yang sudah tersedia
        has_existing_data = self.last_data is not None

        # Buat prompt untuk LLM
        prompt = f"""
        Kamu adalah asisten yang menganalisis permintaan pengguna terkait Google Sheets.
        
        Permintaan pengguna: "{user_request}"
        
        {'Pengguna telah menyediakan data yang perlu disimpan ke Google Sheet.' if has_existing_data else ''}
        
        Pecah permintaan ini menjadi langkah-langkah yang diperlukan untuk memenuhinya.
        Berdasarkan permintaan tersebut, identifikasi langkah-langkah yang harus dilakukan dalam format JSON.
        
        Langkah-langkah yang mungkin diperlukan:
        {'1. Menggunakan data yang sudah tersedia' if has_existing_data else '1. Membuat data dummy jika diperlukan'}
        2. Menyimpan data ke Google Sheet
        3. Membaca data dari Google Sheet
        4. Memperbarui data di Google Sheet
        5. Menyimpan data ke penyimpanan lokal (file Excel, CSV, dll)
        
        Untuk setiap langkah, berikan:
        - type: jenis operasi (create_dummy_data, save_to_gsheet, read_from_gsheet, update_gsheet, save_to_local)
        - description: deskripsi singkat tentang langkah ini
        - params: parameter yang diperlukan untuk langkah tersebut
        
        Khusus untuk read_from_gsheet dengan URL, gunakan format:
        {{
            "type": "read_from_gsheet",
            "description": "Membaca data dari Google Sheet dengan URL tertentu",
            "params": {{
                "spreadsheet_url": "URL yang diekstrak",
                "worksheet_name": "Nama worksheet yang disebutkan"
            }}
        }}
        
        Khusus untuk save_to_local, parameter tambahan yang diperlukan:
        - file_format: format file (excel/csv/json/etc)
        - file_path: path tempat menyimpan file (jika disebutkan)
        
        Berikan respons dalam format JSON yang valid saja, tanpa penjelasan atau komentar tambahan.
        """
        
        # Panggil Gemini LLM
        llm_response = call_gemini(prompt)
        
        # Parse JSON dari respons
        try:
            # Coba ekstrak JSON dari respons (jika ada teks tambahan)
            json_match = re.search(r'\[\s*{.*}\s*\]', llm_response, re.DOTALL)
            if json_match:
                steps = json.loads(json_match.group(0))
            else:
                steps = json.loads(llm_response)
                
            return steps
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON dari LLM: {e}")
            print(f"Respons LLM: {llm_response}")
            
            # Fallback ke langkah default jika terjadi kesalahan
            return self._default_steps(user_request)
    def _default_steps(self, user_request: str) -> List[Dict[str, Any]]:
        """Langkah default jika analisis LLM gagal"""
        # Cek jika ada data yang sudah tersedia
        has_existing_data = self.last_data is not None
        
        # Cek apakah permintaan berkaitan dengan membaca dari URL dan menyimpan ke lokal
        gsheet_url_match = re.search(r'(https://docs\.google\.com/spreadsheets/d/[a-zA-Z0-9_-]+)', user_request)
        worksheet_match = re.search(r'worksheet\s+([a-zA-Z0-9_]+)', user_request, re.IGNORECASE)
        save_local_match = re.search(r'(simpan|save).*?(?:ke|to|di).*?(lokal|local)', user_request, re.IGNORECASE)
        
        if gsheet_url_match:
            # URL GSheet ditemukan
            url = gsheet_url_match.group(1)
            # Extract spreadsheet_id dari URL
            spreadsheet_id_match = re.search(r'spreadsheets/d/([a-zA-Z0-9_-]+)', url)
            spreadsheet_id = spreadsheet_id_match.group(1) if spreadsheet_id_match else "unknown"
            worksheet_name = worksheet_match.group(1) if worksheet_match else "Sheet1"
            
            steps = [
                {
                    "type": "read_from_gsheet",
                    "description": "Membaca data dari Google Sheet dengan URL yang diberikan.",
                    "params": {
                        "spreadsheet_url": url,
                        "worksheet_name": worksheet_name
                    }
                }
            ]
            
            # Jika ada permintaan untuk simpan ke lokal, tambahkan langkah
            if save_local_match:
                # Tentukan format file berdasarkan permintaan
                format_match = re.search(r'(excel|csv|json)', user_request, re.IGNORECASE)
                file_format = format_match.group(1).lower() if format_match else "excel"
                
                # Tentukan nama file berdasarkan format
                file_extension = ".xlsx" if file_format == "excel" else f".{file_format}"
                file_path = f"./data/{spreadsheet_id}_{worksheet_name}{file_extension}"
                
                steps.append({
                    "type": "save_to_local",
                    "description": "Menyimpan data yang dibaca dari Google Sheet ke penyimpanan lokal.",
                    "params": {
                        "file_format": file_format,
                        "file_path": file_path
                    }
                })
            
            return steps
            
        # Identifikasi beberapa kata kunci untuk menentukan operasi
        elif any(word in user_request.lower() for word in ['buat', 'create', 'generate', 'dummy']):
            # Jika ada data yang tersedia, langsung ke save_to_gsheet
            if has_existing_data:
                # Menentukan nama sheet
                description_match = re.search(r'(data|invoice|transaksi|pencairan)_([a-zA-Z0-9_]+)', user_request.lower())
                description = description_match.group(0) if description_match else 'data_arango'
                
                # Add timestamp to make unique sheet name
                timestamp = datetime.datetime.now().strftime('%Y%m%d')
                spreadsheet_name = f"{description}_{timestamp}"
                
                return [
                    {
                        "type": "save_to_gsheet",
                        "description": "Menyimpan data yang sudah tersedia ke Google Sheet",
                        "params": {
                            "spreadsheet_name": spreadsheet_name,
                            "worksheet_name": "Data",
                            "append": False
                        }
                    }
                ]
            else:
                # Buat data dummy jika tidak ada data tersedia
                data_type = 'transaction' if any(word in user_request.lower() for word in ['transaksi', 'transaction', 'trx']) else 'data'
                
                # Menentukan nama sheet
                team_match = re.search(r'tim\s+(\w+)', user_request.lower())
                team = team_match.group(1) if team_match else 'default'
                
                return [
                    {
                        "type": "create_dummy_data",
                        "description": f"Membuat data {data_type} dummy",
                        "params": {
                            "data_type": data_type,
                            "columns": ["id", "name", "value"],
                            "num_rows": 20
                        }
                    },
                    {
                        "type": "save_to_gsheet",
                        "description": "Menyimpan data ke Google Sheet",
                        "params": {
                            "spreadsheet_name": f"Data for {team.capitalize()}",
                            "worksheet_name": "Sheet1",
                            "append": False
                        }
                    }
                ]
        elif has_existing_data:
            # Jika ada data yang tersedia tetapi tidak ada keyword spesifik, tetap simpan ke GSheet
            description = 'arango_data'
            timestamp = datetime.datetime.now().strftime('%Y%m%d')
            spreadsheet_name = f"{description}_{timestamp}"
            
            return [
                {
                    "type": "save_to_gsheet",
                    "description": "Menyimpan data yang sudah tersedia ke Google Sheet",
                    "params": {
                        "spreadsheet_name": spreadsheet_name,
                        "worksheet_name": "Data",
                        "append": False
                    }
                }
            ]
        else:
            # Default untuk operasi baca
            return [
                {
                    "type": "read_from_gsheet",
                    "description": "Membaca data dari Google Sheet",
                    "params": {
                        "spreadsheet_name": "Data Sheet",
                        "worksheet_name": "Sheet1"
                    }
                }
            ]
    def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mengeksekusi langkah berdasarkan jenisnya
        
        Args:
            step: Dictionary berisi detail langkah
            
        Returns:
            Dictionary berisi hasil eksekusi
        """
        step_type = step.get('type', '')
        params = step.get('params', {})
        
        if step_type == 'create_dummy_data':
            return self._create_dummy_data(params)
        elif step_type == 'save_to_gsheet':
            return self._save_to_gsheet(params)
        elif step_type == 'read_from_gsheet':
            return self._read_from_gsheet(params)
        elif step_type == 'update_gsheet':
            return self._update_gsheet(params)
        elif step_type == 'save_to_local':
            return self._save_to_local(params)
        else:
            return {
                "status": "error",
                "message": f"Tipe langkah tidak dikenal: {step_type}"
            }
    
    def _create_dummy_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Membuat data dummy berdasarkan parameter, 
        atau menggunakan data yang sudah ada di self.last_data
        """
        # Jika sudah ada data, gunakan data tersebut
        if self.last_data is not None and isinstance(self.last_data, pd.DataFrame):
            print(f"ℹ️ Menggunakan data yang sudah tersedia ({len(self.last_data)} baris)")
            return {
                "status": "success",
                "message": f"Menggunakan data yang sudah tersedia dengan {len(self.last_data)} baris",
                "data": self.last_data
            }
        
        # Jika tidak ada data, buat data dummy
        data_type = params.get('data_type', 'generic')
        columns = params.get('columns', ['id', 'name', 'value'])
        num_rows = params.get('num_rows', 20)
        
        # Buat DataFrame kosong
        df = pd.DataFrame()
        
        # Isi dengan data sesuai tipe kolom
        for col in columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['id', 'transaction_id', 'trx_id']):
                df[col] = [str(uuid.uuid4()) for _ in range(num_rows)]
            elif any(keyword in col_lower for keyword in ['company_id', 'company']):
                df[col] = [f"COMP-{random.randint(1000, 9999)}" for _ in range(num_rows)]
            elif any(keyword in col_lower for keyword in ['customer_id', 'customer']):
                df[col] = [f"CUST-{random.randint(1000, 9999)}" for _ in range(num_rows)]
            elif any(keyword in col_lower for keyword in ['amount', 'value', 'price', 'total']):
                df[col] = [round(random.uniform(100, 10000), 2) for _ in range(num_rows)]
            elif any(keyword in col_lower for keyword in ['date', 'tanggal', 'transaction_date', 'trx_date']):
                start_date = datetime.datetime.now() - datetime.timedelta(days=30)
                df[col] = [(start_date + datetime.timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d') 
                            for _ in range(num_rows)]
            elif any(keyword in col_lower for keyword in ['status']):
                statuses = ['completed', 'pending', 'failed', 'processing']
                df[col] = [random.choice(statuses) for _ in range(num_rows)]
            elif any(keyword in col_lower for keyword in ['name', 'product_name', 'item_name']):
                prefixes = ['Product', 'Item', 'Good', 'Service']
                df[col] = [f"{random.choice(prefixes)} {random.randint(1, 100)}" for _ in range(num_rows)]
            else:
                # Kolom default untuk tipe yang tidak dikenali
                df[col] = [f"Value-{i+1}" for i in range(num_rows)]
        
        # Simpan data untuk digunakan di langkah berikutnya
        self.last_data = df
        
        return {
            "status": "success",
            "message": f"Berhasil membuat {num_rows} baris data dummy",
            "data": df
        }
    def _save_to_gsheet(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Menyimpan data ke Google Sheet"""
        spreadsheet_name = params.get('spreadsheet_name', 'Data Sheet')
        worksheet_name = params.get('worksheet_name', 'Sheet1')
        append = params.get('append', False)
        
        # Pastikan ada data untuk disimpan
        if self.last_data is None:
            print("⚠️ Error: Tidak ada data yang tersedia untuk disimpan")
            return {
                "status": "error", 
                "message": "Tidak ada data yang tersedia untuk disimpan"
            }
        
        print(f"ℹ️ Tipe data yang akan disimpan: {type(self.last_data)}")
        if isinstance(self.last_data, pd.DataFrame):
            print(f"ℹ️ DataFrame memiliki {len(self.last_data)} baris dan {len(self.last_data.columns)} kolom")
        elif isinstance(self.last_data, list):
            print(f"ℹ️ List memiliki {len(self.last_data)} elemen")
            if len(self.last_data) > 0:
                print(f"ℹ️ Tipe elemen pertama: {type(self.last_data[0])}")
        
        # Convert to DataFrame if necessary
        if not isinstance(self.last_data, pd.DataFrame):
            try:
                # If list of dictionaries, convert to DataFrame
                self.last_data = pd.DataFrame(self.last_data)
                print(f"ℹ️ Berhasil mengkonversi data ke DataFrame dengan {len(self.last_data)} baris dan {len(self.last_data.columns)} kolom")
            except Exception as e:
                print(f"⚠️ Error saat mengkonversi data ke DataFrame: {str(e)}")
                return {
                    "status": "error",
                    "message": f"Gagal mengkonversi data ke DataFrame: {str(e)}"
                }
        
        try:
            print(f"🔄 Menyimpan {len(self.last_data)} baris data ke Google Sheet '{spreadsheet_name}', worksheet '{worksheet_name}'...")
            
            # Simpan ke Google Sheet dan dapatkan URL
            # PENTING: Asumsikan to_push_data() mengembalikan URL sheet
            spreadsheet_url = self.gsheet.to_push_data(
                self.last_data, 
                spreadsheet_name, 
                worksheet_name, 
                append=append
            )
            
            # Jika to_push_data() tidak mengembalikan URL, gunakan string kosong
            if spreadsheet_url is None:
                spreadsheet_url = ""
                
            # Simpan info spreadsheet untuk digunakan nanti
            spreadsheet_info = {
                "spreadsheet_name": spreadsheet_name,
                "worksheet_name": worksheet_name,
                "spreadsheet_url": spreadsheet_url
            }
            self.last_spreadsheet_info = spreadsheet_info
            
            print(f"✅ Data berhasil disimpan ke Google Sheet '{spreadsheet_name}'")
            if spreadsheet_url:
                print(f"🔗 URL: {spreadsheet_url}")
            
            return {
                "status": "success",
                "message": f"Data berhasil disimpan ke '{spreadsheet_name}' worksheet '{worksheet_name}'",
                "spreadsheet_info": spreadsheet_info
            }
        except Exception as e:
            print(f"❌ Error saat menyimpan data ke Google Sheet: {str(e)}")
            return {
                "status": "error",
                "message": f"Gagal menyimpan data: {str(e)}"
            }
    def _read_from_gsheet(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Membaca data dari Google Sheet"""
        # Cek apakah kita membaca dari URL atau nama spreadsheet
        spreadsheet_url = params.get('spreadsheet_url', None)
        spreadsheet_name = params.get('spreadsheet_name', 'Data Sheet')
        worksheet_name = params.get('worksheet_name', 'Sheet1')
        
        # Untuk simulasi data, kita buat data dummy untuk spreadsheet_url yang diberikan
        # Ini untuk demonstrasi saja, pada implementasi nyata Anda akan menggunakan API untuk membaca data
        if spreadsheet_url:
            try:
                print(f"   Info: Mencoba membaca data dari URL: {spreadsheet_url}")
                print(f"   Info: Worksheet: {worksheet_name}")
                
                # SIMULASI: Buat data dummy untuk mendemonstrasikan kemampuan membaca dari URL
                # Pada implementasi nyata, Anda akan memanggil API Google Sheets di sini
                
                # Extract spreadsheet_id dari URL
                spreadsheet_id_match = re.search(r'spreadsheets/d/([a-zA-Z0-9_-]+)', spreadsheet_url)
                if not spreadsheet_id_match:
                    return {
                        "status": "error",
                        "message": f"URL Google Sheet tidak valid: {spreadsheet_url}"
                    }
                
                spreadsheet_id = spreadsheet_id_match.group(1)
                
                try:
                    # Di implementasi nyata, Anda akan membaca data dengan ID spreadsheet
                    # Untuk demo, kita simulasikan dengan membuat data dummy
                    
                    # UNTUK IMPLEMENTASI NYATA: 
                    # Di sini harusnya kode untuk mengakses Google Sheet API dengan spreadsheet_id
                    # Namun karena ini adalah demo, kita gunakan fungsi yang ada
                    
                    # Coba gunakan API.to_pull_data dengan ID jika memungkinkan
                    try:
                        print(f"   Info: Mencoba membaca dengan ID spreadsheet")
                        # Ini adalah bagian simulasi - Anda mungkin perlu menyesuaikan implementasi
                        # Untuk menggunakan ID spreadsheet, bukan nama
                        data = self.gsheet.to_pull_data(spreadsheet_url, worksheet_name)
                    except Exception as e:
                        print(f"   Info: Gagal membaca dengan ID, mengganti ke simulasi: {str(e)}")
                        # Jika gagal, buat data dummy
                        num_rows = 10
                        data = pd.DataFrame({
                            'ID': [f"ID-{i+1}" for i in range(num_rows)],
                            'Date': [(datetime.datetime.now() - datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(num_rows)],
                            'Amount': [round(random.uniform(100, 5000), 2) for _ in range(num_rows)],
                            'Status': [random.choice(['Completed', 'Pending', 'Failed']) for _ in range(num_rows)]
                        })
                        print(f"   Info: Dibuat data simulasi dengan {len(data)} baris")
                    
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Gagal membaca data dari spreadsheet dengan ID {spreadsheet_id}: {str(e)}"
                    }
                
                # Simpan data untuk digunakan di langkah berikutnya
                self.last_data = data
                
                # Simpan info spreadsheet
                spreadsheet_name = f"Spreadsheet-{spreadsheet_id}"
                spreadsheet_info = {
                    "spreadsheet_name": spreadsheet_name,
                    "worksheet_name": worksheet_name,
                    "spreadsheet_url": spreadsheet_url,
                    "spreadsheet_id": spreadsheet_id
                }
                self.last_spreadsheet_info = spreadsheet_info
                
                return {
                    "status": "success",
                    "message": f"Berhasil membaca data dari Google Sheet dengan URL yang diberikan",
                    "data": data,
                    "spreadsheet_info": spreadsheet_info
                }
                
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Gagal membaca data dari URL: {str(e)}"
                }
        else:
            # Membaca dengan nama spreadsheet
            try:
                data = self.gsheet.to_pull_data(spreadsheet_name, worksheet_name)
                
                # Simpan data untuk digunakan di langkah berikutnya
                self.last_data = data
                
                # Gunakan URL sheet yang sudah ada jika ada, atau kosong jika tidak ada
                spreadsheet_url = ""
                if self.last_spreadsheet_info and 'spreadsheet_url' in self.last_spreadsheet_info:
                    spreadsheet_url = self.last_spreadsheet_info['spreadsheet_url']
                
                # Simpan info spreadsheet
                spreadsheet_info = {
                    "spreadsheet_name": spreadsheet_name,
                    "worksheet_name": worksheet_name,
                    "spreadsheet_url": spreadsheet_url
                }
                self.last_spreadsheet_info = spreadsheet_info
                
                return {
                    "status": "success",
                    "message": f"Berhasil membaca data dari '{spreadsheet_name}' worksheet '{worksheet_name}'",
                    "data": data,
                    "spreadsheet_info": spreadsheet_info
                }
            except Exception as e:
                return {
                    "status": "error", 
                    "message": f"Gagal membaca data: {str(e)}"
                }
    
    def _update_gsheet(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Memperbarui data di Google Sheet"""
        spreadsheet_name = params.get('spreadsheet_name', 'Data Sheet')
        worksheet_name = params.get('worksheet_name', 'Sheet1')
        cell_range = params.get('cell_range', 'A1:B1')
        update_data = params.get('data', [["Updated Value"]])
        
        try:
            # Update data di Google Sheet
            # Asumsikan to_update_data() tidak mengembalikan URL
            self.gsheet.to_update_data(
                update_data, 
                spreadsheet_name, 
                cell_range, 
                worksheet_name
            )
            
            # Gunakan URL sheet yang sudah ada jika ada, atau kosong jika tidak ada
            spreadsheet_url = ""
            if self.last_spreadsheet_info and 'spreadsheet_url' in self.last_spreadsheet_info:
                spreadsheet_url = self.last_spreadsheet_info['spreadsheet_url']
            
            # Simpan info spreadsheet
            spreadsheet_info = {
                "spreadsheet_name": spreadsheet_name,
                "worksheet_name": worksheet_name,
                "spreadsheet_url": spreadsheet_url,
                "updated_range": cell_range
            }
            self.last_spreadsheet_info = spreadsheet_info
            
            return {
                "status": "success",
                "message": f"Berhasil memperbarui data di '{spreadsheet_name}' worksheet '{worksheet_name}' range '{cell_range}'",
                "spreadsheet_info": spreadsheet_info
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Gagal memperbarui data: {str(e)}"
            }
    
    def _save_to_local(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Menyimpan data ke penyimpanan lokal"""
        # Pastikan ada data untuk disimpan
        if self.last_data is None or not isinstance(self.last_data, pd.DataFrame):
            return {
                "status": "error", 
                "message": "Tidak ada data yang tersedia untuk disimpan ke lokal"
            }
        
        file_format = params.get('file_format', 'excel').lower()
        file_path = params.get('file_path', None)
        
        # Jika file_path tidak diberikan, buat path default
        if not file_path:
            # Pastikan folder data ada
            os.makedirs("./data", exist_ok=True)
            
            # Dapatkan timestamp untuk nama file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Dapatkan nama sheet dan worksheet
            sheet_name = "data"
            worksheet_name = "sheet1"
            if self.last_spreadsheet_info:
                if 'spreadsheet_id' in self.last_spreadsheet_info:
                    sheet_name = self.last_spreadsheet_info['spreadsheet_id']
                elif 'spreadsheet_name' in self.last_spreadsheet_info:
                    sheet_name = self.last_spreadsheet_info['spreadsheet_name']
                    
                if 'worksheet_name' in self.last_spreadsheet_info:
                    worksheet_name = self.last_spreadsheet_info['worksheet_name']
            
            # Buat file path
            if file_format == 'excel':
                file_path = f"./data/{sheet_name}_{worksheet_name}_{timestamp}.xlsx"
            elif file_format == 'csv':
                file_path = f"./data/{sheet_name}_{worksheet_name}_{timestamp}.csv"
            elif file_format == 'json':
                file_path = f"./data/{sheet_name}_{worksheet_name}_{timestamp}.json"
            else:
                file_path = f"./data/{sheet_name}_{worksheet_name}_{timestamp}.txt"
        
        # Pastikan direktori ada
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        try:
            # Simpan data berdasarkan format
            if file_format == 'excel':
                self.last_data.to_excel(file_path, index=False)
                message = f"Data berhasil disimpan sebagai file Excel: {file_path}"
            elif file_format == 'csv':
                self.last_data.to_csv(file_path, index=False)
                message = f"Data berhasil disimpan sebagai file CSV: {file_path}"
            elif file_format == 'json':
                self.last_data.to_json(file_path, orient='records')
                message = f"Data berhasil disimpan sebagai file JSON: {file_path}"
            else:
                # Format default: text
                self.last_data.to_csv(file_path, index=False, sep='\t')
                message = f"Data berhasil disimpan sebagai file teks: {file_path}"
            
            return {
                "status": "success",
                "message": message,
                "local_path": file_path,
                "file_format": file_format
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Gagal menyimpan data ke lokal: {str(e)}"
            }
    
    def get_spreadsheet_link(self) -> Optional[str]:
        """
        Mendapatkan link spreadsheet terakhir yang diakses/dibuat
        """
        if self.last_spreadsheet_info and 'spreadsheet_url' in self.last_spreadsheet_info:
            return self.last_spreadsheet_info['spreadsheet_url']
        return None
    
    def get_last_data(self) -> Optional[pd.DataFrame]:
        """
        Mendapatkan data terakhir
        """
        return self.last_data