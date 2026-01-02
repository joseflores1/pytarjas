import os
import uuid
from azure.storage.blob import BlobServiceClient
from flask import current_app

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
            return None
            
        try:
            return BlobServiceClient.from_connection_string(connection_string)
        except Exception:
            return None

    @staticmethod
    def upload_file(file):
        """
        Uploads a file to Azure Blob Storage if configured, otherwise saves locally.
        
        Args:
            file: The file object from a Flask form (request.files).
            
        Returns:
            str: The unique filename (UUID) to be stored in the database.
        """
        if not file:
            return None
            
        if file.filename == '':
            return None

        # Generate a unique filename to avoid collisions and preserve extension
        ext = os.path.splitext(file.filename)[1].lower()
        unique_filename = f"{uuid.uuid4()}{ext}"

        blob_service_client = StorageService.get_blob_client()

        if blob_service_client:
            # Production path: Upload to Azure Container
            container_name = current_app.config.get('AZURE_CONTAINER_NAME', 'uploads')
            blob_client = blob_service_client.get_blob_client(
                container=container_name, 
                blob=unique_filename
            )
            
            # Ensure the file pointer is at the start
            file.seek(0)
            blob_client.upload_blob(file)
            
            return unique_filename
        else:
            # Development path: Save to local instance folder
            upload_path = current_app.config.get('UPLOAD_PATH')
            
            if not os.path.exists(upload_path):
                os.makedirs(upload_path, exist_ok=True)
            
            file.save(os.path.join(upload_path, unique_filename))
            
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
            # Extract account name from connection string to build the URL
            # Format: https://<account_name>.blob.core.windows.net/<container>/<filename>
            try:
                account_name = connection_string.split('AccountName=')[1].split(';')[0]
                container = current_app.config.get('AZURE_CONTAINER_NAME', 'uploads')
                return f"https://{account_name}.blob.core.windows.net/{container}/{filename}"
            except (IndexError, AttributeError):
                return f"/uploads/{filename}"
        
        # Fallback to local serving route
        return f"/uploads/{filename}"