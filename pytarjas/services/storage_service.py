# pytarjas/services/storage_service.py
import os
import uuid
import logging
from azure.storage.blob import BlobServiceClient
from flask import current_app

# Configure logger to capture upload events in Azure Log Stream
logger = logging.getLogger(__name__)

class StorageService:
    """
    Service to handle file uploads to Azure Blob Storage or local storage.
    """

    @staticmethod
    def get_blob_client():
        """
        Initializes the Azure Blob Service Client using the connection string.
        """
        connection_string = current_app.config.get('AZURE_STORAGE_CONNECTION_STRING')
        
        if not connection_string:
            logger.warning("AZURE_STORAGE_CONNECTION_STRING not found. Falling back to local storage.")
            return None
            
        try:
            return BlobServiceClient.from_connection_string(connection_string)
        except Exception as e:
            logger.error(f"Error connecting to Azure Blob Storage: {e}")
            return None

    @staticmethod
    def upload_file(file):
        """
        Uploads a file to Azure Blob Storage if configured, otherwise saves locally.
        """
        if not file or file.filename == '':
            return None

        # Generate unique filename to prevent collisions
        ext = os.path.splitext(file.filename)[1].lower()
        unique_filename = f"{uuid.uuid4()}{ext}"

        blob_service_client = StorageService.get_blob_client()

        if blob_service_client:
            try:
                container_name = current_app.config.get('AZURE_CONTAINER_NAME', 'uploads')
                blob_client = blob_service_client.get_blob_client(
                    container=container_name, 
                    blob=unique_filename
                )
                
                file.seek(0)
                blob_client.upload_blob(file)
                logger.info(f"Successfully uploaded {unique_filename} to Azure container: {container_name}")
                return unique_filename
            except Exception as e:
                logger.error(f"Azure upload failed for {unique_filename}: {e}. Falling back to local.")

        # Local Fallback (Warning: files in /tmp are non-persistent on Azure)
        upload_path = current_app.config.get('UPLOAD_PATH')
        
        if not os.path.exists(upload_path):
            os.makedirs(upload_path, exist_ok=True)
        
        file.save(os.path.join(upload_path, unique_filename))
        logger.info(f"Saved {unique_filename} to local storage at {upload_path}")
        
        return unique_filename

    @staticmethod
    def get_file_url(filename):
        """
        Returns the public URL of the file stored in Azure or a local path.
        """
        if not filename:
            return None
            
        connection_string = current_app.config.get('AZURE_STORAGE_CONNECTION_STRING')
        
        if connection_string:
            try:
                # Extract account name from connection string
                account_name = connection_string.split('AccountName=')[1].split(';')[0]
                container = current_app.config.get('AZURE_CONTAINER_NAME', 'uploads')
                return f"https://{account_name}.blob.core.windows.net/{container}/{filename}"
            except (IndexError, AttributeError):
                pass
        
        return f"/uploads/{filename}"