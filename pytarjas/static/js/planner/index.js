/* pytarjas/static/js/planner/index.js */

document.addEventListener('DOMContentLoaded', function () {
    const addRowBtn = document.getElementById('addRowBtn');
    const tableBody = document.getElementById('planningTableBody');
    const tableHeader = document.querySelector('#planningTable thead tr');
    const emptyState = document.getElementById('emptyState');
    const planningForm = document.getElementById('createPlanningForm');
    const fileInput = document.getElementById('fileInput');

    // Header Metadata Elements
    const templateSelect = document.getElementById('template_id');
    const addHeaderFieldBtn = document.getElementById('addHeaderFieldBtn');
    const headerFieldsContainer = document.getElementById('headerFieldsContainer');
    const emptyHeaderState = document.getElementById('emptyHeaderState');

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

    // Stores fields marked as is_row_field = true from the selected template
    let activeRowFields = [];

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

    // --- 3. Dynamic Table Header Management ---

    /**
     * Rebuilds the thead of the planning table based on activeRowFields.
     */
    function updateTableHeader() {
        if (!tableHeader) {
            return;
        }

        tableHeader.innerHTML = '';

        activeRowFields.forEach(function (field) {
            const th = document.createElement('th');
            th.textContent = field.label;
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
    }

    // --- 4. Header Metadata Management (Ad-hoc) ---

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

        const labelInput = document.createElement('input');
        labelInput.type = 'text';
        labelInput.className = 'form-control header-label';
        labelInput.placeholder = 'Ej: Sello';
        labelInput.value = initialLabel;
        labelInput.required = true;

        const typeSelect = document.createElement('select');
        typeSelect.className = 'form-control header-type';
        const types = [
            { val: 'text', label: 'Texto Corto' },
            { val: 'textarea', label: 'Texto Largo' },
            { val: 'number', label: 'Número' },
            { val: 'date', label: 'Fecha' },
            { val: 'datetime', label: 'Fecha y Hora' },
            { val: 'boolean', label: 'Booleano (Sí/No)' },
            { val: 'select', label: 'Selección Múltiple' }
        ];
        types.forEach(function (t) {
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

        function renderValueInput(type, value = '', options = {}) {
            valueContainer.innerHTML = '';
            let input;

            if (type === 'boolean') {
                input = document.createElement('select');
                input.className = 'form-control header-value';
                input.add(new Option('No', 'false'));
                input.add(new Option('Sí', 'true'));
                if (value === 'true' || value === true) {
                    input.value = 'true';
                }
            } else if (type === 'select') {
                input = document.createElement('select');
                input.className = 'form-control header-value';
                input.add(new Option('-- Seleccione --', ''));
                const choices = options.choices || [];
                choices.forEach(function (c) {
                    const opt = new Option(c, c);
                    if (c === value) {
                        opt.selected = true;
                    }
                    input.appendChild(opt);
                });
            } else if (type === 'textarea') {
                input = document.createElement('textarea');
                input.className = 'form-control header-value';
                input.rows = 1;
                input.value = value;
                input.style.minHeight = '38px';
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
        typeSelect.addEventListener('change', function () {
            renderValueInput(this.value);
        });

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-danger btn-sm';
        removeBtn.innerHTML = '✕';
        removeBtn.addEventListener('click', function () {
            row.remove();
            updateHeaderEmptyState();
        });

        mainControls.appendChild(labelInput);
        mainControls.appendChild(typeSelect);
        mainControls.appendChild(valueContainer);
        mainControls.appendChild(removeBtn);
        row.appendChild(mainControls);

        if (headerFieldsContainer) {
            headerFieldsContainer.appendChild(row);
        }
        updateHeaderEmptyState();
    }

    if (addHeaderFieldBtn) {
        addHeaderFieldBtn.addEventListener('click', function () {
            createHeaderFieldRow();
        });
    }

    if (templateSelect) {
        templateSelect.addEventListener('change', function () {
            const templateId = this.value;
            if (!templateId) {
                return;
            }

            const template = planningTemplates.find(function (t) {
                return t.id === templateId;
            });

            if (template) {
                // Determine row-level dynamic columns vs header-level metadata
                activeRowFields = template.fields.filter(function (f) {
                    return f.is_row_field === true;
                });
                const headerFields = template.fields.filter(function (f) {
                    return f.is_row_field === false;
                });

                // Update Table Header with Template Labels
                updateTableHeader();
                
                // Clear existing tasks because the schema changed
                tableBody.innerHTML = '';

                // Populate Header Fields
                headerFields.forEach(function (field) {
                    createHeaderFieldRow(field.label, field.type, '', field.options);
                });
            }

            this.value = '';
            updateEmptyState();
        });
    }

    // --- 5. Table Row Management (Tasks) ---

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

    /**
     * Creates a new task row where columns are mapped to activeRowFields.
     */
    function createRow(data = {}) {
        const tr = document.createElement('tr');

        activeRowFields.forEach(function (field) {
            const td = document.createElement('td');
            let input;

            if (field.type === 'select') {
                input = document.createElement('select');
                input.className = 'form-control';
                input.name = field.name;
                input.add(new Option('--', ''));
                const choices = field.options.choices || [];
                choices.forEach(function (c) {
                    const opt = new Option(c, c);
                    if (c === data[field.name]) {
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
                if (data[field.name] === 'true' || data[field.name] === true) {
                    input.value = 'true';
                }
            } else {
                input = document.createElement('input');
                input.className = 'form-control';
                input.name = field.name;
                input.value = data[field.name] || '';
                if (field.type === 'number') {
                    input.type = 'number';
                } else if (field.type === 'date') {
                    input.type = 'date';
                } else {
                    input.type = 'text';
                }
                input.placeholder = field.label;
            }

            if (field.required) {
                input.required = true;
            }
            td.appendChild(input);
            tr.appendChild(td);
        });

        // Worker column
        const workerTd = document.createElement('td');
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

        // Actions column
        const actionTd = document.createElement('td');
        actionTd.className = 'text-center';
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
            if (activeRowFields.length === 0) {
                alert('Debe seleccionar una plantilla para habilitar los registros de tareas.');
                return;
            }
            createRow();
        });
    }

    // --- 6. CSV Processing ---

    if (fileInput) {
        fileInput.addEventListener('change', function (e) {
            const file = e.target.files[0];
            if (!file) {
                return;
            }
            if (activeRowFields.length === 0) {
                alert('Debe seleccionar una plantilla antes de cargar un archivo.');
                e.target.value = '';
                return;
            }

            const reader = new FileReader();
            reader.onload = function (event) {
                const text = event.target.result;
                processData(text);
            };
            reader.readAsText(file);
        });
    }

    function processData(csvText) {
        const lines = csvText.split('\n');
        // Assumes first line is header and column order matches template order
        for (let i = 1; i < lines.length; i++) {
            const cols = lines[i].split(',');
            if (cols.length >= activeRowFields.length) {
                const rowData = {};
                activeRowFields.forEach(function (field, index) {
                    rowData[field.name] = cols[index].trim();
                });
                createRow(rowData);
            }
        }
    }

    // --- 7. Form Submission ---

    if (planningForm) {
        planningForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const rows = tableBody.querySelectorAll('tr');
            if (rows.length === 0) {
                alert('Debe agregar al menos una tarea.');
                return;
            }

            const submitBtn = document.getElementById('submitBtn');
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Enviando...';

            const records = [];
            rows.forEach(function (tr) {
                const task = {};
                activeRowFields.forEach(function (field) {
                    const input = tr.querySelector(`[name="${field.name}"]`);
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
            headerFieldsContainer.querySelectorAll('.adhoc-header-row').forEach(function (row) {
                const label = row.querySelector('.header-label').value.trim();
                const type = row.querySelector('.header-type').value;
                let val = row.querySelector('.header-value').value;
                if (type === 'boolean') {
                    val = (val === 'true');
                }
                if (label) {
                    metadataValues[label] = val;
                }
            });

            const payload = {
                client_name: clientInput.value,
                form_id: document.getElementById('form_id').value,
                template_id: document.getElementById('template_id').value || null,
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
                    alert('Error: ' + (result.error || 'Fallo al guardar.'));
                    submitBtn.disabled = false;
                    submitBtn.textContent = '🚀 Crear Planificación';
                }
            } catch (error) {
                console.error('Submit Error:', error);
                alert('Ocurrió un error de red.');
                submitBtn.disabled = false;
                submitBtn.textContent = '🚀 Crear Planificación';
            }
        });
    }

    updateEmptyState();
    updateHeaderEmptyState();
});