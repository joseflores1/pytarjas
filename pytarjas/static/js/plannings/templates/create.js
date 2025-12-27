/* pytarjas/static/js/plannings/templates/create.js */

document.addEventListener('DOMContentLoaded', function () {
    const fieldsContainer = document.getElementById('fieldsContainer');
    const addFieldBtn = document.getElementById('addFieldBtn');
    const emptyFieldsState = document.getElementById('emptyFieldsState');
    const templateForm = document.getElementById('templateForm');
    const saveBtn = document.getElementById('saveTemplateBtn');

    /**
     * Shows or hides the empty state message based on the number of fields
     */
    function updateEmptyState() {
        if (fieldsContainer.children.length === 0) {
            emptyFieldsState.style.display = 'block';
        } else {
            emptyFieldsState.style.display = 'none';
        }
    }

    /**
     * Adds a new metadata field configuration card to the container
     */
    function addField() {
        const fieldDiv = document.createElement('div');
        fieldDiv.className = 'field-card';
        
        fieldDiv.innerHTML = `
            <span class="remove-field" title="Eliminar">&times;</span>
            <div class="fields-grid">
                <div class="form-group">
                    <label class="form-label">Etiqueta (Label)</label>
                    <input type="text" class="form-control field-label" placeholder="Ej: Nombre de Nave" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Nombre Interno (Key)</label>
                    <input type="text" class="form-control field-name" placeholder="Ej: vessel_name" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Tipo</label>
                    <select class="form-control field-type">
                        <option value="text">Texto</option>
                        <option value="number">Número</option>
                        <option value="date">Fecha</option>
                        <option value="boolean">Sí/No</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Requerido</label>
                    <select class="form-control field-required">
                        <option value="true">Sí</option>
                        <option value="false">No</option>
                    </select>
                </div>
            </div>
        `;

        // Removal logic
        fieldDiv.querySelector('.remove-field').addEventListener('click', function () {
            fieldDiv.remove();
            updateEmptyState();
        });

        // "Slugify" logic: automatically generate the internal key from the label
        const labelInput = fieldDiv.querySelector('.field-label');
        const nameInput = fieldDiv.querySelector('.field-name');

        labelInput.addEventListener('input', function (e) {
            if (!nameInput.dataset.manual) {
                nameInput.value = e.target.value
                    .toLowerCase()
                    .normalize("NFD")
                    .replace(/[\u0300-\u036f]/g, "") // Remove accents
                    .replace(/[^a-z0-9]/g, '_')
                    .replace(/__+/g, '_')
                    .replace(/^_|_$/g, '');
            }
        });

        // If the user manually edits the internal name, stop the auto-generation
        nameInput.addEventListener('input', function () {
            nameInput.dataset.manual = "true";
        });

        fieldsContainer.appendChild(fieldDiv);
        updateEmptyState();
    }

    // Event Listeners
    if (addFieldBtn) {
        addFieldBtn.addEventListener('click', addField);
    }

    if (templateForm) {
        templateForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const fieldCards = fieldsContainer.querySelectorAll('.field-card');

            if (fieldCards.length === 0) {
                alert('Debe agregar al menos un campo a la plantilla.');
                return;
            }

            // Change UI state
            saveBtn.disabled = true;
            saveBtn.textContent = 'Guardando...';

            const fields = Array.from(fieldCards).map(function (card) {
                return {
                    field_label: card.querySelector('.field-label').value,
                    field_name: card.querySelector('.field-name').value,
                    field_type: card.querySelector('.field-type').value,
                    is_required: card.querySelector('.field-required').value === 'true'
                };
            });

            const payload = {
                name: document.getElementById('name').value,
                description: document.getElementById('description').value,
                fields: fields
            };

            try {
                // The URL is hardcoded here to match the blueprint route
                const response = await fetch('/plannings/templates/create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                const result = await response.json();

                if (result.success) {
                    window.location.href = '/plannings/templates';
                } else {
                    alert('Error: ' + (result.error || 'No se pudo guardar la plantilla.'));
                    saveBtn.disabled = false;
                    saveBtn.textContent = '💾 Guardar Plantilla';
                }
            } catch (error) {
                console.error('Submission error:', error);
                alert('Ocurrió un error de red al intentar guardar la plantilla.');
                saveBtn.disabled = false;
                saveBtn.textContent = '💾 Guardar Plantilla';
            }
        });
    }

    // Initial check
    updateEmptyState();
});