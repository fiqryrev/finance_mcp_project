"""
Service for sending emails
"""
import os
import smtplib
import logging
from typing import List, Dict, Any, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

from config.config import EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD

class EmailService:
    """Service for sending emails"""
    
    def __init__(self):
        """Initialize the email service"""
        self.host = EMAIL_HOST
        self.port = EMAIL_PORT
        self.username = EMAIL_USER
        self.password = EMAIL_PASSWORD
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def send_email(self, recipients: List[str], subject: str, body: str, 
                  attachment_url: Optional[str] = None, 
                  attachment_path: Optional[str] = None) -> bool:
        """
        Send an email
        
        Args:
            recipients: List of recipient email addresses
            subject: Email subject
            body: Email body (HTML)
            attachment_url: URL to include in the email (optional)
            attachment_path: Path to file attachment (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not recipients:
            self.logger.error("No recipients provided")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # Attach HTML body
            msg.attach(MIMEText(body, 'html'))
            
            # Add file attachment if provided
            if attachment_path and os.path.exists(attachment_path):
                self._attach_file(msg, attachment_path)
            
            # Connect to server and send email
            with smtplib.SMTP_SSL(self.host, self.port) as server:
                server.login(self.username, self.password)
                server.send_message(msg)
            
            self.logger.info(f"Email sent successfully to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return False
    
    def send_report(self, recipients: List[str], report_data: Dict[str, Any]) -> bool:
        """
        Send a financial report email
        
        Args:
            recipients: List of recipient email addresses
            report_data: Report data dictionary
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Extract report info
        report_type = report_data.get('report_type', 'Financial')
        period = report_data.get('period', 'Recent')
        
        # Create subject
        subject = f"{report_type.capitalize()} Report for {period}"
        
        # Create email body
        body = self._format_report_email(report_data)
        
        # Send the email
        report_url = report_data.get('report_url')
        return self.send_email(recipients, subject, body, attachment_url=report_url)
    
    def _format_report_email(self, report_data: Dict[str, Any]) -> str:
        """
        Format report data for email
        
        Args:
            report_data: Report data dictionary
            
        Returns:
            Formatted email body as HTML
        """
        # Extract report info
        report_type = report_data.get('report_type', 'Financial')
        period = report_data.get('period', 'Recent')
        total_expenses = report_data.get('total_expenses', '$0.00')
        
        # Create HTML email
        html = f"""
        <html>
        <body>
            <h2>{report_type.capitalize()} Report</h2>
            <p>Period: {period}</p>
            <p>Total Expenses: {total_expenses}</p>
            
            <h3>Expenses by Category</h3>
            <ul>
        """
        
        # Add categories
        categories = report_data.get('categories', {})
        for category, amount in categories.items():
            html += f"<li>{category}: {amount}</li>"
        
        html += """
            </ul>
            
            <h3>Top Merchants</h3>
            <ul>
        """
        
        # Add merchants
        merchants = report_data.get('merchants', {})
        for merchant, amount in merchants.items():
            html += f"<li>{merchant}: {amount}</li>"
        
        html += """
            </ul>
        """
        
        # Add insights if available
        insights = report_data.get('insights', [])
        if insights:
            html += """
            <h3>Insights</h3>
            <ul>
            """
            
            for insight in insights:
                html += f"<li>{insight}</li>"
            
            html += """
            </ul>
            """
        
        # Add report link if available
        report_url = report_data.get('report_url')
        if report_url:
            html += f"""
            <p><a href="{report_url}">View Full Report</a></p>
            """
        
        # Close HTML
        html += """
            <p>This is an automated report generated by your Financial Document Bot.</p>
            <p><small>Generated on {datetime_str}</small></p>
        </body>
        </html>
        """.format(datetime_str=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return html
    
    def _attach_file(self, msg: MIMEMultipart, file_path: str) -> None:
        """
        Attach a file to an email message
        
        Args:
            msg: Email message object
            file_path: Path to the file to attach
        """
        try:
            # Get filename from path
            filename = os.path.basename(file_path)
            
            # Open file in binary mode
            with open(file_path, 'rb') as attachment:
                # Create MIME part
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            # Encode file in ASCII characters to send by email
            encoders.encode_base64(part)
            
            # Add header as key/value pair to attachment part
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}',
            )
            
            # Add attachment to message
            msg.attach(part)
            
        except Exception as e:
            self.logger.error(f"Error attaching file {file_path}: {e}")