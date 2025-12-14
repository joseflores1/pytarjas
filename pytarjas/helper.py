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

# MODIFIED: Added question_id argument
def save_file_to_disk(file, task_id, question_id):
    """Secures filename and saves the file to the UPLOAD_FOLDER, guaranteeing a unique name for history."""
    
    if file and allowed_file(file.filename) and task_id and question_id:
        
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower() # Ensure lowercase extension
        
        # Generate new unique name based on context and UUID
        # Note: The extension saved in the path includes the dot, e.g., '.pdf'
        base_name = f"{task_id}_{question_id}_{str(uuid.uuid4())}"
        unique_filename = base_name + file_ext
        
        upload_path = os.path.join(current_app.instance_path, current_app.config['UPLOAD_FOLDER'])
        
        if not os.path.isdir(upload_path):
            os.makedirs(upload_path, exist_ok=True)
            
        full_path = os.path.join(upload_path, unique_filename)
        
        try:
            file.save(full_path)
        except Exception as e:
            current_app.logger.error(f"Failed to save file {full_path}: {e}")
            return None
        
        # Return the relative path for database storage
        return f"{current_app.config['UPLOAD_FOLDER']}/{unique_filename}"
        
    else:
        # NEW DEBUGGING LOGIC: Explicitly log why the file was rejected
        if not (task_id and question_id):
             current_app.logger.warning("File rejected: Missing task ID or question ID.")
        elif file and file.filename and '.' in file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower()
            current_app.logger.warning(
                f"File rejected: Extension '.{ext}' not in ALLOWED_EXTENSIONS. Configured: {current_app.config.get('ALLOWED_EXTENSIONS')}"
            )
        elif file:
             current_app.logger.warning("File rejected: Invalid filename or missing file object.")
             
    return None