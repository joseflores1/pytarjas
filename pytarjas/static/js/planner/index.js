/* pytarjas/static/js/planner/index.js */

document.addEventListener('DOMContentLoaded', function() {
    const addRowBtn = document.getElementById('addRowBtn');
    const tableBody = document.getElementById('planningTableBody');
    const emptyState = document.getElementById('emptyState');
    const planningForm = document.getElementById('createPlanningForm');
    const fileInput = document.getElementById('fileInput');
    
    // Header Metadata Elements
    const templateSelect = document.getElementById('template_id');
    const addHeaderFieldBtn = document.getElementById('addHeaderFieldBtn');
    const headerFieldsContainer = document.getElementById('headerFieldsContainer');
    const emptyHeaderState = document.getElementById('emptyHeaderState');

    // --- 1. Data Initialization ---
    const usersMap = {};
    const userSpans = document.querySelectorAll('#usersMap span');
    userSpans.forEach(function(span) {
        usersMap[span.dataset.id] = span.dataset.username;
    });

    let planningTemplates = [];
    const templatesDataElem = document.getElementById('planningTemplatesData');
    if (templatesDataElem) {
        try {
            planningTemplates = JSON.parse(templatesDataElem.value);
        } catch (e) {
            console.error("Error parsing planning templates data", e);
        }
    }

    // --- 2. Header Metadata Management (Dynamic Rows) ---

    /**
     * Injects or removes column headers and handles the empty state message.
     */
    function updateHeaderEmptyState() {
        if (!headerFieldsContainer) {
            return;
        }

        const rows = headerFieldsContainer.querySelectorAll('.adhoc-header-row');
        let headerLabelRow = document.getElementById('headerColumnLabels');

        if (rows.length === 0) {
            if (emptyHeaderState) {
                emptyHeaderState.style.display = 'block';
            }
            if (headerLabelRow) {
                headerLabelRow.remove();
            }
        } else {
            if (emptyHeaderState) {
                emptyHeaderState.style.display = 'none';
            }
            
            if (!headerLabelRow) {
                headerLabelRow = document.createElement('div');
                headerLabelRow.id = 'headerColumnLabels';
                headerLabelRow.style.display = 'grid';
                headerLabelRow.style.gridTemplateColumns = '1.5fr 1.2fr 2fr 40px';
                headerLabelRow.style.gap = 'var(--space-sm)';
                headerLabelRow.style.marginBottom = 'var(--space-xs)';
                headerLabelRow.style.padding = '0 var(--space-xs)';
                headerLabelRow.style.fontSize = '0.75rem';
                headerLabelRow.style.fontWeight = 'bold';
                headerLabelRow.style.color = 'var(--color-text-secondary)';
                headerLabelRow.style.textTransform = 'uppercase';

                headerLabelRow.innerHTML = `
                    <div>Etiqueta</div>
                    <div>Tipo de Dato</div>
                    <div>Valor actual</div>
                    <div></div>
                `;
                headerFieldsContainer.prepend(headerLabelRow);
            }
        }
    }

    /**
     * Creates an editable header field row with support for various data types.
     */
    function createHeaderFieldRow(initialLabel = '', initialType = 'text', initialValue = '', initialOptions = {}) {
        const row = document.createElement('div');
        row.className = 'adhoc-header-row';
        row.style.display = 'flex';
        row.style.flexDirection = 'column';
        row.style.gap = 'var(--space-xs)';
        row.style.marginBottom = 'var(--space-sm)';
        row.style.padding = 'var(--space-sm)';
        row.style.background = 'var(--color-bg-primary)';
        row.style.border = '1px solid var(--color-border)';
        row.style.borderRadius = 'var(--radius-sm)';

        const mainControls = document.createElement('div');
        mainControls.style.display = 'grid';
        mainControls.style.gridTemplateColumns = '1.5fr 1.2fr 2fr 40px';
        mainControls.style.gap = 'var(--space-sm)';
        mainControls.style.alignItems = 'center';

        // Label
        const labelInput = document.createElement('input');
        labelInput.type = 'text';
        labelInput.className = 'form-control header-label';
        labelInput.placeholder = 'Ej: Sello';
        labelInput.value = initialLabel;
        labelInput.required = true;

        // Type Select - Includes Question types (except file/photo)
        const typeSelect = document.createElement('select');
        typeSelect.className = 'form-control header-type';
        const types = [
            { val: 'text', label: 'Texto Corto' },
            { val: 'textarea', label: 'Texto Largo' },
            { val: 'number', label: 'Número' },
            { val: 'date', label: 'Fecha' },
            { val: 'datetime', label: 'Fecha y Hora' },
            { val: 'boolean', label: 'Booleano (Sí/No)' },
            { val: 'select', label: 'Selección Múltiple' },
            { val: 'client_select', label: 'Selector Cliente' }
        ];
        types.forEach(function(t) {
            const opt = document.createElement('option');
            opt.value = t.val;
            opt.textContent = t.label;
            if (t.val === initialType) {
                opt.selected = true;
            }
            typeSelect.appendChild(opt);
        });

        const valueContainer = document.createElement('div');
        valueContainer.className = 'header-value-container';

        // Container for 'select' choices configuration
        const choicesWrapper = document.createElement('div');
        choicesWrapper.className = 'choices-wrapper';
        choicesWrapper.style.display = 'none';
        choicesWrapper.style.marginTop = 'var(--space-xs)';
        choicesWrapper.style.padding = 'var(--space-xs)';
        choicesWrapper.style.border = '1px dashed var(--color-border)';
        choicesWrapper.style.borderRadius = 'var(--radius-sm)';

        function renderValueInput(type, value = '', options = {}) {
            valueContainer.innerHTML = '';
            choicesWrapper.style.display = 'none';
            let input;

            if (type === 'boolean') {
                input = document.createElement('select');
                input.className = 'form-control header-value';
                input.add(new Option('No', 'false'));
                input.add(new Option('Sí', 'true'));
                if (value === 'true' || value === true) {
                    input.value = 'true';
                }
            } else if (type === 'textarea') {
                input = document.createElement('textarea');
                input.className = 'form-control header-value';
                input.rows = 1;
                input.value = value;
                input.style.minHeight = '38px';
            } else if (type === 'select') {
                choicesWrapper.style.display = 'block';
                input = document.createElement('select');
                input.className = 'form-control header-value';
                
                const defOpt = document.createElement('option');
                defOpt.value = '';
                defOpt.textContent = '-- Seleccione --';
                input.appendChild(defOpt);
                
                const choicesList = options.choices || [];
                choicesList.forEach(function(choice) {
                    const opt = document.createElement('option');
                    opt.value = choice;
                    opt.textContent = choice;
                    if (choice === value) {
                        opt.selected = true;
                    }
                    input.appendChild(opt);
                });

                // Choice definition UI (comma separated)
                choicesWrapper.innerHTML = `
                    <div style="font-size: 0.75rem; font-weight: bold; margin-bottom: 5px;">Configurar Opciones (separadas por coma):</div>
                    <input type="text" class="form-control form-control-sm header-choices-config" value="${choicesList.join(', ')}" placeholder="Opción A, Opción B">
                `;
                const choicesConfig = choicesWrapper.querySelector('.header-choices-config');
                choicesConfig.addEventListener('input', function() {
                    const newChoices = this.value.split(',').map(s => s.trim()).filter(s => s);
                    input.innerHTML = '';
                    input.appendChild(new Option('-- Seleccione --', ''));
                    newChoices.forEach(c => input.appendChild(new Option(c, c)));
                });
            } else if (type === 'client_select') {
                input = document.createElement('select');
                input.className = 'form-control header-value';
                input.add(new Option('Cargando Clientes...', ''));
                // Note: Logic for fetching clients would be handled here if available
            } else {
                input = document.createElement('input');
                input.className = 'form-control header-value';
                input.value = value;
                if (type === 'number') {
                    input.type = 'number';
                } else if (type === 'date') {
                    input.type = 'date';
                } else if (type === 'datetime') {
                    input.type = 'datetime-local';
                } else {
                    input.type = 'text';
                }
            }
            
            input.required = true;
            valueContainer.appendChild(input);
        }

        renderValueInput(initialType, initialValue, initialOptions);

        typeSelect.addEventListener('change', function() {
            renderValueInput(this.value);
        });

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-danger btn-sm';
        removeBtn.style.height = '38px';
        removeBtn.style.width = '100%';
        removeBtn.innerHTML = '✕';
        removeBtn.addEventListener('click', function() {
            row.remove();
            updateHeaderEmptyState();
        });

        mainControls.appendChild(labelInput);
        mainControls.appendChild(typeSelect);
        mainControls.appendChild(valueContainer);
        mainControls.appendChild(removeBtn);
        
        row.appendChild(mainControls);
        row.appendChild(choicesWrapper);

        if (headerFieldsContainer) {
            headerFieldsContainer.appendChild(row);
        }
        updateHeaderEmptyState();
    }

    if (addHeaderFieldBtn) {
        addHeaderFieldBtn.addEventListener('click', function() {
            createHeaderFieldRow();
        });
    }

    if (templateSelect) {
        templateSelect.addEventListener('change', function() {
            const templateId = this.value;
            if (!templateId) {
                return;
            }

            const template = planningTemplates.find(function(t) {
                return t.id === templateId;
            });

            if (template) {
                template.fields.forEach(function(field) {
                    createHeaderFieldRow(field.label, field.type, '', field.options);
                });
                
                const optionToDisable = templateSelect.querySelector(`option[value="${templateId}"]`);
                if (optionToDisable) {
                    optionToDisable.disabled = true;
                }
            }
            
            this.value = '';
        });
    }

    // --- 3. Table Row Management (Tasks) ---

    function updateEmptyState() {
        const table = document.getElementById('planningTable');
        if (tableBody.children.length === 0) {
            if (emptyState) {
                emptyState.style.display = 'block';
            }
            if (table) {
                table.style.display = 'none';
            }
        } else {
            if (emptyState) {
                emptyState.style.display = 'none';
            }
            if (table) {
                table.style.display = 'table';
            }
        }
    }

    function createRow(data = {}) {
        const tr = document.createElement('tr');
        
        const columns = [
            { name: 'container_number', placeholder: 'ABCD1234567', value: data.container_number || '' },
            { name: 'seal', placeholder: 'S12345', value: data.seal || '' },
            { name: 'type', placeholder: '40HC / 20GP', value: data.type || '' },
            { name: 'weight', placeholder: '0.00', type: 'number', value: data.weight || '' }
        ];

        let html = '';
        columns.forEach(function(col) {
            let inputType = 'text';
            if (col.type) {
                inputType = col.type;
            }
            html += `
                <td>
                    <input type="${inputType}" name="${col.name}" 
                           class="form-control" placeholder="${col.placeholder}" 
                           value="${col.value}" required>
                </td>
            `;
        });

        let workerOptions = '<option value="">-- Sin asignar --</option>';
        for (const [id, name] of Object.entries(usersMap)) {
            let selectedAttr = '';
            if (data.worker_id === id) {
                selectedAttr = 'selected';
            }
            workerOptions += `<option value="${id}" ${selectedAttr}>${name}</option>`;
        }

        html += `
            <td>
                <select name="worker_id" class="form-control">
                    ${workerOptions}
                </select>
            </td>
            <td class="text-center">
                <button type="button" class="btn btn-sm btn-danger remove-row-btn" style="padding: 2px 8px;">&times;</button>
            </td>
        `;

        tr.innerHTML = html;
        if (tableBody) {
            tableBody.appendChild(tr);
        }
        updateEmptyState();

        tr.querySelector('.remove-row-btn').addEventListener('click', function() {
            tr.remove();
            updateEmptyState();
        });
    }

    if (addRowBtn) {
        addRowBtn.addEventListener('click', function() {
            createRow();
        });
    }

    // --- 4. File Upload ---

    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) {
                return;
            }

            const reader = new FileReader();
            reader.onload = function(event) {
                const text = event.target.result;
                processData(text);
            };
            reader.readAsText(file);
        });
    }

    function processData(csvText) {
        const lines = csvText.split('\n');
        for (let i = 1; i < lines.length; i++) {
            const cols = lines[i].split(',');
            if (cols.length >= 4) {
                createRow({
                    container_number: cols[0].trim(),
                    seal: cols[1].trim(),
                    type: cols[2].trim(),
                    weight: cols[3].trim()
                });
            }
        }
    }

    // --- 5. Form Submission ---

    if (planningForm) {
        planningForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const rows = tableBody.querySelectorAll('tr');
            if (rows.length === 0) {
                alert('Debe agregar al menos una tarea a la planificación.');
                return;
            }

            const submitBtn = document.getElementById('submitBtn');
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Enviando...';

            const records = [];
            rows.forEach(function(row) {
                const record = {
                    container_number: row.querySelector('[name="container_number"]').value,
                    seal: row.querySelector('[name="seal"]').value,
                    type: row.querySelector('[name="type"]').value,
                    weight: row.querySelector('[name="weight"]').value,
                    worker_id: row.querySelector('[name="worker_id"]').value || null
                };
                records.push(record);
            });

            const metadataValues = {};
            if (headerFieldsContainer) {
                headerFieldsContainer.querySelectorAll('.adhoc-header-row').forEach(function(row) {
                    const label = row.querySelector('.header-label').value.trim();
                    const valueInput = row.querySelector('.header-value');
                    let val = valueInput.value;
                    
                    if (valueInput.tagName === 'SELECT') {
                        if (val === 'true') {
                            val = true;
                        } else if (val === 'false') {
                            val = false;
                        }
                    }

                    if (label) {
                        metadataValues[label] = val;
                    }
                });
            }

            const payload = {
                client_name: document.getElementById('client_name').value,
                form_id: document.getElementById('form_id').value,
                template_id: null,
                metadata_values: metadataValues,
                records: records
            };

            try {
                const response = await fetch(window.location.href, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                const result = await response.json();

                if (result.success) {
                    window.location.href = '/plannings/';
                } else {
                    alert('Error: ' + (result.error || 'No se pudo crear la planificación.'));
                    submitBtn.disabled = false;
                    submitBtn.textContent = '🚀 Crear Planificación';
                }
            } catch (error) {
                console.error('Submission error:', error);
                alert('Ocurrió un error de red o del servidor.');
                submitBtn.disabled = false;
                submitBtn.textContent = '🚀 Crear Planificación';
            }
        });
    }

    updateEmptyState();
    updateHeaderEmptyState();
});