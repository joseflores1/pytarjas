# pytarjas/services/pdf_service.py
"""
Service for generating high-quality PDF reports using ReportLab.
This implementation replicates the original high-fidelity design 
while remaining compatible with Azure App Service by avoiding 
system-level library dependencies.
"""

import os
import json
import logging
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, Image, PageBreak, LongTable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from flask import current_app
from pytarjas.models.docs_models import Task

# Configure logger
logger = logging.getLogger(__name__)

def get_absolute_path(web_path):
    """
    Converts a web path to an absolute system path for image embedding.
    Ensures compatibility between Local and Azure environments.
    """
    if not web_path:
        return None
    
    clean_path = web_path.lstrip('/')
    abs_path = os.path.join(current_app.instance_path, clean_path)
    
    if not os.path.exists(abs_path):
        abs_path = os.path.join(current_app.root_path, clean_path)
    
    if os.path.exists(abs_path):
        return abs_path
        
    return None

def format_value(value):
    """
    Helper to format dates, times, and booleans into friendly strings.
    Ensures dates always show hours and minutes (DD-MM-YYYY HH:MM).
    """
    if value is None or value == "" or value == "[]":
        return "---"
    
    if isinstance(value, bool):
        if value:
            return 'Sí'
        else:
            return 'No'
    
    if isinstance(value, datetime):
        return value.strftime('%d-%m-%Y %H:%M')
        
    if isinstance(value, str):
        try:
            if len(value) >= 10 and value[4] == '-' and value[7] == '-':
                if len(value) == 10:
                    dt = datetime.strptime(value, '%Y-%m-%d')
                    return dt.strftime('%d-%m-%Y %H:%M')
                else:
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return dt.strftime('%d-%m-%Y %H:%M')
            
            if value.lower() == 'true': 
                return 'Sí'
            if value.lower() == 'false': 
                return 'No'
        except (ValueError, TypeError):
            pass
            
    return str(value)

def calculate_duration(task: Task) -> str:
    """Calculates formatted duration string between start and completion."""
    if task.started_at and task.completed_at:
        diff = task.completed_at - task.started_at
        seconds = int(diff.total_seconds())
        h = seconds // 3600
        m = (seconds % 3600) // 60
        if h > 0:
            return f"{h} hrs {m} min"
        else:
            return f"{m} min"
    return "---"

# --- CONSTANTS ---
ORANGE = colors.Color(245/255, 130/255, 32/255)
DARK_BLUE = colors.Color(44/255, 62/255, 80/255)
GRAY_TEXT = colors.Color(127/255, 140/255, 141/255)
LIGHT_BG = colors.Color(249/255, 249/255, 249/255)
BORDER_COLOR = colors.Color(230/255, 230/255, 230/255)
TABLE_HEADER_BG = colors.Color(236/255, 240/255, 241/255)
TABLE_BORDER = colors.Color(200/255, 200/255, 200/255)

def draw_header(canvas, doc):
    """
    Draws the stylized header with reduced vertical space.
    """
    canvas.saveState()
    
    logo_path = get_absolute_path('static/icons/HGT-Logo-greyblue-orange-RGB-512x512.png')
    
    if logo_path:
        try:
            # COMPACT POSITIONING:
            draw_x = 0.8 * cm
            draw_w = 12.0 * cm 
            draw_h = 5.0 * cm
            # Shifted up: Bottom of logo at 5.1cm from top instead of 5.5cm
            draw_y = A4[1] - 6 * cm 
            
            canvas.drawImage(
                logo_path, 
                draw_x, 
                draw_y, 
                width=draw_w, 
                height=draw_h,
                preserveAspectRatio=True, 
                anchor='sw', 
                mask='auto'
            )
        except Exception as e:
            logger.error(f"Logo drawing error: {e}")
    
    # Metadata shifted UP to reduce header height
    canvas.setFont('Helvetica-Bold', 18)
    canvas.setFillColor(DARK_BLUE)
    canvas.drawRightString(
        A4[0] - 1.2 * cm, 
        A4[1] - 1.5 * cm, 
        getattr(doc, 'form_name', 'REPORTE DE TARJA').upper()
    )
    
    canvas.setFont('Helvetica', 10)
    canvas.setFillColor(GRAY_TEXT)
    canvas.drawRightString(
        A4[0] - 1.2 * cm, 
        A4[1] - 2.2 * cm, 
        f"ID Tarea: #{getattr(doc, 'task_id', '---')}"
    )
    
    canvas.drawRightString(
        A4[0] - 1.2 * cm, 
        A4[1] - 2.7 * cm, 
        f"Generado: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
    )
    
    # Orange line pulled UP right under the logo
    canvas.setStrokeColor(ORANGE)
    canvas.setLineWidth(2.5)
    canvas.line(doc.leftMargin, A4[1] - 5.3 * cm, A4[0] - doc.rightMargin, A4[1] - 5.3 * cm)
    
    canvas.restoreState()

def generate_tarja_pdf(task: Task) -> bytes:
    """
    Main function to generate the PDF report using the ReportLab Platypus engine.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=1.2*cm, 
        leftMargin=1.2*cm, 
        topMargin=5.8*cm, # Reduced from 6.5cm to start content higher
        bottomMargin=1.5*cm
    )
    
    doc.form_name = task.form.name if task.form else "REPORTE DE TARJA"
    doc.task_id = str(task.id)
    
    styles = getSampleStyleSheet()
    
    # Section title style (Explicit Orange text, no borders)
    title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        textColor=ORANGE,
        fontSize=12,
        fontName='Helvetica-Bold',
        spaceBefore=18,
        spaceAfter=10,
        textTransform='uppercase'
    )
    
    label_style = ParagraphStyle(
        'LabelStyle',
        fontSize=8,
        leading=10,
        fontName='Helvetica-Bold',
        color=DARK_BLUE,
        textTransform='uppercase',
        leftIndent=2
    )
    
    value_style = ParagraphStyle(
        'ValueStyle',
        fontSize=10,
        leading=14,
        fontName='Helvetica',
        color=colors.black,
        backColor=LIGHT_BG,
        borderPadding=(5, 5, 5, 5),
        borderRadius=3,
        borderWidth=0.5,
        borderColor=BORDER_COLOR
    )
    
    cell_style = ParagraphStyle(
        'TableCell',
        fontSize=9.5,
        leading=14,
        fontName='Helvetica'
    )
    
    header_style = ParagraphStyle(
        'HeaderCell',
        parent=cell_style,
        fontName='Helvetica-Bold',
        color=DARK_BLUE
    )

    elements = []
    
    # --- 1. INFORMACIÓN GENERAL ---
    elements.append(Paragraph("Información Faena", title_style))
    items = []
    
    if task.planning and task.planning.template:
        for f in sorted(task.planning.template.fields, key=lambda x: x.order):
            if not f.is_row_field:
                items.append((f.field_label, format_value(task.planning.metadata_values.get(f.field_name))))
    
    items.extend([
        ('Tarjador', task.worker.username if task.worker else '---'),
        ('Fecha Faena', format_value(task.completed_at)),
        ('Duración Faena', calculate_duration(task))
    ])
    
    for i in range(0, len(items), 4):
        chunk = items[i:i+4]
        row_l = [Paragraph(x[0], label_style) for x in chunk] + [""]*(4-len(chunk))
        row_v = [Paragraph(x[1], value_style) for x in chunk] + [""]*(4-len(chunk))
        
        elements.append(Table([row_l], colWidths=[4.6*cm]*4, style=[
            ('LEFTPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),1)
        ]))
        elements.append(Table([row_v], colWidths=[4.6*cm]*4, style=[
            ('LEFTPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),8)
        ]))

    # --- 2. DATOS DEL REGISTRO ---
    reg_items = []
    if task.planning and task.planning.template:
        for f in sorted(task.planning.template.fields, key=lambda x: x.order):
            if f.is_row_field:
                reg_items.append((f.field_label, format_value(task.record_data.get(f.field_name))))
    
    if reg_items:
        elements.append(Paragraph("Datos del Registro", title_style))
        for i in range(0, len(reg_items), 4):
            chunk = reg_items[i:i+4]
            row_l = [Paragraph(x[0], label_style) for x in chunk] + [""]*(4-len(chunk))
            row_v = [Paragraph(x[1], value_style) for x in chunk] + [""]*(4-len(chunk))
            
            elements.append(Table([row_l], colWidths=[4.6*cm]*4, style=[
                ('LEFTPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),1)
            ]))
            elements.append(Table([row_v], colWidths=[4.6*cm]*4, style=[
                ('LEFTPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),8)
            ]))

    # --- 3. OBSERVACIONES Y CONTROL ---
    elements.append(Paragraph("Observaciones y Control", title_style))
    obs_data = [[Paragraph("Ítem / Pregunta", header_style), Paragraph("Respuesta / Detalle", header_style)]]
    gallery = []
    
    if task.form:
        for q in sorted(task.form.questions, key=lambda x: x.order):
            res = task.responses.get(q.id)
            if res is None: 
                continue
            
            if q.question_type in ['photo', 'file']:
                try:
                    if isinstance(res, str) and res.startswith('['):
                        paths = json.loads(res)
                    elif not isinstance(res, list):
                        paths = [res]
                    else:
                        paths = res
                    if paths: 
                        gallery.append({'l': q.question_text, 'p': paths})
                except Exception: 
                    pass
            else:
                obs_data.append([Paragraph(q.question_text, cell_style), Paragraph(format_value(res), cell_style)])
    
    t = LongTable(obs_data, colWidths=[7.5*cm, 11*cm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_BG),
        ('GRID', (0,0), (-1,-1), 0.5, TABLE_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.Color(252/255, 252/255, 252/255)]),
        ('TOPPADDING', (0,0), (-1,-1), 10), 
        ('BOTTOMPADDING', (0,0), (-1,-1), 10), 
        ('LEFTPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(t)

    # --- 4. REGISTRO FOTOGRÁFICO ---
    if gallery:
        elements.append(PageBreak())
        elements.append(Paragraph("Registro Fotográfico", title_style))
        for g in gallery:
            elements.append(Paragraph(g['l'], label_style))
            elements.append(Spacer(1, 8))
            row = []
            for path in g['p']:
                abs_p = get_absolute_path(path)
                if abs_p:
                    try:
                        img = Image(abs_p, width=8.8*cm, height=6.6*cm, kind='proportional')
                        row.append(img)
                        if len(row) == 2:
                            elements.append(Table([row], colWidths=[9.2*cm, 9.2*cm], style=[
                                ('ALIGN',(0,0),(-1,-1),'CENTER'),
                                ('VALIGN',(0,0),(-1,-1),'MIDDLE')
                            ]))
                            elements.append(Spacer(1, 12))
                            row = []
                    except Exception: 
                        pass
            
            if row: 
                elements.append(Table([row+[""]], colWidths=[9.2*cm, 9.2*cm]))
            elements.append(Spacer(1, 20))

    doc.build(elements, onFirstPage=draw_header, onLaterPages=draw_header)
    return buffer.getvalue()