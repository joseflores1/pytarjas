-- scripts/create_form.sql
-- Restores all original question types while complying with the versioned Form model.

DO $$ 
DECLARE 
    form_uuid UUID := gen_random_uuid();
    -- Fetch an admin ID for the creator field
    creator_id_val VARCHAR(36) := (SELECT id FROM users WHERE role = 'admin' LIMIT 1); 
BEGIN

-- 1. Insert the main Form record with the 'version' column
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

-- 2. Insert Question records for each supported type

-- A. Text (Short)
INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Nombre del Contenedor / Tarea', 'Ingrese el identificador principal del contenedor (ej: ABCU1234567).', 'text', TRUE, 1, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

-- B. Textarea (Long Text)
INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Observaciones Generales de la Faena', 'Registre cualquier novedad, daño o incidente que requiera descripción detallada.', 'textarea', FALSE, 2, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

-- C. Number
INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Cantidad de Bultos Encontrados', 'Debe ser un número entero. Verifique el manifiesto.', 'number', TRUE, 3, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

-- D. Date
INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Fecha de Inicio de Faena', NULL, 'date', TRUE, 4, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

-- E. Datetime
INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Hora de Término de la Revisión', NULL, 'datetime', TRUE, 5, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

-- F. Photo
INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Fotografía del Sello/Candado Inicial', 'Capture la imagen del sello del contenedor antes de romperlo.', 'photo', TRUE, 6, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

-- G. Select (Dropdown)
INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Condición General de la Carga', NULL, 'select', TRUE, 7, '{"choices": ["Buena", "Aceptable", "Húmeda", "Dañada/Roto"]}'::jsonb, NOW() AT TIME ZONE 'UTC');

-- H. File (Document attachment)
INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Adjuntar Manifiesto de Carga (PDF/DOC)', 'Permite adjuntar cualquier documento de soporte adicional.', 'file', FALSE, 8, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

-- I. Boolean (Yes/No)
INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, '¿El peso coincide con el manifiesto?', NULL, 'boolean', TRUE, 9, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

-- J. Client Select
INSERT INTO question (id, form_id, question_text, question_description, question_type, is_required, "order", options, created_at)
VALUES (gen_random_uuid(), form_uuid, 'Selección de Cliente Final', 'Campo para integrar la lista de clientes preexistente en el sistema.', 'client_select', TRUE, 10, '{}'::jsonb, NOW() AT TIME ZONE 'UTC');

END $$;