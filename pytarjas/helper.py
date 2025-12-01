# pytarjas/helper.py
from flask import request, current_app 
import uuid
import os
from werkzeug.utils import secure_filename

def wants_json():
    """
    Helper function to determine if the client wants a JSON response.
    
    Checks multiple indicators:
    1. Content-Type header is application/json
    2. Accept header includes application/json
    3. Flask's request.is_json flag
    
    Returns:
        bool: True if client wants JSON, False if HTML
    """
    return (
        request.is_json or 
        request.headers.get("Accept") == "application/json" or
        "application/json" in request.headers.get("Accept", "")
    )

def allowed_file(filename):
    """Checks if a file extension is allowed based on app configuration."""
    # Check if filename exists and contains a dot
    if not (filename and '.' in filename):
        return False
        
    ext = filename.rsplit('.', 1)[1].lower()
    # Check if the extension is in the allowed set from config
    return ext in current_app.config['ALLOWED_EXTENSIONS']

def save_file_to_disk(file):
    """Secures filename and saves the file to the UPLOAD_FOLDER."""
    # Ensure file is present and allowed
    if file and allowed_file(file.filename):
        # Secure the filename
        filename = secure_filename(file.filename)
        # Generate a unique path using UUID to prevent collisions
        file_ext = os.path.splitext(filename)[1]
        unique_filename = str(uuid.uuid4()) + file_ext
        
        # Determine the full save path
        upload_path = os.path.join(current_app.instance_path, current_app.config['UPLOAD_FOLDER'])
        
        # Ensure the uploads directory exists
        if not os.path.isdir(upload_path):
            os.makedirs(upload_path, exist_ok=True)
            
        full_path = os.path.join(upload_path, unique_filename)
        
        # Save the file
        try:
            file.save(full_path)
        except Exception as e:
            # If saving fails, log the error but don't crash the request
            current_app.logger.error(f"Failed to save file {full_path}: {e}")
            return None
        
        # Return the relative path for database storage
        return f"{current_app.config['UPLOAD_FOLDER']}/{unique_filename}"
        
    else:
        # NEW DEBUGGING LINE: Log why the file was rejected
        if file and file.filename and '.' in file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower()
            current_app.logger.warning(
                f"File rejected: Extension '.{ext}' not in ALLOWED_EXTENSIONS ({current_app.config.get('ALLOWED_EXTENSIONS')})"
            )
        elif file:
             current_app.logger.warning("File rejected: Invalid filename or missing file object.")
             
    return None