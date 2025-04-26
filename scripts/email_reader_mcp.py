import os
import re
import imaplib
import email
import smtplib
import pandas as pd
import datetime
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, List, Optional, Union, Tuple
from dotenv import load_dotenv
from utils.gemini import call_gemini

# Load environment variables
load_dotenv()

class EmailReaderMCP:
    """
    Model Context Protocol untuk membaca dan membalas email.
    Fungsionalitas meliputi:
    1. Membaca email yang belum dibaca
    2. Membuat ringkasan email harian
    3. Mencari email dari pengirim tertentu
    4. Menganalisis tren email
    5. Membalas email
    """
    
    def __init__(self):
        """Inisialisasi Email Reader MCP"""
        # Konfigurasi email account untuk membaca
        self.email_address = os.getenv('EMAIL_SENDER')
        self.email_password = os.getenv("EMAIL_PASSWORD")
        self.sender_name = os.getenv("EMAIL_SENDER_NAME")
        
        # Konfigurasi IMAP untuk membaca email
        self.imap_server = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
        self.imap_port = int(os.getenv("EMAIL_IMAP_PORT", "993"))
        
        # Konfigurasi SMTP untuk mengirim email
        self.smtp_server = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "465"))
        
        if not self.email_address or not self.email_password:
            raise ValueError("EMAIL_SENDER dan EMAIL_PASSWORD harus diatur pada file .env")
        
        # Cache untuk email yang sudah diambil
        self.email_cache = {}
    
    def process_request(self, user_request: str) -> Dict[str, Any]:
        """
        Memproses permintaan pengguna terkait email
        
        Args:
            user_request: Permintaan pengguna dalam bahasa natural
            
        Returns:
            Dictionary berisi hasil proses dan status
        """
        print(f"🔍 Menganalisis permintaan email reading: '{user_request}'")
        
        # Analisis permintaan dengan LLM
        request_type, request_params = self._analyze_email_request(user_request)
        
        # Proses permintaan berdasarkan jenisnya
        print(f"📨 Permintaan diidentifikasi sebagai: {request_type}")
        
        try:
            # Tambahkan case untuk reply_all_from_sender
            if request_type == "reply_all_from_sender":
                sender = request_params.get('sender', '')
                days = request_params.get('days', 7)
                limit = request_params.get('limit', 10)
                
                # Hapus parameter ini agar tidak mengganggu search_emails
                today_only = request_params.pop('today_only', False)
                
                # Cari email dari pengirim tertentu
                search_result = self.search_emails(
                    sender=sender, 
                    subject='', 
                    days=days, 
                    limit=limit
                )
                
                # Jika tidak ada email yang ditemukan
                if not search_result['emails']:
                    return {
                        "status": "success",
                        "message": f"Tidak ada email dari {sender} dalam {days} hari terakhir",
                        "result_type": "reply_all_from_sender",
                        "data": {
                            "emails_found": 0,
                            "emails_replied": 0,
                            "sender": sender,
                            "days": days
                        }
                    }
                
                # Balas semua email yang ditemukan
                replied_emails = []
                for email in search_result['emails']:
                    # Generate dan kirim balasan
                    reply_result = self.suggest_and_reply_email(email['id'])
                    replied_emails.append({
                        "email": email,
                        "reply_result": reply_result
                    })
                
                return {
                    "status": "success",
                    "message": f"Berhasil membalas {len(replied_emails)} email dari {sender}",
                    "result_type": "reply_all_from_sender",
                    "data": {
                        "emails_found": len(search_result['emails']),
                        "emails_replied": len(replied_emails),
                        "replied_emails": replied_emails,
                        "sender": sender,
                        "days": days
                    }
                }
            
            elif request_type == "unread_emails":
                result = self.get_unread_emails(limit=request_params.get('limit', 10))
                return {
                    "status": "success",
                    "message": f"Berhasil mendapatkan {len(result['emails'])} email yang belum dibaca",
                    "result_type": "unread_emails",
                    "data": result
                }
                
            elif request_type == "email_summary":
                days = request_params.get('days', 1)
                result = self.get_email_summary(days=days)
                return {
                    "status": "success",
                    "message": f"Berhasil membuat summary email untuk {days} hari terakhir",
                    "result_type": "email_summary",
                    "data": result
                }
                
            elif request_type == "search_emails":
                sender = request_params.get('sender', '')
                subject = request_params.get('subject', '')
                days = request_params.get('days', 7)
                limit = request_params.get('limit', 10)
                
                result = self.search_emails(
                    sender=sender, 
                    subject=subject, 
                    days=days, 
                    limit=limit
                )
                
                return {
                    "status": "success",
                    "message": f"Berhasil menemukan {len(result['emails'])} email yang sesuai kriteria",
                    "result_type": "search_emails",
                    "data": result
                }
                
            elif request_type == "email_trends":
                days = request_params.get('days', 7)
                result = self.analyze_email_trends(days=days)
                return {
                    "status": "success",
                    "message": f"Berhasil menganalisis tren email untuk {days} hari terakhir",
                    "result_type": "email_trends",
                    "data": result
                }
            
            elif request_type == "reply_email":
                email_id = request_params.get('email_id', '')
                reply_content = request_params.get('reply_content', '')
                suggestion = request_params.get('suggestion', False)
                
                # Jika email_id tidak ada, coba cari dari indeks
                if not email_id and 'email_index' in request_params:
                    # Ambil email terbaru dan pilih berdasarkan indeks
                    recent_emails = self.get_unread_emails(limit=10)
                    email_index = request_params.get('email_index')
                    
                    if 0 <= email_index < len(recent_emails['emails']):
                        email_id = recent_emails['emails'][email_index]['id']
                
                if not email_id:
                    return {
                        "status": "error",
                        "message": "ID email tidak ditemukan atau tidak valid",
                        "result_type": "reply_email"
                    }
                
                # Jika mode suggestion, buat draft reply
                if suggestion:
                    result = self.suggest_email_reply(email_id)
                    return {
                        "status": "success",
                        "message": "Berhasil membuat saran balasan email",
                        "result_type": "reply_suggestion",
                        "data": result
                    }
                
                # Jika ada reply_content, kirim reply
                if reply_content:
                    result = self.reply_to_email(email_id, reply_content)
                    return {
                        "status": "success",
                        "message": "Berhasil membalas email",
                        "result_type": "reply_email",
                        "data": result
                    }
                
                # Jika tidak ada reply_content, buat draft dan kirim
                result = self.suggest_and_reply_email(email_id)
                return {
                    "status": "success",
                    "message": "Berhasil membuat dan mengirim balasan email",
                    "result_type": "reply_email",
                    "data": result
                }
                
            else:
                return {
                    "status": "error",
                    "message": "Jenis permintaan tidak dikenali"
                }
                
        except Exception as e:
            print(f"❌ Error saat memproses permintaan email: {str(e)}")
            return {
                "status": "error",
                "message": f"Gagal memproses permintaan: {str(e)}"
            }
    
    def _analyze_email_request(self, request: str) -> Tuple[str, Dict[str, Any]]:
        """
        Menganalisis permintaan pengguna untuk mengidentifikasi jenis operasi
        dan parameter yang diperlukan
        
        Args:
            request: Permintaan pengguna
            
        Returns:
            Tuple berisi (jenis_permintaan, parameter)
        """
        # Gunakan LLM untuk mengidentifikasi jenis permintaan dan parameter
        prompt = f"""
        Kamu adalah asisten yang menganalisis permintaan terkait pembacaan dan pembalasan email.
        
        Permintaan pengguna: "{request}"
        
        Klasifikasikan permintaan ke dalam salah satu kategori berikut:
        1. "unread_emails" - untuk melihat email yang belum dibaca
        2. "email_summary" - untuk membuat ringkasan email dalam periode tertentu
        3. "search_emails" - untuk mencari email dari pengirim atau dengan subjek tertentu
        4. "email_trends" - untuk menganalisis tren email (pengirim yang paling sering, waktu paling aktif, dll)
        5. "reply_email" - untuk membalas email tertentu
        6. "reply_all_from_sender" - untuk membalas semua email dari pengirim tertentu
        
        Untuk setiap kategori, ekstrak parameter berikut (jika relevan):
        - limit: jumlah email yang ingin dilihat (default 10)
        - days: jumlah hari ke belakang untuk dicari (default 7)
        - sender: email pengirim yang ingin dicari (jika ada)
        - subject: subjek email yang ingin dicari (jika ada)
        - email_id: ID email yang ingin dibalas (jika disebutkan)
        - email_index: Indeks email dari daftar (jika disebutkan, misalnya "balas email pertama")
        - reply_content: Konten balasan email (jika disebutkan)
        - suggestion: Boolean apakah hanya ingin mendapatkan saran balasan (true jika disebutkan)
        - today_only: Boolean untuk mencari email hanya hari ini (true jika disebutkan kata "hari ini")
        
        Berikan respons dalam format JSON seperti ini:
        {{
            "request_type": "kategori_permintaan",
            "params": {{
                "limit": 10,
                "days": 7,
                "sender": "email@example.com",
                "subject": "kata kunci subjek",
                "email_id": "email_id",
                "email_index": 0,
                "reply_content": "Isi balasan",
                "suggestion": true/false,
                "today_only": true/false
            }}
        }}
        
        Hanya sertakan parameter yang relevan dan disebutkan/tersirat dalam permintaan.
        """
        
        try:
            # Panggil Gemini LLM
            llm_response = call_gemini(prompt)
            
            # Parse JSON dari respons
            json_match = re.search(r'{.*}', llm_response, re.DOTALL)
            if json_match:
                import json
                analysis = json.loads(json_match.group(0))
                request_type = analysis.get("request_type", "unread_emails")
                params = analysis.get("params", {})
                
                # Deteksi permintaan untuk membalas semua email dari pengirim tertentu
                if request_type == "reply_all_from_sender":
                    # Tetapkan parameter days=0 jika today_only=True
                    if params.get("today_only", False):
                        params["days"] = 1
                    
                    return request_type, params
                
                return request_type, params
        except Exception as e:
            print(f"Error saat menganalisis permintaan: {e}")
        
        # Fallback untuk analisis sederhana
        if "balas semua" in request.lower() or "reply all" in request.lower():
            # Cari sender
            sender_match = re.search(r'dari\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', request, re.IGNORECASE)
            sender = sender_match.group(1) if sender_match else ""
            
            # Cek apakah hanya untuk hari ini
            today_only = "hari ini" in request.lower() or "today" in request.lower()
            days = 1 if today_only else 7
            
            return "reply_all_from_sender", {
                "sender": sender,
                "days": days,
                "today_only": today_only,
                "suggestion": True
            }
        
        # Fallback untuk analisis sederhana
        if any(word in request.lower() for word in ["balas", "reply", "jawab"]):
            # Cek apakah ada indikasi email tertentu
            email_index = -1
            index_patterns = [
                r"(?:email|mail)\s+(?:ke-|ke\s+)?(\d+)",  # "email ke-2", "email ke 3"
                r"(\d+)(?:st|nd|rd|th)?\s+(?:email|mail)",  # "2nd email", "3 email"
                r"(?:pertama|kedua|ketiga|keempat|kelima|keenam|ketujuh|kedelapan|kesembilan|kesepuluh)"  # "email pertama", "email kedua"
            ]
            
            for pattern in index_patterns:
                index_match = re.search(pattern, request.lower())
                if index_match:
                    try:
                        # Parse angka dari match
                        match_text = index_match.group(1)
                        if match_text.isdigit():
                            email_index = int(match_text) - 1  # Convert to 0-based index
                        else:
                            # Convert words to index
                            word_to_index = {
                                "pertama": 0, "kedua": 1, "ketiga": 2, "keempat": 3, "kelima": 4,
                                "keenam": 5, "ketujuh": 6, "kedelapan": 7, "kesembilan": 8, "kesepuluh": 9
                            }
                            email_index = word_to_index.get(match_text, -1)
                    except:
                        email_index = 0
                    break
            
            # Cek apakah hanya minta saran
            suggestion = any(word in request.lower() for word in ["saran", "suggest", "rekomendasi", "draft"])
            
            # Cek apakah ada konten balasan
            reply_content = ""
            content_match = re.search(r'(?:dengan|dgn|dengan isi|content|body)[:\s]+["\']?([^"\']+)["\']?', request, re.IGNORECASE)
            if content_match:
                reply_content = content_match.group(1).strip()
            
            return "reply_email", {
                "email_index": email_index if email_index >= 0 else 0,
                "suggestion": suggestion,
                "reply_content": reply_content
            }
            
        elif any(word in request.lower() for word in ["belum dibaca", "unread"]):
            return "unread_emails", {"limit": 10}
        elif any(word in request.lower() for word in ["summary", "ringkasan", "rangkuman"]):
            return "email_summary", {"days": 1}
        elif any(word in request.lower() for word in ["cari", "search", "dari", "from"]):
            sender_match = re.search(r'dari\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', request, re.IGNORECASE)
            sender = sender_match.group(1) if sender_match else ""
            return "search_emails", {"sender": sender, "days": 7, "limit": 10}
        elif any(word in request.lower() for word in ["trend", "tren", "analisis", "analyze"]):
            return "email_trends", {"days": 7}
        else:
            return "unread_emails", {"limit": 10}
    
    def get_unread_emails(self, limit: int = 10) -> Dict[str, Any]:
        """
        Mendapatkan daftar email yang belum dibaca
        
        Args:
            limit: Jumlah email yang akan diambil
            
        Returns:
            Dictionary berisi info email yang belum dibaca
        """
        print(f"📥 Mengambil {limit} email yang belum dibaca...")
        
        try:
            # Buat koneksi ke IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.email_password)
            mail.select("INBOX")
            
            # Cari email yang belum dibaca
            status, data = mail.search(None, "UNSEEN")
            if status != "OK":
                raise Exception(f"Gagal mencari email yang belum dibaca: {status}")
            
            # Ambil ID email
            email_ids = data[0].split()
            
            # Terapkan limit
            if limit > 0:
                email_ids = email_ids[:limit]
            
            # Ambil data email
            emails = []
            for email_id in email_ids:
                email_data = self._fetch_email(mail, email_id)
                if email_data:
                    emails.append(email_data)
            
            mail.close()
            mail.logout()
            
            return {
                "count": len(emails),
                "emails": emails
            }
            
        except Exception as e:
            print(f"Error saat mengambil email yang belum dibaca: {str(e)}")
            return {
                "count": 0,
                "emails": [],
                "error": str(e)
            }
    
    def get_email_summary(self, days: int = 1) -> Dict[str, Any]:
        """
        Membuat ringkasan email untuk periode tertentu
        
        Args:
            days: Jumlah hari ke belakang untuk diringkas
            
        Returns:
            Dictionary berisi ringkasan email
        """
        print(f"📊 Membuat ringkasan email untuk {days} hari terakhir...")
        
        try:
            # Buat koneksi ke IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.email_password)
            mail.select("INBOX")
            
            # Hitung tanggal untuk pencarian
            since_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
            
            # Cari email sejak tanggal tertentu
            search_criteria = f'(SINCE "{since_date}")'
            status, data = mail.search(None, search_criteria)
            
            if status != "OK":
                raise Exception(f"Gagal mencari email: {status}")
            
            # Ambil ID email
            email_ids = data[0].split()
            
            # Ambil data email
            emails = []
            for email_id in email_ids:
                email_data = self._fetch_email(mail, email_id)
                if email_data:
                    emails.append(email_data)
            
            mail.close()
            mail.logout()
            
            # Analisis untuk ringkasan
            unread_count = len([e for e in emails if e.get("read") == False])
            sender_counts = {}
            subject_keywords = {}
            
            for e in emails:
                # Hitung email per pengirim
                sender = e.get("sender", "")
                if sender:
                    sender_counts[sender] = sender_counts.get(sender, 0) + 1
                
                # Analisis kata kunci di subjek
                subject = e.get("subject", "")
                words = re.findall(r'\b\w{3,}\b', subject.lower())
                for word in words:
                    if word not in ["the", "and", "for", "from", "with", "yang", "dari", "untuk", "dengan"]:
                        subject_keywords[word] = subject_keywords.get(word, 0) + 1
            
            # Top senders
            top_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Top subject keywords
            top_keywords = sorted(subject_keywords.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Buat ringkasan dengan LLM
            summary_text = self._generate_email_summary(emails, days)
            
            return {
                "total_emails": len(emails),
                "unread_emails": unread_count,
                "top_senders": top_senders,
                "top_subject_keywords": top_keywords,
                "summary": summary_text,
                "period_days": days,
                "emails": emails[:10]  # Hanya tampilkan 10 email terakhir
            }
            
        except Exception as e:
            print(f"Error saat membuat ringkasan email: {str(e)}")
            return {
                "total_emails": 0,
                "unread_emails": 0,
                "top_senders": [],
                "top_subject_keywords": [],
                "summary": f"Gagal membuat ringkasan: {str(e)}",
                "period_days": days,
                "emails": []
            }
    
    def search_emails(self, sender: str = "", subject: str = "", days: int = 7, limit: int = 10) -> Dict[str, Any]:
        """
        Mencari email berdasarkan kriteria tertentu
        
        Args:
            sender: Email pengirim yang dicari
            subject: Kata kunci subjek yang dicari
            days: Jumlah hari ke belakang untuk dicari
            limit: Jumlah maksimum email yang dikembalikan
            
        Returns:
            Dictionary berisi hasil pencarian
        """
        print(f"🔎 Mencari email dengan kriteria - pengirim: '{sender}', subjek: '{subject}', {days} hari terakhir...")
        
        try:
            # Buat koneksi ke IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.email_password)
            mail.select("INBOX")
            
            # Buat search criteria
            search_parts = []
            
            # Tambahkan kriteria waktu
            if days > 0:
                since_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
                search_parts.append(f'SINCE "{since_date}"')
            
            # Tambahkan kriteria pengirim
            if sender:
                search_parts.append(f'FROM "{sender}"')
            
            # Tambahkan kriteria subject
            if subject:
                search_parts.append(f'SUBJECT "{subject}"')
            
            # Gabungkan semua kriteria
            search_criteria = "(" + " ".join(search_parts) + ")" if search_parts else "ALL"
            
            # Jalankan pencarian
            status, data = mail.search(None, search_criteria)
            
            if status != "OK":
                raise Exception(f"Gagal mencari email: {status}")
            
            # Ambil ID email
            email_ids = data[0].split()
            
            # Terapkan limit
            if limit > 0:
                email_ids = email_ids[:limit]
            
            # Ambil data email
            emails = []
            for email_id in email_ids:
                email_data = self._fetch_email(mail, email_id)
                if email_data:
                    emails.append(email_data)
            
            mail.close()
            mail.logout()
            
            return {
                "count": len(emails),
                "search_criteria": {
                    "sender": sender,
                    "subject": subject,
                    "days": days
                },
                "emails": emails
            }
            
        except Exception as e:
            print(f"Error saat mencari email: {str(e)}")
            return {
                "count": 0,
                "search_criteria": {
                    "sender": sender,
                    "subject": subject,
                    "days": days
                },
                "emails": [],
                "error": str(e)
            }
    
    def analyze_email_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        Menganalisis tren email dalam periode tertentu
        
        Args:
            days: Jumlah hari ke belakang untuk dianalisis
            
        Returns:
            Dictionary berisi hasil analisis tren
        """
        print(f"📈 Menganalisis tren email untuk {days} hari terakhir...")
        
        try:
            # Buat koneksi ke IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.email_password)
            mail.select("INBOX")
            
            # Hitung tanggal untuk pencarian
            since_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
            
            # Cari email sejak tanggal tertentu
            search_criteria = f'(SINCE "{since_date}")'
            status, data = mail.search(None, search_criteria)
            
            if status != "OK":
                raise Exception(f"Gagal mencari email: {status}")
            
            # Ambil ID email
            email_ids = data[0].split()
            
            # Ambil data email
            emails = []
            for email_id in email_ids:
                email_data = self._fetch_email(mail, email_id)
                if email_data:
                    emails.append(email_data)
            
            mail.close()
            mail.logout()
            
            # Analisis tren
            
            # 1. Email per hari
            emails_by_date = {}
            for e in emails:
                date = e.get("date", "").split(" ")[0]  # Ambil tanggal saja
                if date:
                    emails_by_date[date] = emails_by_date.get(date, 0) + 1
            
            # 2. Email per jam
            emails_by_hour = {}
            for e in emails:
                try:
                    date_str = e.get("date", "")
                    if date_str:
                        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        hour = dt.hour
                        emails_by_hour[hour] = emails_by_hour.get(hour, 0) + 1
                except:
                    pass  # Skip jika format tanggal tidak sesuai
            
            # 3. Email per pengirim
            emails_by_sender = {}
            for e in emails:
                sender = e.get("sender", "")
                if sender:
                    emails_by_sender[sender] = emails_by_sender.get(sender, 0) + 1
            
            # 4. Email per domain
            emails_by_domain = {}
            for e in emails:
                sender = e.get("sender", "")
                if sender and "@" in sender:
                    domain = sender.split("@")[1]
                    emails_by_domain[domain] = emails_by_domain.get(domain, 0) + 1
            
            # Sortir hasil
            top_dates = sorted(emails_by_date.items(), key=lambda x: x[1], reverse=True)
            top_hours = sorted(emails_by_hour.items(), key=lambda x: x[0])
            top_senders = sorted(emails_by_sender.items(), key=lambda x: x[1], reverse=True)[:10]
            top_domains = sorted(emails_by_domain.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Buat ringkasan dengan LLM
            trend_analysis = self._generate_trend_analysis(
                emails, top_dates, top_hours, top_senders, top_domains, days
            )
            
            return {
                "total_emails": len(emails),
                "emails_by_date": dict(top_dates),
                "emails_by_hour": dict(top_hours),
                "top_senders": dict(top_senders),
                "top_domains": dict(top_domains),
                "analysis": trend_analysis,
                "period_days": days
            }
            
        except Exception as e:
            print(f"Error saat menganalisis tren email: {str(e)}")
            return {
                "total_emails": 0,
                "emails_by_date": {},
                "emails_by_hour": {},
                "top_senders": {},
                "top_domains": {},
                "analysis": f"Gagal menganalisis tren: {str(e)}",
                "period_days": days
            }
    
    def suggest_email_reply(self, email_id: str) -> Dict[str, Any]:
        """
        Membuat saran balasan untuk email tertentu
        
        Args:
            email_id: ID email yang akan dibalas
            
        Returns:
            Dictionary berisi saran balasan
        """
        print(f"💡 Membuat saran balasan untuk email ID: {email_id}...")
        
        try:
            # Dapatkan informasi email
            email_data = self._get_email_by_id(email_id)
            
            if not email_data:
                raise Exception(f"Email dengan ID {email_id} tidak ditemukan")
            
            # Buat saran balasan dengan LLM
            suggested_reply = self._generate_email_reply(email_data)
            
            return {
                "email": email_data,
                "suggested_reply": suggested_reply
            }
            
        except Exception as e:
            print(f"Error saat membuat saran balasan: {str(e)}")
            return {
                "error": str(e)
            }
    
    def reply_to_email(self, email_id: str, reply_content: str) -> Dict[str, Any]:
        """
        Membalas email tertentu
        
        Args:
            email_id: ID email yang akan dibalas
            reply_content: Konten balasan
            
        Returns:
            Dictionary berisi status pengiriman
        """
        print(f"↩️ Membalas email ID: {email_id}...")
        
        try:
            # Dapatkan informasi email
            email_data = self._get_email_by_id(email_id)
            
            if not email_data:
                raise Exception(f"Email dengan ID {email_id} tidak ditemukan")
            
            # Extract recipient from sender
            recipient = email_data.get("sender", "")
            if "<" in recipient and ">" in recipient:
                recipient = recipient.split("<")[1].split(">")[0].strip()
            
            # Prepare subject (add Re: if not already there)
            subject = email_data.get("subject", "")
            if not subject.lower().startswith("re:"):
                subject = f"Re: {subject}"
            
            # Send the reply
            self._send_email(
                recipient=recipient,
                subject=subject,
                body_html=reply_content,
                is_reply=True,
                original_email=email_data
            )
            
            return {
                "status": "success",
                "message": f"Email balasan berhasil dikirim ke {recipient}",
                "original_email": email_data,
                "reply_content": reply_content
            }
            
        except Exception as e:
            print(f"Error saat membalas email: {str(e)}")
            return {
                "status": "error",
                "message": f"Gagal membalas email: {str(e)}"
            }
    
    def suggest_and_reply_email(self, email_id: str) -> Dict[str, Any]:
        """
        Membuat saran balasan dan mengirimnya secara otomatis
        
        Args:
            email_id: ID email yang akan dibalas
            
        Returns:
            Dictionary berisi status pengiriman
        """
        print(f"🔄 Membuat dan mengirim balasan otomatis untuk email ID: {email_id}...")
        
        try:
            # Buat saran balasan
            suggestion_result = self.suggest_email_reply(email_id)
            
            if "error" in suggestion_result:
                raise Exception(suggestion_result["error"])
            
            # Kirim balasan
            reply_content = suggestion_result["suggested_reply"]
            reply_result = self.reply_to_email(email_id, reply_content)
            
            return {
                "status": "success",
                "message": "Berhasil membuat dan mengirim balasan otomatis",
                "suggested_reply": reply_content,
                "original_email": suggestion_result["email"],
                "reply_result": reply_result
            }
            
        except Exception as e:
            print(f"Error saat membuat dan mengirim balasan otomatis: {str(e)}")
            return {
                "status": "error",
                "message": f"Gagal membuat dan mengirim balasan otomatis: {str(e)}"
            }
    
    def _fetch_email(self, mail, email_id) -> Dict[str, Any]:
        """
        Mengambil informasi email berdasarkan ID
        
        Args:
            mail: Objek IMAP
            email_id: ID email
            
        Returns:
            Dictionary dengan informasi email
        """
        # Cek cache
        email_id_str = email_id.decode() if isinstance(email_id, bytes) else str(email_id)
        if email_id_str in self.email_cache:
            return self.email_cache[email_id_str]
        
        try:
            status, data = mail.fetch(email_id, "(RFC822)")
            if status != "OK" or not data or not data[0]:
                return None
            
            # Parse email
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Dapatkan sender
            from_header = msg.get("From", "")
            if "<" in from_header and ">" in from_header:
                sender_name = from_header.split("<")[0].strip()
                sender_email = from_header.split("<")[1].split(">")[0].strip()
                sender = f"{sender_name} <{sender_email}>"
            else:
                sender = from_header
            
            # Dapatkan subject
            subject = self._decode_email_header(msg.get("Subject", ""))
            
            # Dapatkan tanggal
            date_header = msg.get("Date", "")
            try:
                parsed_date = email.utils.parsedate_to_datetime(date_header)
                date_str = parsed_date.strftime("%Y-%m-%d %H:%M:%S")
            except:
                date_str = date_header
            
            # Cek apakah email sudah dibaca
            status, flags_data = mail.fetch(email_id, "(FLAGS)")
            flags = flags_data[0].decode()
            is_read = "\\Seen" in flags
            
            # Dapatkan body
            body = ""
            html_body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        try:
                            part_body = part.get_payload(decode=True).decode()
                            if part_body:
                                body = part_body
                        except:
                            pass
                    elif content_type == "text/html":
                        try:
                            part_body = part.get_payload(decode=True).decode()
                            if part_body:
                                html_body = part_body
                        except:
                            pass
            else:
                try:
                    body = msg.get_payload(decode=True).decode()
                except:
                    body = msg.get_payload()
            
            # Preferensi HTML jika ada, atau plain text
            full_body = html_body if html_body else body
            
            # Buat preview (plain text untuk preview)
            body_preview = body
            if len(body_preview) > 1000:
                body_preview = body_preview[:1000] + "... [truncated]"
            
            # Dapatkan attachments
            attachments = []
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_maintype() == 'multipart':
                        continue
                    if part.get('Content-Disposition') is None:
                        continue
                    
                    filename = part.get_filename()
                    if filename:
                        attachments.append(filename)
            
            # Dapatkan penerima (To)
            to_header = msg.get("To", "")
            recipients = []
            if to_header:
                for recipient in to_header.split(","):
                    recipient = recipient.strip()
                    if recipient:
                        recipients.append(recipient)
            
            # Dapatkan penerima CC
            cc_header = msg.get("Cc", "")
            cc_recipients = []
            if cc_header:
                for recipient in cc_header.split(","):
                    recipient = recipient.strip()
                    if recipient:
                        cc_recipients.append(recipient)
            
            # Buat dictionary hasil
            email_data = {
                "id": email_id_str,
                "sender": sender,
                "subject": subject,
                "date": date_str,
                "read": is_read,
                "body_preview": body_preview,
                "body": body,
                "html_body": html_body,
                "full_body": full_body,
                "recipients": recipients,
                "cc_recipients": cc_recipients,
                "has_attachments": len(attachments) > 0,
                "attachments": attachments
            }
            
            # Simpan ke cache
            self.email_cache[email_id_str] = email_data
            
            return email_data
            
        except Exception as e:
            print(f"Error saat mengambil email {email_id}: {str(e)}")
            return None
    
    def _get_email_by_id(self, email_id: str) -> Dict[str, Any]:
        """
        Mengambil informasi email berdasarkan ID
        
        Args:
            email_id: ID email
            
        Returns:
            Dictionary dengan informasi email
        """
        # Cek cache
        if email_id in self.email_cache:
            return self.email_cache[email_id]
        
        try:
            # Buat koneksi ke IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.email_password)
            mail.select("INBOX")
            
            # Convert string ID to bytes if needed
            fetch_id = email_id.encode() if isinstance(email_id, str) else email_id
            
            # Fetch email
            email_data = self._fetch_email(mail, fetch_id)
            
            mail.close()
            mail.logout()
            
            return email_data
            
        except Exception as e:
            print(f"Error saat mengambil email dengan ID {email_id}: {str(e)}")
            return None
    
    def _decode_email_header(self, header: str) -> str:
        """
        Decode email header (subject, from, etc)
        """
        if not header:
            return ""
        
        try:
            decoded_header = decode_header(header)
            header_parts = []
            
            for part, encoding in decoded_header:
                if isinstance(part, bytes):
                    if encoding:
                        try:
                            header_parts.append(part.decode(encoding))
                        except:
                            header_parts.append(part.decode('utf-8', errors='replace'))
                    else:
                        header_parts.append(part.decode('utf-8', errors='replace'))
                else:
                    header_parts.append(part)
            
            return ''.join(header_parts)
        except:
            return header
    
    def _send_email(self, recipient: str, subject: str, body_html: str, 
                   is_reply: bool = False, original_email: Dict[str, Any] = None) -> bool:
        """
        Mengirim email
        
        Args:
            recipient: Email penerima
            subject: Subjek email
            body_html: Isi email dalam format HTML
            is_reply: Apakah email ini balasan
            original_email: Data email asli yang dibalas
            
        Returns:
            Boolean success status
        """
        try:
            # Buat email message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_address
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Tambahkan header Reply-To jika ini adalah balasan
            if is_reply and original_email:
                # Get Message-ID dari email asli
                if 'message_id' in original_email:
                    msg['In-Reply-To'] = original_email['message_id']
                    msg['References'] = original_email['message_id']
                
                # Tambahkan CC asli
                if 'cc_recipients' in original_email and original_email['cc_recipients']:
                    msg['Cc'] = ', '.join(original_email['cc_recipients'])
            
            # Wrap body_html in proper HTML if needed
            if not body_html.strip().startswith('<html'):
                body_html = f"""
                <html>
                <body>
                {body_html}
                </body>
                </html>
                """
            
            # Buat email parts
            part = MIMEText(body_html, 'html')
            msg.attach(part)
            
            # Kirim email
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Error saat mengirim email: {str(e)}")
            raise e
    
    def _generate_email_summary(self, emails: List[Dict[str, Any]], days: int) -> str:
        """
        Menggunakan LLM untuk membuat ringkasan dari email
        
        Args:
            emails: List email yang akan diringkas
            days: Periode waktu
            
        Returns:
            String berisi ringkasan email
        """
        # Batasi jumlah email untuk analisis
        max_emails = min(10, len(emails))
        recent_emails = emails[:max_emails]
        
        if not recent_emails:
            return "Tidak ada email untuk diringkas."
        
        # Buat prompt untuk LLM
        prompt = f"""
        Buat ringkasan yang informatif tentang email yang diterima dalam {days} hari terakhir.
        
        Data email ({len(emails)} total, menampilkan {max_emails} email terbaru):
        """
        
        for i, email in enumerate(recent_emails, 1):
            prompt += f"""
            Email {i}:
            - Pengirim: {email.get('sender', '')}
            - Subjek: {email.get('subject', '')}
            - Tanggal: {email.get('date', '')}
            - Status: {"Belum dibaca" if not email.get('read') else "Sudah dibaca"}
            """
        
        prompt += """
        Berdasarkan data di atas, buatlah ringkasan email dengan:
        1. Tren utama atau tema yang muncul
        2. Email penting yang mungkin perlu perhatian
        3. Insight lain yang berguna
        
        Buatlah ringkasan dalam format paragraf yang koheren dan informatif, bukan dalam poin-poin.
        """
        
        try:
            # Panggil Gemini LLM
            summary = call_gemini(prompt)
            return summary
        except:
            # Fallback jika LLM gagal
            return f"Anda menerima {len(emails)} email dalam {days} hari terakhir. {len([e for e in emails if not e.get('read', True)])} email belum dibaca."
    
    def _generate_trend_analysis(self, emails: List[Dict[str, Any]], 
                               dates: List[Tuple], hours: List[Tuple], 
                               senders: List[Tuple], domains: List[Tuple],
                               days: int) -> str:
        """
        Menggunakan LLM untuk menganalisis tren email
        
        Returns:
            String berisi analisis tren
        """
        # Buat prompt untuk LLM
        prompt = f"""
        Analisis tren email yang diterima dalam {days} hari terakhir berdasarkan data berikut:
        
        Total email: {len(emails)}
        
        Email per hari:
        {', '.join(f"{date}: {count}" for date, count in dates[:7])}
        
        Email per jam (format jam: jumlah):
        {', '.join(f"{hour}: {count}" for hour, count in hours)}
        
        Top pengirim:
        {', '.join(f"{sender}: {count}" for sender, count in senders[:5])}
        
        Top domain:
        {', '.join(f"{domain}: {count}" for domain, count in domains[:5])}
        
        Berdasarkan data di atas:
        1. Identifikasi pola utama dalam pengiriman email (waktu, frekuensi)
        2. Berikan insight tentang pengirim yang paling aktif
        3. Berikan rekomendasi untuk pengelolaan email berdasarkan tren tersebut
        
        Buatlah analisis dalam bentuk paragraf yang informatif, bukan dalam poin-poin.
        """
        
        try:
            # Panggil Gemini LLM
            analysis = call_gemini(prompt)
            return analysis
        except:
            # Fallback jika LLM gagal
            return f"Analisis volume email: Anda menerima {len(emails)} email dalam {days} hari terakhir, dengan rata-rata {len(emails)/days:.1f} email per hari."
    
    def _generate_email_reply(self, email_data: Dict[str, Any]) -> str:
        """
        Menggunakan LLM untuk membuat balasan email
        
        Args:
            email_data: Data email yang akan dibalas
            
        Returns:
            String berisi balasan email dalam format HTML
        """
        # Ekstrak informasi penting
        sender = self.sender_name
        subject = email_data.get('subject', '')
        body = email_data.get('body_preview', '') or email_data.get('body', '')
        
        # Jika pengirim memiliki format "Nama <email>", ekstrak nama
        sender_name = self.sender_name
        print(sender_name)
        if '<' in sender and '>' in sender:
            sender_name = sender.split('<')[0].strip()
        
        # Buat prompt untuk LLM
        prompt = f"""
        Buatkan balasan yang profesional untuk email berikut:
        
        Dari: {sender}
        Subjek: {subject}
        
        Isi Email:
        {body}
        
        Buat balasan dengan kriteria berikut:
        1. Sopan dan profesional
        2. Relevan dengan isi email yang diterima
        3. Tidak terlalu panjang (maksimal 3-4 paragraf)
        4. Dalam format HTML sederhana (dengan paragraf yang dibungkus dengan tag p)
        5. Mulai dengan salam pembuka seperti "Halo [Nama]," atau "Dear [Nama],"
        6. Akhiri dengan salam penutup dan nama Anda
        
        Jika email tersebut adalah pesan otomatis, newsletter, atau spam, berikan respons yang sopan bahwa Anda telah menerima email tersebut.
        
        Berikan HANYA balasan email dalam format HTML, tanpa komentar tambahan.
        """
        
        try:
            # Panggil Gemini LLM
            reply_content = call_gemini(prompt)
            
            # Pastikan balasan dalam format HTML
            if not reply_content.strip().lower().startswith('<html') and not reply_content.strip().startswith('<p>'):
                # Tambahkan tag HTML sederhana jika tidak ada
                reply_content = f"""
                <p>{reply_content}</p>
                """.replace('\n\n', '</p><p>').replace('\n', '<br>')
            
            return reply_content
        except Exception as e:
            print(f"Error saat membuat balasan email: {str(e)}")
            # Fallback jika LLM gagal
            return f"""
            <p>Terima kasih atas email Anda.</p>
            <p>Saya sudah menerima email Anda dan akan segera menindaklanjuti.</p>
            <p>Salam,<br>
            {self.email_address.split('@')[0]}</p>
            """