"""
Utility for handling time operations
"""
import time
import datetime
import pytz

class Timer:
    """
    A utility class for handling time operations including time zones,
    timestamps, and performance timing.
    """
    
    @staticmethod
    def get_current_time():
        """
        Get the current UTC time
        
        Returns:
            datetime: Current UTC datetime object
        """
        return datetime.datetime.now(datetime.timezone.utc)
    
    @staticmethod
    def get_current_time_iso():
        """
        Get the current UTC time in ISO 8601 format
        
        Returns:
            str: Current time in ISO format
        """
        return Timer.get_current_time().isoformat()
    
    @staticmethod
    def get_jakarta_current_time():
        """
        Get the current time in Jakarta/Asia timezone (WIB/UTC+7)
        
        Returns:
            str: Current Jakarta time in ISO format
        """
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        jakarta_time = datetime.datetime.now(jakarta_tz)
        return jakarta_time.isoformat()
    
    @staticmethod
    def format_time(dt, format_str="%Y-%m-%d %H:%M:%S"):
        """
        Format a datetime object using the specified format
        
        Args:
            dt: datetime object
            format_str: Format string (default: "%Y-%m-%d %H:%M:%S")
            
        Returns:
            str: Formatted time string
        """
        return dt.strftime(format_str)
    
    @staticmethod
    def timestamp_ms():
        """
        Get current timestamp in milliseconds
        
        Returns:
            int: Current timestamp in milliseconds
        """
        return int(time.time() * 1000)
    
    @staticmethod
    def calculate_processing_time(start_time_ms):
        """
        Calculate processing time in milliseconds
        
        Args:
            start_time_ms: Starting timestamp in milliseconds
            
        Returns:
            int: Processing time in milliseconds
        """
        return Timer.timestamp_ms() - start_time_ms
    
    @staticmethod
    def format_processing_time(milliseconds):
        """
        Format processing time for display
        
        Args:
            milliseconds: Time in milliseconds
            
        Returns:
            str: Formatted time string
        """
        seconds = milliseconds / 1000.0
        if seconds < 1:
            return f"{milliseconds}ms"
        elif seconds < 60:
            return f"{seconds:.2f}s"
        else:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{int(minutes)}m {remaining_seconds:.2f}s"