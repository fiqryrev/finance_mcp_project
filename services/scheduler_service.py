"""
Service for scheduling automated tasks like report generation
"""
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from config.config import DEFAULT_REPORT_SCHEDULE
from services.sheets_service import SheetsService
from services.email_service import EmailService

class SchedulerService:
    """Service for scheduling automated tasks"""
    
    def __init__(self):
        """Initialize the scheduler service"""
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Create scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_jobstore(MemoryJobStore(), 'default')
        
        # Initialize services
        self.sheets_service = SheetsService()
        self.email_service = EmailService()
        
        # Start the scheduler
        self.scheduler.start()
        self.logger.info("Scheduler started")
    
    def schedule_weekly_report(self, day_of_week: int = 0, hour: int = 9, minute: int = 0) -> None:
        """
        Schedule a weekly financial report
        
        Args:
            day_of_week: Day of week (0-6, where 0 is Monday)
            hour: Hour of the day (0-23)
            minute: Minute of the hour (0-59)
        """
        # Create a cron trigger for weekly reports
        trigger = CronTrigger(
            day_of_week=day_of_week,
            hour=hour,
            minute=minute
        )
        
        # Add the job to the scheduler
        self.scheduler.add_job(
            self._generate_and_send_weekly_report,
            trigger=trigger,
            id='weekly_report',
            replace_existing=True,
            name='Weekly Financial Report'
        )
        
        self.logger.info(f"Scheduled weekly report for day {day_of_week}, at {hour:02d}:{minute:02d}")
    
    def schedule_monthly_report(self, day: int = 1, hour: int = 9, minute: int = 0) -> None:
        """
        Schedule a monthly financial report
        
        Args:
            day: Day of month (1-31)
            hour: Hour of the day (0-23)
            minute: Minute of the hour (0-59)
        """
        # Create a cron trigger for monthly reports
        trigger = CronTrigger(
            day=day,
            hour=hour,
            minute=minute
        )
        
        # Add the job to the scheduler
        self.scheduler.add_job(
            self._generate_and_send_monthly_report,
            trigger=trigger,
            id='monthly_report',
            replace_existing=True,
            name='Monthly Financial Report'
        )
        
        self.logger.info(f"Scheduled monthly report for day {day}, at {hour:02d}:{minute:02d}")
    
    def schedule_custom_report(self, cron_expression: str, report_name: str) -> None:
        """
        Schedule a custom report with a cron expression
        
        Args:
            cron_expression: Cron expression (e.g. "0 9 * * 1-5" for weekdays at 9am)
            report_name: Name of the report
        """
        # Create a cron trigger from expression
        trigger = CronTrigger.from_crontab(cron_expression)
        
        # Add the job to the scheduler
        self.scheduler.add_job(
            self._generate_and_send_custom_report,
            trigger=trigger,
            id=f'custom_report_{report_name.lower().replace(" ", "_")}',
            replace_existing=True,
            name=f'Custom Report: {report_name}',
            kwargs={'report_name': report_name}
        )
        
        self.logger.info(f"Scheduled custom report '{report_name}' with cron: {cron_expression}")
    
    def schedule_one_time_report(self, run_date: datetime, report_type: str) -> None:
        """
        Schedule a one-time report
        
        Args:
            run_date: Date and time to run the report
            report_type: Type of report to generate
        """
        # Add the job to the scheduler
        self.scheduler.add_job(
            self._generate_and_send_custom_report,
            'date',
            run_date=run_date,
            id=f'one_time_report_{datetime.now().strftime("%Y%m%d%H%M%S")}',
            name=f'One-time {report_type.capitalize()} Report',
            kwargs={'report_name': report_type}
        )
        
        self.logger.info(f"Scheduled one-time {report_type} report for {run_date}")
    
    def list_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """
        List all scheduled jobs
        
        Returns:
            List of dictionaries with job information
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger)
            })
        return jobs
    
    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job
        
        Args:
            job_id: ID of the job to remove
            
        Returns:
            True if job was removed, False otherwise
        """
        try:
            self.scheduler.remove_job(job_id)
            self.logger.info(f"Removed job {job_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error removing job {job_id}: {e}")
            return False
    
    def pause_job(self, job_id: str) -> bool:
        """
        Pause a scheduled job
        
        Args:
            job_id: ID of the job to pause
            
        Returns:
            True if job was paused, False otherwise
        """
        try:
            self.scheduler.pause_job(job_id)
            self.logger.info(f"Paused job {job_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error pausing job {job_id}: {e}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job
        
        Args:
            job_id: ID of the job to resume
            
        Returns:
            True if job was resumed, False otherwise
        """
        try:
            self.scheduler.resume_job(job_id)
            self.logger.info(f"Resumed job {job_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error resuming job {job_id}: {e}")
            return False
    
    def _generate_and_send_weekly_report(self) -> None:
        """Generate and send a weekly financial report"""
        self.logger.info("Generating weekly report")
        
        try:
            # Calculate the date range for the past week
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
            
            # Generate the report
            report_data = self.sheets_service._generate_report_sync("weekly")
            
            # Send the report via email
            subject = f"Weekly Financial Report {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            body = self._format_report_email(report_data, "weekly")
            
            recipients = self._get_report_recipients()
            self.email_service.send_email(recipients, subject, body, report_data.get('report_url'))
            
            self.logger.info("Weekly report sent successfully")
            
        except Exception as e:
            self.logger.error(f"Error generating weekly report: {e}")
    
    def _generate_and_send_monthly_report(self) -> None:
        """Generate and send a monthly financial report"""
        self.logger.info("Generating monthly report")
        
        try:
            # Calculate the date range for the past month
            today = datetime.now().date()
            
            # Get the first day of the current month
            first_day_current_month = today.replace(day=1)
            
            # Get the last day of the previous month
            last_day_previous_month = first_day_current_month - timedelta(days=1)
            
            # Get the first day of the previous month
            first_day_previous_month = last_day_previous_month.replace(day=1)
            
            # Generate the report
            report_data = self.sheets_service._generate_report_sync("monthly")
            
            # Send the report via email
            subject = f"Monthly Financial Report {first_day_previous_month.strftime('%B %Y')}"
            body = self._format_report_email(report_data, "monthly")
            
            recipients = self._get_report_recipients()
            self.email_service.send_email(recipients, subject, body, report_data.get('report_url'))
            
            self.logger.info("Monthly report sent successfully")
            
        except Exception as e:
            self.logger.error(f"Error generating monthly report: {e}")
    
    def _generate_and_send_custom_report(self, report_name: str) -> None:
        """
        Generate and send a custom report
        
        Args:
            report_name: Name of the report
        """
        self.logger.info(f"Generating custom report: {report_name}")
        
        try:
            # Generate the report
            report_data = self.sheets_service._generate_report_sync("custom")
            
            # Send the report via email
            subject = f"Custom Financial Report: {report_name}"
            body = self._format_report_email(report_data, "custom", report_name)
            
            recipients = self._get_report_recipients()
            self.email_service.send_email(recipients, subject, body, report_data.get('report_url'))
            
            self.logger.info(f"Custom report '{report_name}' sent successfully")
            
        except Exception as e:
            self.logger.error(f"Error generating custom report '{report_name}': {e}")
    
    def _format_report_email(self, report_data: Dict[str, Any], report_type: str, report_name: str = None) -> str:
        """
        Format report data for email
        
        Args:
            report_data: Report data dictionary
            report_type: Type of report (weekly, monthly, custom)
            report_name: Name of the report (for custom reports)
            
        Returns:
            Formatted email body as HTML
        """
        # Get period and title
        period = report_data.get('period', 'Unknown period')
        title = f"{report_name or report_type.capitalize()} Financial Report"
        
        # Format the email
        html = f"""
        <html>
        <body>
            <h2>{title}</h2>
            <p>Period: {period}</p>
            <p>Total Expenses: {report_data.get('total_expenses', '$0.00')}</p>
            
            <h3>Expenses by Category</h3>
            <ul>
        """
        
        # Add category breakdown
        for category, amount in report_data.get('categories', {}).items():
            html += f"<li>{category}: {amount}</li>"
        
        html += """
            </ul>
            
            <p>For more details, please view the full report using the link below.</p>
        """
        
        # Add the report link if available
        if 'report_url' in report_data:
            html += f'<p><a href="{report_data["report_url"]}">View Full Report</a></p>'
        
        html += """
            <p>This is an automated report generated by your Financial Document Bot.</p>
        </body>
        </html>
        """
        
        return html
    
    def _get_report_recipients(self) -> List[str]:
        """
        Get the list of email recipients for reports
        
        Returns:
            List of email addresses
        """
        # In a real implementation, this would retrieve configured recipients
        # For now, we'll use the default from config
        from config.config import EMAIL_RECIPIENTS
        return EMAIL_RECIPIENTS