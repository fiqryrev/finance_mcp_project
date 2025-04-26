"""
Utility for managing Google Cloud Storage operations
"""
import os
import datetime
from google.cloud import storage
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class GCSManager:
    """
    A utility class for handling Google Cloud Storage operations
    """
    
    def __init__(self, bucket_name="finance_mcp_project"):
        """
        Initialize the GCS Manager
        
        Args:
            bucket_name: Name of the GCS bucket
        """
        self.bucket_name = bucket_name
        self.credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        # Initialize the storage client
        self.storage_client = storage.Client.from_service_account_json(
            self.credentials_path
        )
        self.bucket = self.storage_client.bucket(self.bucket_name)
    
    def upload_file(self, user_id, file_name, file_data, content_type=None):
        """
        Upload a file to Google Cloud Storage
        
        Args:
            user_id: Telegram user ID for folder name
            file_name: Original file name
            file_data: File content as bytes
            content_type: MIME type of the file (optional)
            
        Returns:
            str: URL of the uploaded file
        """
        try:
            # Create timestamp for file name
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
            
            # Extract file extension
            _, ext = os.path.splitext(file_name)
            
            # Create the new file name
            new_file_name = f"{timestamp}__{file_name}"
            
            # Create the full path including folder structure
            destination_blob_name = f"documents/{user_id}/{new_file_name}"
            
            # Create a blob object
            blob = self.bucket.blob(destination_blob_name)
            
            # Upload the file
            if isinstance(file_data, bytes):
                if content_type:
                    blob.upload_from_string(file_data, content_type=content_type)
                else:
                    blob.upload_from_string(file_data)
            else:
                blob.upload_from_file(file_data)
            
            # Generate the public URL
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/{destination_blob_name}"
            
            print(f"File uploaded to GCS: {public_url}")
            
            # Return the public URL
            return public_url
            
        except Exception as e:
            print(f"Error uploading file to GCS: {str(e)}")
            return None
    
    def list_user_files(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all files for a specific user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of dictionaries with file info (name, date, url, size)
        """
        try:
            # Create the prefix for the user's folder
            prefix = f"documents/{user_id}/"
            
            # List all blobs with the prefix
            blobs = self.bucket.list_blobs(prefix=prefix)
            
            # Prepare the result list
            files = []
            for blob in blobs:
                # Skip if this is a folder marker
                if blob.name.endswith('/'):
                    continue
                
                # Extract the file name (without the path)
                full_name = blob.name.replace(prefix, '')
                
                # Extract the timestamp and original filename
                parts = full_name.split('__', 1)
                if len(parts) == 2:
                    timestamp, original_name = parts
                else:
                    timestamp = "Unknown"
                    original_name = full_name
                
                # Format the timestamp
                try:
                    date_obj = datetime.datetime.strptime(timestamp, "%Y-%m-%d-%H:%M:%S")
                    formatted_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    formatted_date = timestamp
                
                # Generate the public URL
                public_url = f"https://storage.googleapis.com/{self.bucket_name}/{blob.name}"
                
                # Add file info to the list
                files.append({
                    "original_name": original_name,
                    "timestamp": formatted_date,
                    "size": self._format_size(blob.size),
                    "url": public_url,
                    "blob_name": blob.name,
                    "upload_date": formatted_date
                })
            
            # Sort files by timestamp (newest first)
            files.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return files
            
        except Exception as e:
            print(f"Error listing files for user {user_id}: {str(e)}")
            return []
    
    def delete_file(self, blob_name: str) -> bool:
        """
        Delete a specific file
        
        Args:
            blob_name: Full path of the blob to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            # Get the blob
            blob = self.bucket.blob(blob_name)
            
            # Delete the blob
            blob.delete()
            
            print(f"Successfully deleted file: {blob_name}")
            return True
            
        except Exception as e:
            print(f"Error deleting file {blob_name}: {str(e)}")
            return False
    
    def delete_user_files(self, user_id: str, filter_criteria: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Delete files for a specific user based on criteria
        
        Args:
            user_id: Telegram user ID
            filter_criteria: Dictionary with filter criteria:
                - filename: String to match in filename
                - before_date: Delete files before this date (YYYY-MM-DD)
                - after_date: Delete files after this date (YYYY-MM-DD)
                - all: If True, delete all files for the user
            
        Returns:
            Dict with count of deleted files and status
        """
        try:
            # Default to empty dict if filter_criteria is None
            if filter_criteria is None:
                filter_criteria = {}
            
            # List all files for the user
            files = self.list_user_files(user_id)
            
            # Apply filters
            files_to_delete = []
            
            # Check if we should delete all files
            if filter_criteria.get("all", False):
                files_to_delete = files
            else:
                # Filter by filename
                filename_filter = filter_criteria.get("filename", "")
                if filename_filter:
                    files = [f for f in files if filename_filter.lower() in f["original_name"].lower()]
                
                # Filter by date range
                before_date = filter_criteria.get("before_date")
                after_date = filter_criteria.get("after_date")
                
                if before_date or after_date:
                    filtered_files = []
                    for file in files:
                        try:
                            file_date = datetime.datetime.strptime(file["timestamp"], "%Y-%m-%d %H:%M:%S").date()
                            
                            include_file = True
                            if before_date:
                                before_date_obj = datetime.datetime.strptime(before_date, "%Y-%m-%d").date()
                                if file_date > before_date_obj:
                                    include_file = False
                            
                            if after_date:
                                after_date_obj = datetime.datetime.strptime(after_date, "%Y-%m-%d").date()
                                if file_date < after_date_obj:
                                    include_file = False
                            
                            if include_file:
                                filtered_files.append(file)
                        except ValueError:
                            # If date parsing fails, skip this file
                            continue
                    
                    files = filtered_files
                
                files_to_delete = files
            
            # Delete the files
            deleted_count = 0
            for file in files_to_delete:
                if self.delete_file(file["blob_name"]):
                    deleted_count += 1
            
            return {
                "deleted_count": deleted_count,
                "status": "success",
                "message": f"Successfully deleted {deleted_count} files"
            }
            
        except Exception as e:
            print(f"Error deleting files for user {user_id}: {str(e)}")
            return {
                "deleted_count": 0,
                "status": "error",
                "message": f"Error deleting files: {str(e)}"
            }
    
    def get_user_directory_url(self, user_id: str) -> str:
        """
        Get the URL for a user's directory
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            str: URL to the user's directory in GCS
        """
        return f"https://storage.googleapis.com/{self.bucket_name}/documents/{user_id}/"
    
    def _format_size(self, size_bytes: int) -> str:
        """
        Format file size in a human-readable format
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            str: Formatted size string
        """
        # Handle edge cases
        if size_bytes < 0:
            return "0 B"
        
        # Define size units
        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        
        # Calculate size
        i = 0
        while size_bytes >= 1024 and i < len(units) - 1:
            size_bytes /= 1024
            i += 1
        
        # Format with appropriate precision
        if i == 0:
            return f"{size_bytes} {units[i]}"
        else:
            return f"{size_bytes:.2f} {units[i]}"