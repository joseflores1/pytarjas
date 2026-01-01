/* pytarjas/static/js/planner/index.js */

document.addEventListener('DOMContentLoaded', function () {
    const addRowBtn = document.getElementById('addRowBtn');
    const tableBody = document.getElementById('planningTableBody');
    const tableHeader = document.querySelector('#planningTableHeader');
    const emptyState = document.getElementById('emptyState');
    const planningForm = document.getElementById('createPlanningForm');
    const fileInput = document.getElementById('fileInput');

    // Header Metadata Elements
    const headerTemplateSelect = document.getElementById('template_id_header');
    const addHeaderFieldBtn = document.getElementById('addHeaderFieldBtn');
    const headerFieldsContainer = document.getElementById('headerFieldsContainer');
    const emptyHeaderState = document.getElementById('emptyHeaderState');

    // Row Fields (Columns) Elements
    const tasksTemplateSelect = document.getElementById('template_id_tasks');
    const addRowFieldBtn = document.getElementById('addRowFieldBtn');
    const rowFieldsContainer = document.getElementById('rowFieldsContainer');
    const emptyRowFieldsState = document.getElementById('emptyRowFieldsState');

    // Client Autocomplete Elements
    const clientInput = document.getElementById('client_name');
    const clientResults = document.getElementById('client_results');
    const clientList = document.getElementById('client_list');
    const toggleClientBtn = document.getElementById('toggleClientDropdown');

    // --- 1. Data Initialization ---
    const usersMap = {};
    const userSpans = document.querySelectorAll('#usersMap span');
    userSpans.forEach(function (span) {
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

    // --- 2. Client Autocomplete & Toggle Logic ---
    if (clientInput && clientResults && clientList) {
        const clientItems = clientList.querySelectorAll('.autocomplete-item');

        const filterClients = function () {
            const query = clientInput.value.toLowerCase().trim();
            let hasMatches = false;

            if (query.length > 0) {
                clientItems.forEach(function (item) {
                    const text = item.textContent.toLowerCase();
                    if (text.includes(query)) {
                        item.style.display = 'block';
                        hasMatches = true;
                    } else {
                        item.style.display = 'none';
                    }
                });
                clientResults.style.display = hasMatches ? 'block' : 'none';
            } else {
                clientResults.style.display = 'none';
            }
        };

        clientInput.addEventListener('input', filterClients);

        if (toggleClientBtn) {
            toggleClientBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                const isHidden = clientResults.style.display === 'none' || !clientResults.style.display;
                if (isHidden) {
                    clientItems.forEach(function (item) {
                        item.style.display = 'block';
                    });
                    clientResults.style.display = 'block';
                } else {
                    clientResults.style.display = 'none';
                }
            });
        }

        clientList.addEventListener('click', function (e) {
            const item = e.target.closest('.autocomplete-item');
            if (item) {
                clientInput.value = item.dataset.value;
                clientResults.style.display = 'none';
            }
        });

        document.addEventListener('click', function (e) {
            if (!clientInput.contains(e.target) && !clientResults.contains(e.target) && (!toggleClientBtn || !toggleClientBtn.contains(e.target))) {
                clientResults.style.display = 'none';
            }
        });
    }

    // --- 3. Dynamic Column Logic ---

    function getActiveRowFields() {
        const fields = [];
        rowFieldsContainer.querySelectorAll('.adhoc-row-field-setup').forEach(row => {
            const labelInput = row.querySelector('.row-field-label');
            const label = labelInput.value.trim();
            const type = row.querySelector('.row-field-type').value;
            const isVerifiable = row.querySelector('.row-field-verify').checked;
            
            let options = {};
            if (row.dataset.options) {
                try {
                    options = JSON.parse(row.dataset.options);
                } catch (e) {
                    options = {};
                }
            }

            if (label) {
                fields.push({
                    label: label,
                    name: label.toLowerCase().replace(/\s+/g, '_'),
                    type: type,
                    id: row.dataset.fieldId,
                    isVerifiable: isVerifiable,
                    options: options
                });
            }
        });
        return fields;
    }

    function syncTableWithColumns() {
        if (!tableHeader) {
            return;
        }

        const fields = getActiveRowFields();
        
        tableHeader.innerHTML = '';
        fields.forEach(field => {
            const th = document.createElement('th');
            th.textContent = field.label;
            th.dataset.columnId = field.id;
            th.style.minWidth = '140px';
            tableHeader.appendChild(th);
        });

        const workerTh = document.createElement('th');
        workerTh.textContent = 'Asignado a';
        workerTh.style.minWidth = '180px';
        tableHeader.appendChild(workerTh);

        const actionsTh = document.createElement('th');
        actionsTh.style.width = '50px';
        tableHeader.appendChild(actionsTh);

        const rows = tableBody.querySelectorAll('tr');
        rows.forEach(tr => {
            const existingCells = Array.from(tr.querySelectorAll('td.dynamic-cell'));
            const workerCell = tr.querySelector('td.worker-cell');

            existingCells.forEach(cell => {
                const stillExists = fields.some(f => f.id === cell.dataset.columnId);
                if (!stillExists) {
                    cell.remove();
                }
            });

            fields.forEach(field => {
                let cell = tr.querySelector(`td[data-column-id="${field.id}"]`);
                if (!cell) {
                    cell = document.createElement('td');
                    cell.className = 'dynamic-cell';
                    cell.dataset.columnId = field.id;
                    const input = createInputForField(field);
                    cell.appendChild(input);
                } else {
                    const input = cell.querySelector('.form-control');
                    if (input) {
                        input.name = field.name;
                    }
                }
                tr.insertBefore(cell, workerCell);
            });
        });
        
        updateEmptyState();
    }

    function createInputForField(field, value = '') {
        let input;
        if (field.type === 'select') {
            input = document.createElement('select');
            input.className = 'form-control';
            input.name = field.name;
            input.add(new Option('-- Seleccione --', ''));
            
            const choices = field.options?.choices || [];
            choices.forEach(c => {
                const opt = new Option(c, c);
                if (c === value) {
                    opt.selected = true;
                }
                input.appendChild(opt);
            });
        } else if (field.type === 'boolean') {
            input = document.createElement('select');
            input.className = 'form-control';
            input.name = field.name;
            input.add(new Option('No', 'false'));
            input.add(new Option('Sí', 'true'));
            if (value === 'true' || value === true) {
                input.value = 'true';
            }
        } else {
            input = document.createElement('input');
            input.className = 'form-control';
            input.name = field.name;
            input.value = value;
            if (field.type === 'number') {
                input.type = 'number';
            } else if (field.type === 'date') {
                input.type = 'date';
            } else if (field.type === 'datetime') {
                input.type = 'datetime-local';
            } else {
                input.type = 'text';
            }
            input.placeholder = field.label;
        }
        input.required = true;
        return input;
    }

    // --- 4. Setup Row Creator ---

    function createFieldSetupRow(container, isHeaderField = true, initialLabel = '', initialType = 'text', initialValue = '', initialOptions = {}, initialVerify = false) {
        const row = document.createElement('div');
        row.className = isHeaderField ? 'adhoc-header-row' : 'adhoc-row-field-setup';
        row.dataset.fieldId = 'field_' + Math.random().toString(36).substr(2, 9);
        row.dataset.options = JSON.stringify(initialOptions || {});
        
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
        mainControls.style.gridTemplateColumns = isHeaderField ? '1.5fr 1.2fr 2fr 100px 40px' : '1.5fr 1.2fr 100px 40px';
        mainControls.style.gap = 'var(--space-sm)';
        mainControls.style.alignItems = 'center';

        const labelInput = document.createElement('input');
        labelInput.type = 'text';
        labelInput.className = isHeaderField ? 'form-control header-label' : 'form-control row-field-label';
        labelInput.placeholder = isHeaderField ? 'Ej: Sello' : 'Ej: Cubicaje';
        labelInput.value = initialLabel;
        labelInput.required = true;
        
        if (!isHeaderField) {
            labelInput.addEventListener('input', function() {
                syncTableWithColumns();
            });
        }

        const typeSelect = document.createElement('select');
        typeSelect.className = isHeaderField ? 'form-control header-type' : 'form-control row-field-type';
        const types = [
            { val: 'text', label: 'Texto Corto' },
            { val: 'textarea', label: 'Texto Largo' },
            { val: 'number', label: 'Número' },
            { val: 'date', label: 'Fecha' },
            { val: 'datetime', label: 'Fecha y Hora' },
            { val: 'boolean', label: 'Booleano (Sí/No)' },
            { val: 'select', label: 'Selección Múltiple' }
        ];
        types.forEach(t => {
            const opt = new Option(t.label, t.val);
            if (t.val === initialType) {
                opt.selected = true;
            }
            typeSelect.appendChild(opt);
        });

        if (!isHeaderField) {
            typeSelect.addEventListener('change', function() {
                syncTableWithColumns();
            });
        }

        // Verification Toggle
        const verifyContainer = document.createElement('div');
        verifyContainer.style.display = 'flex';
        verifyContainer.style.alignItems = 'center';
        verifyContainer.style.gap = '5px';
        verifyContainer.style.fontSize = '0.8rem';
        
        const verifyCheck = document.createElement('input');
        verifyCheck.type = 'checkbox';
        verifyCheck.className = isHeaderField ? 'header-field-verify' : 'row-field-verify';
        verifyCheck.checked = initialVerify;
        
        const verifyLabel = document.createElement('label');
        verifyLabel.textContent = 'Verificable';
        
        verifyContainer.appendChild(verifyCheck);
        verifyContainer.appendChild(verifyLabel);

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-danger btn-sm';
        removeBtn.innerHTML = '✕';
        removeBtn.addEventListener('click', function () {
            row.remove();
            if (isHeaderField) {
                updateHeaderEmptyState();
            } else {
                updateRowFieldsEmptyState();
                syncTableWithColumns();
            }
        });

        mainControls.appendChild(labelInput);
        mainControls.appendChild(typeSelect);

        if (isHeaderField) {
            const valueContainer = document.createElement('div');
            valueContainer.className = 'header-value-container';

            function renderValueInput(type, value = '', options = {}) {
                valueContainer.innerHTML = '';
                const input = createInputForField({ type: type, options: options, label: 'Valor' }, value);
                input.className = 'form-control header-value';
                valueContainer.appendChild(input);
            }

            renderValueInput(initialType, initialValue, initialOptions);
            typeSelect.addEventListener('change', function () {
                renderValueInput(this.value);
            });
            mainControls.appendChild(valueContainer);
        }

        mainControls.appendChild(verifyContainer);
        mainControls.appendChild(removeBtn);
        row.appendChild(mainControls);
        container.appendChild(row);

        if (isHeaderField) {
            updateHeaderEmptyState();
        } else {
            updateRowFieldsEmptyState();
            syncTableWithColumns();
        }
    }

    // --- 5. Empty State Handlers ---

    function updateHeaderEmptyState() {
        if (!headerFieldsContainer) {
            return;
        }
        const rows = headerFieldsContainer.querySelectorAll('.adhoc-header-row');
        if (emptyHeaderState) {
            emptyHeaderState.style.display = (rows.length === 0) ? 'block' : 'none';
        }
    }

    function updateRowFieldsEmptyState() {
        if (!rowFieldsContainer) {
            return;
        }
        const rows = rowFieldsContainer.querySelectorAll('.adhoc-row-field-setup');
        if (emptyRowFieldsState) {
            emptyRowFieldsState.style.display = (rows.length === 0) ? 'block' : 'none';
        }
    }

    function updateEmptyState() {
        const table = document.getElementById('planningTable');
        const hasRows = tableBody.children.length > 0;
        if (emptyState) {
            emptyState.style.display = hasRows ? 'none' : 'block';
        }
        if (table) {
            table.style.display = hasRows ? 'table' : 'none';
        }
    }

    // --- 6. Interaction Listeners ---

    if (addHeaderFieldBtn) {
        addHeaderFieldBtn.addEventListener('click', function() {
            createFieldSetupRow(headerFieldsContainer, true);
        });
    }

    if (addRowFieldBtn) {
        addRowFieldBtn.addEventListener('click', function() {
            createFieldSetupRow(rowFieldsContainer, false);
        });
    }

    if (headerTemplateSelect) {
        headerTemplateSelect.addEventListener('change', function () {
            const templateId = this.value;
            if (!templateId) {
                return;
            }
            const template = planningTemplates.find(t => t.id === templateId);
            if (template) {
                template.fields.filter(f => !f.is_row_field).forEach(f => {
                    createFieldSetupRow(headerFieldsContainer, true, f.label, f.type, '', f.options, f.is_verifiable);
                });
            }
            this.value = '';
        });
    }

    if (tasksTemplateSelect) {
        tasksTemplateSelect.addEventListener('change', function () {
            const templateId = this.value;
            if (!templateId) {
                return;
            }
            const template = planningTemplates.find(t => t.id === templateId);
            if (template) {
                template.fields.filter(f => f.is_row_field).forEach(f => {
                    createFieldSetupRow(rowFieldsContainer, false, f.label, f.type, '', f.options, f.is_verifiable);
                });
            }
            this.value = '';
        });
    }

    // --- 7. Task Table Row Management ---

    function createRow(data = {}) {
        const tr = document.createElement('tr');
        const fields = getActiveRowFields();

        fields.forEach(field => {
            const td = document.createElement('td');
            td.className = 'dynamic-cell';
            td.dataset.columnId = field.id;
            const input = createInputForField(field, data[field.name]);
            td.appendChild(input);
            tr.appendChild(td);
        });

        const workerTd = document.createElement('td');
        workerTd.className = 'worker-cell';
        const workerSelect = document.createElement('select');
        workerSelect.className = 'form-control';
        workerSelect.name = 'worker_id';
        workerSelect.add(new Option('-- Sin asignar --', ''));
        for (const [id, name] of Object.entries(usersMap)) {
            const opt = new Option(name, id);
            if (data.worker_id === id) {
                opt.selected = true;
            }
            workerSelect.appendChild(opt);
        }
        workerTd.appendChild(workerSelect);
        tr.appendChild(workerTd);

        const actionTd = document.createElement('td');
        actionTd.className = 'text-center action-cell';
        const remBtn = document.createElement('button');
        remBtn.type = 'button';
        remBtn.className = 'btn btn-sm btn-danger remove-row-btn';
        remBtn.innerHTML = '&times;';
        remBtn.addEventListener('click', function () {
            tr.remove();
            updateEmptyState();
        });
        actionTd.appendChild(remBtn);
        tr.appendChild(actionTd);

        tableBody.appendChild(tr);
        updateEmptyState();
    }

    if (addRowBtn) {
        addRowBtn.addEventListener('click', function () {
            if (getActiveRowFields().length === 0) {
                alert('Debe definir al menos una columna de tarea.');
                return;
            }
            createRow();
        });
    }

    // --- 8. Form Submission ---

    if (planningForm) {
        planningForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const fields = getActiveRowFields();
            const rows = tableBody.querySelectorAll('tr');

            if (rows.length === 0) {
                alert('Debe agregar al menos una tarea.');
                return;
            }

            const submitBtn = document.getElementById('submitBtn');
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Enviando...';

            const records = [];
            rows.forEach(tr => {
                const task = {};
                fields.forEach(field => {
                    const cell = tr.querySelector(`td[data-column-id="${field.id}"]`);
                    const input = cell.querySelector('.form-control');
                    let val = input.value;
                    if (field.type === 'boolean') {
                        val = (val === 'true');
                    }
                    task[field.name] = val;
                });
                task.worker_id = tr.querySelector('[name="worker_id"]').value || null;
                records.push(task);
            });

            const metadataValues = {};
            const verificationConfig = {};

            // Collect Header Verifications
            headerFieldsContainer.querySelectorAll('.adhoc-header-row').forEach(row => {
                const label = row.querySelector('.header-label').value.trim();
                const type = row.querySelector('.header-type').value;
                const isVerify = row.querySelector('.header-field-verify').checked;
                const fieldName = label.toLowerCase().replace(/\s+/g, '_');
                
                let val = row.querySelector('.header-value').value;
                if (type === 'boolean') {
                    val = (val === 'true');
                }
                
                if (label) {
                    metadataValues[label] = val;
                    if (isVerify) {
                        verificationConfig[fieldName] = {
                            label: label,
                            is_row_field: false
                        };
                    }
                }
            });

            // Collect Row Verifications
            fields.forEach(f => {
                if (f.isVerifiable) {
                    verificationConfig[f.name] = {
                        label: f.label,
                        is_row_field: true
                    };
                }
            });

            const payload = {
                client_name: clientInput.value,
                form_id: document.getElementById('form_id').value,
                template_id: null,
                metadata_values: metadataValues,
                verification_config: verificationConfig,
                records: records
            };

            try {
                const response = await fetch(window.location.href, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await response.json();
                if (result.success) {
                    window.location.href = '/plannings/';
                } else {
                    alert('Error: ' + (result.error || 'Fallo al guardar.'));
                    submitBtn.disabled = false;
                    submitBtn.textContent = '🚀 Crear Planificación';
                }
            } catch (error) {
                alert('Ocurrió un error de red.');
                submitBtn.disabled = false;
                submitBtn.textContent = '🚀 Crear Planificación';
            }
        });
    }

    updateEmptyState();
    updateHeaderEmptyState();
    updateRowFieldsEmptyState();
    syncTableWithColumns();
});