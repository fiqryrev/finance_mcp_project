import smtplib
import os
import re
import pandas as pd
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, List, Optional, Union, Tuple
from dotenv import load_dotenv
from utils.gemini import call_gemini

# Load environment variables
load_dotenv()

class EmailModelContextProtocol:
    """
    Model Context Protocol untuk mengirim email.
    MCP ini menerima permintaan pengguna untuk mengirim email,
    menyesuaikan isi email menggunakan LLM, dan mengirim email.
    """
    
    def __init__(self):
        """Inisialisasi Email MCP"""
        self.sender_email = os.getenv('EMAIL_SENDER')
        self.sender_password = os.getenv("EMAIL_PASSWORD")
        self.sender_name = os.getenv("EMAIL_SENDER_NAME", "Aril")
        
        if not self.sender_email or not self.sender_password:
            raise ValueError("EMAIL_SENDER dan EMAIL_PASSWORD harus diatur pada file .env")
    
    def process_request(self, user_request: str, file_info: Optional[Union[str, Dict[str, Any], pd.DataFrame]] = None) -> Dict[str, Any]:
        """
        Memproses permintaan pengguna terkait pengiriman email
        
        Args:
            user_request: Permintaan pengguna dalam bahasa natural
            file_info: Informasi file yang dapat berupa:
                      - Path ke file (string)
                      - Dictionary info dari Google Sheet (dengan link, nama, dll)
                      - DataFrame untuk disimpan sebagai file
            
        Returns:
            Dictionary berisi hasil proses dan status
        """
        print(f"🔍 Menganalisis permintaan email: '{user_request}'")
        
        # Langkah 1: Analisis permintaan untuk mendapatkan detail email
        email_details = self._analyze_email_request(user_request)
        
        # Langkah 2: Proses file_info menjadi attachment dan/atau links
        attachment_path, gsheet_link = self._process_file_info(file_info, email_details)
        
        # Langkah 3: Generate konten email yang sesuai menggunakan LLM
        subject, email_content = self._generate_email_content_and_subject(
            user_request,
            email_details,
            bool(attachment_path),
            bool(gsheet_link),
            gsheet_link
        )
        
        print(f"📝 Konten email berhasil dibuat")
        
        # Langkah 4: Kirim email
        print(f"📧 Mengirim email ke: {email_details['recipient_email']}")
        try:
            self.send_email(
                attachment_path,
                email_details['recipient_email'],
                subject,
                email_content,
                email_details.get('cc_email', ''),
                gsheet_link
            )
            print(f"✅ Email berhasil dikirim ke {email_details['recipient_email']}")
            
            return {
                "status": "success",
                "message": f"Email berhasil dikirim ke {email_details['recipient_email']}",
                "details": {
                    "recipient": email_details['recipient_email'],
                    "subject": subject,
                    "has_attachment": attachment_path is not None,
                    "has_gsheet_link": gsheet_link is not None
                }
            }
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Gagal mengirim email: {error_msg}")
            return {
                "status": "error",
                "message": f"Gagal mengirim email: {error_msg}"
            }
    
    def _analyze_email_request(self, request: str) -> Dict[str, Any]:
        """
        Menganalisis permintaan pengguna untuk mendapatkan detail email
        """
        # Gunakan LLM untuk mengekstrak detail dari permintaan
        prompt = f"""
        Kamu adalah asisten yang menganalisis permintaan pengguna untuk mengirim email.
        
        Permintaan pengguna: "{request}"
        
        Ekstrak informasi berikut dari permintaan:
        1. Email penerima (jika tidak disebutkan, isi dengan "")
        2. Nama penerima (jika disebutkan, atau gunakan "")
        3. Topik atau konteks email (apa yang sedang dibicarakan)
        4. Tujuan pengiriman email (memberi info, melampirkan file, berbagi data, dll)
        5. Email CC (jika disebutkan)
        6. Path file untuk dilampirkan (jika disebutkan)
        7. Tingkat formalitas (formal, semi-formal, casual)
        8. Bahasa yang diinginkan (Indonesia, Inggris, dll)
        
        Berikan respons dalam format JSON yang valid seperti berikut:
        {{
            "recipient_email": "email@example.com",
            "recipient_name": "Nama Penerima",
            "topic": "Topik atau Konteks Email",
            "purpose": "Tujuan Email",
            "cc_email": "cc@example.com",
            "file_path": "/path/to/file.xlsx",
            "formality": "formal/semi-formal/casual",
            "language": "Indonesia/English"
        }}
        
        Jika beberapa informasi tidak disebutkan, berikan string kosong.
        """
        
        # Panggil Gemini LLM
        llm_response = call_gemini(prompt)
        
        try:
            # Coba ekstrak JSON dari respons
            json_match = re.search(r'{.*}', llm_response, re.DOTALL)
            if json_match:
                import json
                email_details = json.loads(json_match.group(0))
            else:
                # Fallback jika tidak bisa parse JSON
                recipient_email = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', request)
                topic_match = re.search(r'(?:report|laporan|topik|topic)[:\s]+([a-zA-Z0-9\s]+)', request, re.IGNORECASE)
                
                email_details = {
                    "recipient_email": recipient_email.group(1) if recipient_email else "",
                    "recipient_name": "",
                    "topic": topic_match.group(1).strip() if topic_match else "Data Report",
                    "purpose": "share information",
                    "cc_email": "",
                    "file_path": "",
                    "formality": "formal" if "formal" in request.lower() else "semi-formal",
                    "language": "Indonesia" if any(word in request.lower() for word in ["bahasa", "indonesia"]) else "English"
                }
            
            # Pastikan semua field ada
            required_fields = ["recipient_email", "recipient_name", "topic", "purpose", 
                              "cc_email", "file_path", "formality", "language"]
            for field in required_fields:
                if field not in email_details:
                    email_details[field] = ""
            
            return email_details
            
        except Exception as e:
            print(f"Error menganalisis permintaan email: {e}")
            # Nilai default jika analisis gagal
            return {
                "recipient_email": "",
                "recipient_name": "",
                "topic": "Data Report",
                "purpose": "share information",
                "cc_email": "",
                "file_path": "",
                "formality": "semi-formal",
                "language": "English"
            }
    
    def _process_file_info(self, file_info: Optional[Union[str, Dict[str, Any], pd.DataFrame]], 
                            email_details: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
            """
            Memproses informasi file yang akan dilampirkan/dibagikan
            
            Args:
                file_info: Informasi file (path, dict info, atau DataFrame)
                email_details: Detail email dari analisis permintaan
                
            Returns:
                Tuple[attachment_path, gsheet_link]
            """
            attachment_path = None
            gsheet_link = None
            
            # Jika tidak ada file_info, cek dari email_details
            if file_info is None and email_details.get("file_path"):
                file_info = email_details["file_path"]
            
            # Jika masih tidak ada file_info, kembalikan None, None
            if file_info is None:
                return None, None
            
            # Proses berdasarkan tipe file_info
            if isinstance(file_info, str):
                # Jika string, anggap sebagai path file
                if os.path.exists(file_info):
                    attachment_path = file_info
                    print(f"🔍 File ditemukan di: {attachment_path}")
                else:
                    # Jika bukan path yang valid, mungkin ini adalah link
                    if file_info.startswith(("http://", "https://", "www.")):
                        gsheet_link = file_info
                    else:
                        print(f"⚠️ Warning: Path file tidak valid: {file_info}")
            
            elif isinstance(file_info, dict):
                print(f"📦 Processing file info dictionary: {list(file_info.keys())}")
                
                # Jika dictionary, cari link dan/atau path
                if "link" in file_info:
                    gsheet_link = file_info["link"]
                elif "spreadsheet_url" in file_info:
                    gsheet_link = file_info["spreadsheet_url"]
                
                # Jika ada path file di dictionary
                if "file_path" in file_info and file_info["file_path"]:
                    attachment_path = file_info["file_path"]
                    print(f"📎 File akan dilampirkan dari: {attachment_path}")
                    
                    # Copy additional metadata to email_details for better email content
                    if "data_source" in file_info:
                        email_details["data_source"] = file_info["data_source"]
                    if "query_description" in file_info:
                        email_details["query_description"] = file_info["query_description"]
                    if "row_count" in file_info:
                        email_details["row_count"] = file_info["row_count"]
                
                # Jika ada spreadsheet_name, buat link GSheet dummy (pada implementasi nyata, ini akan jadi link sebenarnya)
                elif "spreadsheet_name" in file_info and not gsheet_link:
                    sheet_name = file_info["spreadsheet_name"]
                    gsheet_link = f"https://docs.google.com/spreadsheets/d/{self._generate_dummy_gsheet_id(sheet_name)}/edit"
            
            elif isinstance(file_info, pd.DataFrame):
                # Jika DataFrame, simpan sebagai Excel
                os.makedirs("./temp", exist_ok=True)
                filename = f"./temp/data_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                try:
                    file_info.to_excel(filename, index=False)
                    attachment_path = filename
                    print(f"💾 Data disimpan ke file Excel: {filename}")
                    
                    # Add data info to email_details
                    email_details["row_count"] = len(file_info)
                except Exception as e:
                    print(f"❌ Error saat menyimpan DataFrame ke Excel: {e}")
            
            return attachment_path, gsheet_link
    
    def _generate_dummy_gsheet_id(self, sheet_name: str) -> str:
        """
        Membuat ID Google Sheet dummy (untuk tujuan demo)
        Pada implementasi nyata, ini akan diganti dengan ID Google Sheet sebenarnya
        """
        import hashlib
        # Buat ID acak berdasarkan nama sheet
        return hashlib.md5(sheet_name.encode()).hexdigest()[:26]
    
    def _generate_email_content_and_subject(self, user_request: str, email_details: Dict[str, Any],
                                            has_attachment: bool, has_link: bool, 
                                            link: Optional[str] = None) -> Tuple[str, str]:
        """
        Menggunakan LLM untuk menghasilkan subject dan konten email
        berdasarkan konteks dan permintaan pengguna
        
        Returns:
            Tuple[subject, html_content]
        """
        # Buat prompt untuk LLM berdasarkan konteks
        language = email_details["language"]
        formality = email_details["formality"]
        topic = email_details["topic"]
        recipient_name = email_details["recipient_name"]
        purpose = email_details["purpose"]
        
        # Get additional details if available
        data_source = email_details.get("data_source", "")
        query_description = email_details.get("query_description", "")
        row_count = email_details.get("row_count", "")
        
        attachment_details = ""
        if has_attachment:
            if data_source == "ArangoDB":
                attachment_details = (f"Email ini memiliki file lampiran berisi data dari ArangoDB. "
                                f"File Excel terlampir berisi {row_count} baris data invoice "
                                f"yang sedang diajukan pencairannya hari ini. "
                                f"Data mencakup informasi seperti ID transaksi, status pencairan, "
                                f"jumlah pembayaran, nama partner, dan metode pembayaran.")
            else:
                attachment_details = "Email ini memiliki file lampiran."
        else:
            attachment_details = "Email ini tidak memiliki file lampiran."
        
        link_details = ""
        if has_link:
            if "google" in link.lower() or "spreadsheet" in link.lower():
                link_details = (f"Email ini menyertakan link Google Sheet yang berisi data yang diminta. "
                            f"Anda dapat mengakses dan mengedit data secara langsung melalui link berikut: {link}")
            else:
                link_details = f"Email ini memiliki link yang dibagikan: {link}"
        else:
            link_details = "Email ini tidak menyertakan link Google Sheet. Data disediakan sebagai lampiran Excel."
        
        prompt = f"""
        Buatkan subject dan konten email berdasarkan informasi berikut:
        
        Permintaan pengguna: "{user_request}"
        Topik/konteks: {topic}
        Tujuan email: {purpose}
        Nama penerima: {recipient_name if recipient_name else "tidak disebutkan"}
        Tingkat formalitas: {formality}
        Bahasa: {language}
        Pengirim: {self.sender_name}
        
        Detail tambahan:
        - {attachment_details}
        - {link_details}
        
        Hasilkan subject email dan konten email dalam format HTML.
        Email harus profesional, konkret dan spesifik (tidak menggunakan placeholder), 
        dan sesuai dengan tingkat formalitas yang diminta.
        
        Jangan pernah menyertakan text placeholder seperti [isi dengan X] atau [contoh: Y].
        Selalu menggunakan pernyataan spesifik tentang data (seperti "data invoice pencairan yang diajukan hari ini").
        
        Jika ada link Google Sheet, buatkan call-to-action yang jelas untuk mengakses sheet tersebut.
        Jika ada data dari ArangoDB, jelaskan bahwa data telah dilampirkan sebagai file Excel dan berikan informasi 
        detail tentang isi lampiran, termasuk jumlah baris, jenis data, dan field-field penting.
        
        Format respons:
        ```subject
        Subject email di sini
        ```
        
        ```html
        Konten email dalam format HTML di sini
        ```
        
        Jangan sertakan placeholder atau teks template. Buatlah email yang terdengar natural dan personal.
        """
        
        # Panggil Gemini LLM
        llm_response = call_gemini(prompt)
        
        # Ekstrak subject dari respons
        subject_match = re.search(r'```subject\s*(.*?)\s*```', llm_response, re.DOTALL)
        subject = subject_match.group(1).strip() if subject_match else "Your Data Report"
        
        # Ekstrak HTML dari respons
        html_match = re.search(r'```html\s*(.*?)\s*```', llm_response, re.DOTALL)
        html_content = html_match.group(1).strip() if html_match else llm_response
        
        # Jika tidak dalam format HTML, bungkus dengan tag HTML
        if not re.search(r'<html>', html_content, re.IGNORECASE):
            html_content = f"""
            <html>
            <body>
                {html_content}
            </body>
            </html>
            """
        
        return subject, html_content
    def send_email(self, attachment_path: Optional[str], recipient_email: str, 
                  subject: str, html_content: str, cc_email: str = "", 
                  gsheet_link: Optional[str] = None) -> None:
        """
        Mengirim email dengan lampiran dan/atau link Google Sheet
        
        Args:
            attachment_path: Path ke file yang akan dilampirkan (opsional)
            recipient_email: Email penerima
            subject: Subject email
            html_content: Konten HTML email
            cc_email: Email CC (opsional)
            gsheet_link: Link Google Sheet (opsional)
        """
        # Validasi email penerima
        if not recipient_email:
            raise ValueError("Email penerima tidak boleh kosong")
            
        # Buat email
        message = MIMEMultipart()
        message['Subject'] = subject
        message['From'] = self.sender_email
        message['To'] = recipient_email
        
        if cc_email:
            message['Cc'] = cc_email
        
        # Inject link Google Sheet ke dalam konten HTML jika belum disertakan
        if gsheet_link and gsheet_link not in html_content:
            # Pastikan tidak mengganggu struktur HTML yang sudah ada
            if "</body>" in html_content:
                html_content = html_content.replace("</body>", 
                    f'<p>Link to Google Sheet: <a href="{gsheet_link}">{gsheet_link}</a></p></body>')
        
        # Attach HTML content
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Attach file jika tersedia
        if attachment_path:
            try:
                with open(attachment_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    
                    # Ambil nama file dari path
                    filename = os.path.basename(attachment_path)
                    part.add_header("Content-Disposition", f"attachment; filename= {filename}")
                    message.attach(part)
            except FileNotFoundError:
                raise FileNotFoundError(f"File tidak ditemukan: {attachment_path}")
            except Exception as e:
                raise Exception(f"Error saat melampirkan file: {str(e)}")
        
        # Kirim email
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.sender_email, self.sender_password)
                recipients = [recipient_email]
                if cc_email:
                    recipients.append(cc_email)
                server.sendmail(self.sender_email, recipients, message.as_string())
        except smtplib.SMTPAuthenticationError:
            raise Exception("Autentikasi email gagal. Periksa EMAIL_SENDER dan EMAIL_PASSWORD.")
        except Exception as e:
            raise Exception(f"Error saat mengirim email: {str(e)}")