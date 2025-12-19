# pytarjas/services/pdf_service.py
"""
Service for generating PDF reports.
Uses absolute paths with file:// protocol to ensure WeasyPrint renders images correctly.
"""

import io
import os
import json
from datetime import datetime
from flask import render_template, current_app
from weasyprint import HTML
from pytarjas.models.docs_models import Task

def get_absolute_path(web_path):
    """
    Converts a web path to an absolute system path for WeasyPrint.
    """
    if not web_path:
        return None
    
    if web_path.startswith('/'):
        web_path = web_path[1:]
        
    upload_folder_name = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    
    # Check if path belongs to uploads
    if web_path.startswith(upload_folder_name):
        abs_path = os.path.join(current_app.instance_path, web_path)
        if not os.path.exists(abs_path):
             abs_path_root = os.path.join(current_app.root_path, web_path)
             if os.path.exists(abs_path_root):
                 abs_path = abs_path_root
    else:
        abs_path = os.path.join(current_app.root_path, web_path)
    
    if os.path.exists(abs_path):
        return f"file://{abs_path}"
        
    return None

def format_value(value):
    """
    Helper to format dates, times, and booleans into friendly strings.
    Ensures dates always show hours and minutes.
    """
    if value is None:
        return ""
    
    # Handle Booleans
    if str(value).lower() == 'true': 
        return 'Sí'
        
    if str(value).lower() == 'false': 
        return 'No'
    
    # Handle Datetime Objects (Native)
    if isinstance(value, datetime):
        return value.strftime('%d/%m/%Y %H:%M')
        
    # Handle Date Strings (ISO format detection)
    if isinstance(value, str):
        try:
            # Check for basic date format (YYYY-MM-DD)
            if len(value) == 10 and value[4] == '-' and value[7] == '-':
                dt = datetime.strptime(value, '%Y-%m-%d')
                # Even for simple dates, we keep consistency if needed, 
                # but usually day/month/year is enough for a "date-only" field.
                return dt.strftime('%d/%m/%Y')
            
            # Check for datetime format (YYYY-MM-DDTHH:MM...)
            if len(value) > 10 and value[4] == '-' and value[7] == '-':
                 dt = datetime.fromisoformat(value)
                 return dt.strftime('%d/%m/%Y %H:%M')
        except ValueError:
            # Not a date, return as is
            pass
            
    return value

def calculate_duration(task: Task) -> str:
    """Calculates formatted duration between start and completion."""
    if task.started_at and task.completed_at:
        diff = task.completed_at - task.started_at
        total_seconds = int(diff.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        parts = []
        if hours > 0:
            parts.append(f"{hours} hrs")
            
        if minutes > 0 or hours == 0:
            parts.append(f"{minutes} min")
            
        return " ".join(parts)
        
    return "---"

def generate_tarja_pdf(task: Task) -> bytes:
    """
    Generates a PDF for a specific completed Task using WeasyPrint.
    """
    form_type = 'generic'
    if task.form:
        form_type = task.form.form_type
        
    template_name = 'pdfs/tarja_consolidado.html'

    table_rows = []
    gallery_groups = []
    
    if task.form and task.form.questions:
        sorted_questions = sorted(task.form.questions, key=lambda x: x.order)
        
        for question in sorted_questions:
            response_value = task.responses.get(question.id)
            if response_value is None:
                continue

            # Handle Photos and Files (Gallery)
            if question.question_type in ['photo', 'file']:
                paths = []
                if isinstance(response_value, str) and response_value.startswith('['):
                    try:
                        paths = json.loads(response_value)
                    except json.JSONDecodeError:
                        paths = []
                elif isinstance(response_value, list):
                    paths = response_value
                else:
                    paths = [str(response_value)]
                
                valid_paths = []
                for p in paths:
                    if not p: 
                        continue
                        
                    abs_p = get_absolute_path(p)
                    if abs_p:
                        valid_paths.append(abs_p)
                
                if valid_paths:
                    gallery_groups.append({
                        'label': question.question_text,
                        'paths': valid_paths
                    })

            # Handle Standard Data
            else:
                formatted_val = format_value(response_value)
                table_rows.append({
                    'label': question.question_text,
                    'value': formatted_val
                })

    # Prepare Context
    formatted_record_data = {}
    for k, v in task.record_data.items():
        formatted_record_data[k] = format_value(v)
    
    duration_str = calculate_duration(task)

    context = {
        'task_id': task.id,
        'created_at': format_value(task.created_at),
        'completed_at': task.completed_at or datetime.now(),
        'worker_name': task.worker.username if task.worker else "Sin Asignar",
        'form_name': task.form.name if task.form else "Formulario",
        'form_type': form_type,
        'now': datetime.now(),
        'duration': duration_str,
        'table_rows': table_rows,
        'gallery_groups': gallery_groups
    }
    
    # Merge formatted record data into context
    context.update(formatted_record_data)

    html_string = render_template(template_name, **context)

    static_folder = os.path.join(current_app.root_path, 'static')
    pdf_file = io.BytesIO()
    
    # base_url is set to the static folder to resolve relative links in the template
    HTML(string=html_string, base_url=static_folder).write_pdf(pdf_file)
    
    pdf_file.seek(0)
    return pdf_file.read()