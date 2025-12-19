/* pytarjas/static/js/planner/index.js */

document.addEventListener('DOMContentLoaded', function() {
    const addRowBtn = document.getElementById('addRowBtn');
    const tableBody = document.getElementById('planningTableBody');
    const emptyState = document.getElementById('emptyState');
    const planningForm = document.getElementById('createPlanningForm');
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('drop-zone');

    // --- 1. User Data Initialization ---
    const usersMap = {};
    document.querySelectorAll('#usersMap span').forEach(span => {
        usersMap[span.dataset.id] = span.dataset.username;
    });

    // --- 2. Table Row Management ---
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
        
        // Define columns based on your maritime requirements
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

        // Worker Selection Column
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

        // Attach remove listener
        tr.querySelector('.remove-row-btn').addEventListener('click', () => {
            tr.remove();
            updateEmptyState();
        });
    }

    if (addRowBtn) {
        addRowBtn.addEventListener('click', () => createRow());
    }

    // --- 3. File Upload & Parsing (CSV/Excel) ---
    // Note: For real Excel parsing you'd need a library like SheetJS (xlsx)
    // Here we implement a basic CSV parser as a fallback or starting point
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
        // Simple logic: assume headers are Container, Seal, Type, Weight
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

    // --- 4. Form Submission ---
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

            const payload = {
                client_name: document.getElementById('client_name').value,
                form_id: document.getElementById('form_id').value,
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

    // Initial state
    updateEmptyState();
});