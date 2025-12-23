/* pytarjas/static/js/tasks/create.js */

document.addEventListener('DOMContentLoaded', function() {
    let formChanged = false;
    const taskForm = document.getElementById('createTaskForm');
    const formSelect = document.getElementById('form_id');
    const planningSelect = document.getElementById('planning_id');
    const predefinedContainer = document.getElementById('predefinedMetadataContainer');
    const fieldsContainer = document.getElementById('fieldsContainer');
    const addFieldBtn = document.getElementById('addFieldBtn');
    const emptyFieldsState = document.getElementById('emptyFieldsState');
    const templatesData = document.getElementById('planningTemplatesData');

    /**
     * Renders predefined fields based on the selected Planning Template.
     * @param {string} planningId 
     */
    function renderPlanningFields(planningId) {
        predefinedContainer.innerHTML = '';
        
        if (!planningId) {
            predefinedContainer.style.display = 'none';
            return;
        }

        const source = templatesData.querySelector(`[data-planning-id="${planningId}"]`);
        
        if (!source) {
            predefinedContainer.style.display = 'none';
            return;
        }

        const fields = source.querySelectorAll('span');
        
        if (fields.length > 0) {
            predefinedContainer.style.display = 'block';
            
            const header = document.createElement('h4');
            header.style.fontSize = '0.9rem';
            header.style.marginBottom = 'var(--space-md)';
            header.style.color = 'var(--color-primary)';
            header.textContent = 'Atributos de la Planificación:';
            predefinedContainer.appendChild(header);

            fields.forEach(function(field) {
                const group = document.createElement('div');
                group.className = 'form-group';

                const label = document.createElement('label');
                label.className = 'form-label';
                label.textContent = field.dataset.fieldLabel;

                if (field.dataset.isRequired === 'true') {
                    const req = document.createElement('span');
                    req.style.color = 'var(--color-danger)';
                    req.textContent = ' *';
                    label.appendChild(req);
                }

                group.appendChild(label);

                let input;
                const fieldType = field.dataset.fieldType;
                const fieldName = field.dataset.fieldName;

                if (fieldType === 'select') {
                    input = document.createElement('select');
                    input.className = 'form-control';
                    
                    const defOpt = document.createElement('option');
                    defOpt.value = '';
                    defOpt.textContent = '-- Seleccione --';
                    input.appendChild(defOpt);

                    const opts = JSON.parse(field.dataset.options || '{}');
                    if (opts.choices) {
                        opts.choices.forEach(function(choice) {
                            const opt = document.createElement('option');
                            opt.value = choice;
                            opt.textContent = choice;
                            input.appendChild(opt);
                        });
                    }
                } else if (fieldType === 'boolean') {
                    input = document.createElement('select');
                    input.className = 'form-control';
                    input.add(new Option('No', 'false'));
                    input.add(new Option('Sí', 'true'));
                } else if (fieldType === 'date') {
                    input = document.createElement('input');
                    input.className = 'form-control';
                    input.type = 'date';
                } else {
                    input = document.createElement('input');
                    input.className = 'form-control';
                    input.type = (fieldType === 'number') ? 'number' : 'text';
                }

                input.name = `predefined_${fieldName}`;
                input.dataset.isPredefined = 'true';
                input.dataset.key = fieldName;
                
                if (field.dataset.isRequired === 'true') {
                    input.required = true;
                }

                group.appendChild(input);
                predefinedContainer.appendChild(group);
            });
        } else {
            predefinedContainer.style.display = 'none';
        }
    }

    /**
     * Updates the empty state message visibility for ad-hoc fields.
     */
    function updateEmptyState() {
        if (fieldsContainer.children.length === 0) {
            emptyFieldsState.style.display = 'block';
        } else {
            emptyFieldsState.style.display = 'none';
        }
    }

    /**
     * Creates and appends a new ad-hoc metadata field row.
     */
    function createAdhocField() {
        const fieldRow = document.createElement('div');
        fieldRow.className = 'adhoc-field-row';
        fieldRow.style.display = 'flex';
        fieldRow.style.gap = 'var(--space-sm)';
        fieldRow.style.marginBottom = 'var(--space-sm)';
        fieldRow.style.alignItems = 'flex-start';

        fieldRow.innerHTML = `
            <div style="flex: 1;">
                <input type="text" class="form-control field-key" placeholder="Etiqueta (Ej: Sello)" required>
            </div>
            <div style="flex: 2;">
                <input type="text" class="form-control field-value" placeholder="Valor" required>
            </div>
            <button type="button" class="btn btn-danger btn-sm remove-field-btn" style="margin-top: 5px;">✕</button>
        `;

        fieldRow.querySelector('.remove-field-btn').addEventListener('click', function() {
            fieldRow.remove();
            updateEmptyState();
        });

        fieldsContainer.appendChild(fieldRow);
        updateEmptyState();
        formChanged = true;
    }

    // --- Event Listeners ---

    planningSelect?.addEventListener('change', function() {
        renderPlanningFields(this.value);
        formChanged = true;
    });

    addFieldBtn?.addEventListener('click', function() {
        createAdhocField();
    });

    formSelect?.addEventListener('change', function() {
        const preview = document.getElementById('formPreview');
        const selected = this.options[this.selectedIndex];
        
        if (selected.value) {
            document.getElementById('previewName').textContent = selected.dataset.name;
            document.getElementById('previewDescription').textContent = selected.dataset.description || 'Sin descripción';
            document.getElementById('previewType').textContent = selected.dataset.type || 'General';
            preview.classList.add('visible');
        } else {
            preview.classList.remove('visible');
        }
        formChanged = true;
    });

    taskForm?.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const submitBtn = document.getElementById('submitBtn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '⏳ Procesando...';

        // Collect predefined metadata (from Planning Template)
        const metadataValues = {};
        predefinedContainer.querySelectorAll('[data-is-predefined="true"]').forEach(function(input) {
            metadataValues[input.dataset.key] = input.value;
        });

        // Collect ad-hoc metadata (manual fields)
        const adhocMetadata = [];
        fieldsContainer.querySelectorAll('.adhoc-field-row').forEach(function(row) {
            const key = row.querySelector('.field-key').value;
            const val = row.querySelector('.field-value').value;
            if (key.trim()) {
                adhocMetadata.push({ key: key.trim(), value: val });
            }
        });

        const payload = {
            form_id: formSelect.value,
            planning_id: planningSelect.value || null,
            worker_id: document.getElementById('worker_id')?.value,
            metadata_values: metadataValues,
            ad_hoc_metadata: adhocMetadata
        };

        try {
            const response = await fetch(window.location.href, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            
            if (result.success) {
                formChanged = false;
                window.location.href = '/tasks/';
            } else {
                alert('Error: ' + result.error);
                submitBtn.disabled = false;
                submitBtn.innerHTML = '✓ Crear Tarea';
            }
        } catch (err) {
            console.error('Submission error:', err);
            submitBtn.disabled = false;
            submitBtn.innerHTML = '✓ Crear Tarea';
        }
    });

    const backHandler = function(e) {
        if (formChanged && !confirm('¿Desea salir sin guardar los cambios?')) {
            e.preventDefault();
        }
    };

    document.getElementById('cancelBtn')?.addEventListener('click', backHandler);
    document.getElementById('headerBackBtn')?.addEventListener('click', backHandler);
});