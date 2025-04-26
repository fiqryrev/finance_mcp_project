"""
Utility for managing Google Cloud Storage operations
"""
import os
import datetime
from google.cloud import storage
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