-- scripts/create_objects.sql
-- Inserts a full demo Form, a Planning Template, and an actual Planning instance with tasks.

DO $$ 
DECLARE 
    form_uuid UUID := gen_random_uuid();
    planning_template_uuid UUID := gen_random_uuid();
    planning_uuid UUID := gen_random_uuid();
    -- Fetch an admin ID for the creator field
    creator_id_val VARCHAR(36) := (SELECT id FROM users WHERE role = 'admin' LIMIT 1); 
BEGIN

-- ============================================================================
-- 1. FORM TEMPLATE: 'Demo - Pruebas de Tipo de Pregunta'
-- ============================================================================

INSERT INTO form (
    id, 
    name, 
    version, 
    description, 
    form_type, 
    is_active, 
    created_by_id, 
    created_at
) VALUES (
    form_uuid, 
    'Demo - Pruebas de Tipo de Pregunta', 
    1, 
    'Formulario de prueba que contiene todos los tipos de entrada soportados por el sistema (Text, File, Photo, Select, etc.).', 
    'testing', 
    TRUE, 
    creator_id_val, 
    NOW() AT TIME ZONE 'UTC'
);

-- Questions for the Form
INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Nombre del Contenedor / Tarea', 'Ingrese el identificador principal del contenedor (ej: ABCU1234567).', 'text', TRUE, 1, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Observaciones Generales de la Faena', 'Registre cualquier novedad, daño o incidente que requiera descripción detallada.', 'textarea', FALSE, 2, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Cantidad de Bultos Encontrados', 'Debe ser un número entero. Verifique el manifiesto.', 'number', TRUE, 3, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Fecha de Inicio de Faena', NULL, 'date', TRUE, 4, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Hora de Término de la Revisión', NULL, 'datetime', TRUE, 5, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Fotografía del Sello/Candado Inicial', 'Capture la imagen del sello del contenedor antes de romperlo.', 'photo', TRUE, 6, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Condición General de la Carga', NULL, 'select', TRUE, 7, '{"choices": ["Buena", "Aceptable", "Húmeda", "Dañada/Roto"]}'::jsonb, NOW() AT TIME ZONE 'UTC');

INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Adjuntar Manifiesto de Carga (PDF/DOC)', 'Permite adjuntar cualquier documento de soporte adicional.', 'file', FALSE, 8, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, '¿El peso coincide con el manifiesto?', NULL, 'boolean', TRUE, 9, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');


-- ============================================================================
-- 2. PLANNING TEMPLATE: 'Demo - Metadata de Operación'
-- ============================================================================

INSERT INTO planning_template (
    id, 
    name, 
    description, 
    created_by_id, 
    created_at
) VALUES (
    planning_template_uuid, 
    'Demo - Metadata de Operación Logística', 
    'Plantilla base para capturar información de cabecera de una planificación (Barco, Terminal, etc.) y definir las columnas dinámicas de la tabla de tareas.', 
    creator_id_val, 
    NOW() AT TIME ZONE 'UTC'
);

-- Metadata Fields for the Planning Template
-- Note: 'is_row_field' is FALSE for header fields and TRUE for table row fields.

-- Header Fields (Global information)
INSERT INTO planning_metadata_field (id, template_id, field_label, field_name, field_type, is_required, is_row_field, "order", options, created_at)
VALUES (gen_random_uuid(), planning_template_uuid, 'Nombre de la Nave', 'vessel_name', 'text', TRUE, FALSE, 1, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

INSERT INTO planning_metadata_field (id, template_id, field_label, field_name, field_type, is_required, is_row_field, "order", options, created_at)
VALUES (gen_random_uuid(), planning_template_uuid, 'Terminal de Operación', 'terminal', 'select', TRUE, FALSE, 2, '{"choices": ["TPS", "DP World", "SVTI", "ATI"]}'::jsonb, NOW() AT TIME ZONE 'UTC');

-- Row Fields (Dynamic columns in the task table)
INSERT INTO planning_metadata_field (id, template_id, field_label, field_name, field_type, is_required, is_row_field, "order", options, created_at)
VALUES (gen_random_uuid(), planning_template_uuid, 'N° Contenedor', 'container_number', 'text', TRUE, TRUE, 3, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

INSERT INTO planning_metadata_field (id, template_id, field_label, field_name, field_type, is_required, is_row_field, "order", options, created_at)
VALUES (gen_random_uuid(), planning_template_uuid, 'Sello', 'seal', 'text', FALSE, TRUE, 4, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

INSERT INTO planning_metadata_field (id, template_id, field_label, field_name, field_type, is_required, is_row_field, "order", options, created_at)
VALUES (gen_random_uuid(), planning_template_uuid, 'Tipo de Unidad', 'type', 'select', TRUE, TRUE, 5, '{"choices": ["20GP", "40HC", "40RF", "20RF"]}'::jsonb, NOW() AT TIME ZONE 'UTC');


-- ============================================================================
-- 3. PLANNING INSTANCE: 'Demo - Faena de Importación'
-- ============================================================================

INSERT INTO planning (
    id, 
    planner_id, 
    form_id, 
    template_id, 
    metadata_values, 
    client_name, 
    status, 
    total_tasks, 
    created_at
) VALUES (
    planning_uuid, 
    creator_id_val, 
    form_uuid, 
    planning_template_uuid, 
    '{
        "vessel_name": "MS Explorer",
        "terminal": "TPS"
    }'::jsonb, 
    'Importaciones ABC S.A.', 
    'uploaded', 
    2, 
    NOW() AT TIME ZONE 'UTC'
);

-- ============================================================================
-- 4. ASSOCIATED TASKS (Using dynamic record_data)
-- ============================================================================

INSERT INTO task (
    id, 
    planning_id, 
    form_id, 
    record_data, 
    worker_id, 
    created_by_id, 
    status, 
    responses, 
    is_synced,
    created_at
) VALUES (
    gen_random_uuid(), 
    planning_uuid, 
    form_uuid, 
    '{"container_number": "CONT-A1", "seal": "S-100", "type": "40HC"}'::jsonb, 
    creator_id_val, 
    creator_id_val, 
    'pending', 
    '{}'::jsonb, 
    TRUE,
    NOW() AT TIME ZONE 'UTC'
);

INSERT INTO task (
    id, 
    planning_id, 
    form_id, 
    record_data, 
    worker_id, 
    created_by_id, 
    status, 
    responses, 
    is_synced,
    created_at
) VALUES (
    gen_random_uuid(), 
    planning_uuid, 
    form_uuid, 
    '{"container_number": "CONT-B2", "seal": "S-101", "type": "20GP"}'::jsonb, 
    creator_id_val, 
    creator_id_val, 
    'pending', 
    '{}'::jsonb, 
    TRUE,
    NOW() AT TIME ZONE 'UTC'
);

END $$;