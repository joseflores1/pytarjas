/* pytarjas/static/js/planner/index.js */

document.addEventListener('DOMContentLoaded', function() {
    const addRowBtn = document.getElementById('addRowBtn');
    const tableBody = document.getElementById('planningTableBody');
    const emptyState = document.getElementById('emptyState');
    const planningForm = document.getElementById('createPlanningForm');
    const fileInput = document.getElementById('fileInput');
    const templateSelect = document.getElementById('template_id');
    const dynamicMetadataSection = document.getElementById('dynamicMetadataSection');
    const templateFieldsContainer = document.getElementById('templateFieldsContainer');

    // --- 1. Data Initialization ---
    const usersMap = {};
    document.querySelectorAll('#usersMap span').forEach(span => {
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

    // --- 2. Dynamic Metadata Management ---
    function renderTemplateFields(templateId) {
        // Clear previous fields
        templateFieldsContainer.innerHTML = '';
        
        if (!templateId) {
            dynamicMetadataSection.style.display = 'none';
            return;
        }

        const template = planningTemplates.find(t => t.id === templateId);
        if (!template) {
            dynamicMetadataSection.style.display = 'none';
            return;
        }

        template.fields.forEach(field => {
            const formGroup = document.createElement('div');
            formGroup.className = 'form-group';
            
            const label = document.createElement('label');
            label.className = 'form-label';
            label.textContent = field.label;
            
            if (field.required) {
                const span = document.createElement('span');
                span.style.color = 'var(--color-danger)';
                span.textContent = ' *';
                label.appendChild(span);
            }
            formGroup.appendChild(label);

            let input;
            if (field.type === 'select') {
                input = document.createElement('select');
                input.className = 'form-control';
                
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = '-- Seleccione --';
                input.appendChild(defaultOption);

                if (field.options && field.options.choices) {
                    field.options.choices.forEach(choice => {
                        const opt = document.createElement('option');
                        opt.value = choice;
                        opt.textContent = choice;
                        input.appendChild(opt);
                    });
                }
            } else if (field.type === 'boolean') {
                input = document.createElement('select');
                input.className = 'form-control';
                
                const optNo = document.createElement('option');
                optNo.value = 'false';
                optNo.textContent = 'No';
                
                const optYes = document.createElement('option');
                optYes.value = 'true';
                optYes.textContent = 'Sí';
                
                input.appendChild(optNo);
                input.appendChild(optYes);
            } else {
                input = document.createElement('input');
                input.type = field.type === 'number' ? 'number' : 'text';
                input.className = 'form-control';
            }

            input.name = `metadata_${field.name}`;
            input.dataset.fieldName = field.name;
            if (field.required) {
                input.required = true;
            }

            formGroup.appendChild(input);
            templateFieldsContainer.appendChild(formGroup);
        });

        dynamicMetadataSection.style.display = 'block';
    }

    if (templateSelect) {
        templateSelect.addEventListener('change', (e) => {
            renderTemplateFields(e.target.value);
        });
    }

    // --- 3. Table Row Management ---
    function updateEmptyState() {
        if (tableBody.children.length === 0) {
            emptyState.style.display = 'block';
            document.getElementById('planningTable').style.display = 'none';
        } else {
            emptyState.style.display = 'none';
            document.getElementById('planningTable').style.display = 'table';
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
        columns.forEach(col => {
            html += `
                <td>
                    <input type="${col.type || 'text'}" name="${col.name}" 
                           class="form-control" placeholder="${col.placeholder}" 
                           value="${col.value}" required>
                </td>
            `;
        });

        let workerOptions = '<option value="">-- Sin asignar --</option>';
        for (const [id, name] of Object.entries(usersMap)) {
            const selected = data.worker_id === id ? 'selected' : '';
            workerOptions += `<option value="${id}" ${selected}>${name}</option>`;
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
        tableBody.appendChild(tr);
        updateEmptyState();

        tr.querySelector('.remove-row-btn').addEventListener('click', () => {
            tr.remove();
            updateEmptyState();
        });
    }

    if (addRowBtn) {
        addRowBtn.addEventListener('click', () => {
            createRow();
        });
    }

    // --- 4. File Upload & Parsing ---
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
            submitBtn.textContent = 'Enviando...';

            const records = [];
            rows.forEach(row => {
                const record = {
                    container_number: row.querySelector('[name="container_number"]').value,
                    seal: row.querySelector('[name="seal"]').value,
                    type: row.querySelector('[name="type"]').value,
                    weight: row.querySelector('[name="weight"]').value,
                    worker_id: row.querySelector('[name="worker_id"]').value || null
                };
                records.push(record);
            });

            // Gather metadata values from dynamic fields
            const metadataValues = {};
            templateFieldsContainer.querySelectorAll('[data-field-name]').forEach(input => {
                let val = input.value;
                if (input.tagName === 'SELECT' && (val === 'true' || val === 'false')) {
                    val = (val === 'true');
                }
                metadataValues[input.dataset.fieldName] = val;
            });

            const payload = {
                client_name: document.getElementById('client_name').value,
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
});