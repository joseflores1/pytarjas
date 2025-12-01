# pytarjas/helper.py
from flask import request, current_app, flash 
import uuid
import os
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage # Added for type hinting/readability

def wants_json() -> bool:
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

def allowed_file(filename: str) -> bool:
    """Checks if a file extension is allowed based on app configuration."""
    # Check if filename exists and contains a dot
    if not (filename and '.' in filename):
        return False
        
    ext = filename.rsplit('.', 1)[1].lower()
    # Check if the extension is in the allowed set from config
    return ext in current_app.config['ALLOWED_EXTENSIONS']

def save_file_to_disk(file: FileStorage) -> str | None:
    """
    Secures filename, saves the file to the instance/uploads directory, 
    and returns the public URL path for database storage and display.
    
    The file is saved under a unique UUID filename to prevent collisions.
    The maximum size is restricted by MAX_CONTENT_LENGTH (16MB by default).
    
    Args:
        file: The FileStorage object from request.files.
        
    Returns:
        str | None: The public URL path (e.g., '/uploads/uuid.ext') or None on failure.
    """
    # Ensure file is present and allowed
    if file and allowed_file(file.filename):
        # Secure the filename
        filename = secure_filename(file.filename)
        # Generate a unique name using UUID and the file extension
        file_ext = os.path.splitext(filename)[1]
        unique_filename = str(uuid.uuid4()) + file_ext
        
        # Determine the full save path
        # Uses the configured UPLOAD_FOLDER ('uploads') within the instance_path
        upload_path = os.path.join(current_app.instance_path, current_app.config['UPLOAD_FOLDER'])
        
        # Ensure the uploads directory exists (CRITICAL FIX)
        # This is defensively handled here, but also in __init__.py
        if not os.path.isdir(upload_path):
            os.makedirs(upload_path, exist_ok=True)
            
        full_path = os.path.join(upload_path, unique_filename)
        
        # Save the file
        try:
            file.save(full_path)
        except Exception as e:
            current_app.logger.error(f"Failed to save file {full_path}: {e}")
            flash('Error saving file to disk. File size limit may have been exceeded.', 'error')
            return None
        
        # CRITICAL UPDATE: Return the public URL path, which is what the front-end 
        # needs to access the file via the /uploads route defined in __init__.py
        return f"/uploads/{unique_filename}"
        
    return None