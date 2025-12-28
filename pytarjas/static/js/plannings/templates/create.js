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
     * Handles the dynamic UI for multiple options fields
     */
    function toggleOptionsEditor(selectElement, card) {
        const optionsContainer = card.querySelector('.options-editor-container');
        if (selectElement.value === 'select') {
            optionsContainer.style.display = 'block';
        } else {
            optionsContainer.style.display = 'none';
            optionsContainer.querySelector('.options-list').innerHTML = '';
        }
    }

    /**
     * Adds an option tag to the list
     */
    function addOptionTag(list, value) {
        const val = value.trim();
        if (!val) {
            return;
        }

        const existing = Array.from(list.querySelectorAll('.option-tag-text'))
            .map(span => span.textContent);
        
        if (existing.includes(val)) {
            return;
        }

        const tag = document.createElement('div');
        tag.className = 'option-tag';
        tag.style.display = 'inline-flex';
        tag.style.alignItems = 'center';
        tag.style.background = 'var(--color-bg-secondary)';
        tag.style.padding = 'var(--space-xs) var(--space-sm)';
        tag.style.margin = '2px';
        tag.style.borderRadius = 'var(--radius-sm)';
        tag.style.border = '1px solid var(--color-border)';

        tag.innerHTML = `
            <span class="option-tag-text" style="font-size: 0.85rem; margin-right: var(--space-xs);">${val}</span>
            <span class="remove-option" style="cursor: pointer; font-weight: bold; color: var(--color-danger);">&times;</span>
        `;

        tag.querySelector('.remove-option').addEventListener('click', function() {
            tag.remove();
        });

        list.appendChild(tag);
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
                    <input type="text" class="form-control field-label" placeholder="Ej: N° Contenedor" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Nombre Interno (Key)</label>
                    <input type="text" class="form-control field-name" placeholder="Ej: container_no" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Tipo</label>
                    <select class="form-control field-type">
                        <option value="text">Texto</option>
                        <option value="number">Número</option>
                        <option value="date">Fecha</option>
                        <option value="boolean">Sí/No</option>
                        <option value="select">Selección Múltiple</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Ubicación</label>
                    <select class="form-control field-location">
                        <option value="false">Cabecera (Información General)</option>
                        <option value="true">Fila (Registro de Tarea)</option>
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

            <div class="options-editor-container" style="display: none; margin-top: var(--space-md); border-top: 1px solid var(--color-border); padding-top: var(--space-sm);">
                <label class="form-label">Opciones disponibles</label>
                <div class="input-group" style="display: flex; gap: var(--space-xs); margin-bottom: var(--space-xs);">
                    <input type="text" class="form-control option-input" placeholder="Nueva opción...">
                    <button type="button" class="btn btn-secondary btn-sm add-option-btn">Añadir</button>
                </div>
                <div class="options-list" style="display: flex; flex-wrap: wrap; gap: var(--space-xs);"></div>
            </div>
        `;

        const typeSelect = fieldDiv.querySelector('.field-type');
        const optionInput = fieldDiv.querySelector('.option-input');
        const addOptionBtn = fieldDiv.querySelector('.add-option-btn');
        const optionsList = fieldDiv.querySelector('.options-list');

        typeSelect.addEventListener('change', function() {
            toggleOptionsEditor(this, fieldDiv);
        });

        addOptionBtn.addEventListener('click', function() {
            addOptionTag(optionsList, optionInput.value);
            optionInput.value = '';
            optionInput.focus();
        });

        optionInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addOptionBtn.click();
            }
        });

        fieldDiv.querySelector('.remove-field').addEventListener('click', function () {
            fieldDiv.remove();
            updateEmptyState();
        });

        const labelInput = fieldDiv.querySelector('.field-label');
        const nameInput = fieldDiv.querySelector('.field-name');

        labelInput.addEventListener('input', function (e) {
            if (!nameInput.dataset.manual) {
                nameInput.value = e.target.value
                    .toLowerCase()
                    .normalize("NFD")
                    .replace(/[\u0300-\u036f]/g, "")
                    .replace(/[^a-z0-9]/g, '_')
                    .replace(/__+/g, '_')
                    .replace(/^_|_$/g, '');
            }
        });

        nameInput.addEventListener('input', function () {
            nameInput.dataset.manual = "true";
        });

        fieldsContainer.appendChild(fieldDiv);
        updateEmptyState();
    }

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

            saveBtn.disabled = true;
            saveBtn.textContent = 'Guardando...';

            const fields = Array.from(fieldCards).map(function (card) {
                const type = card.querySelector('.field-type').value;
                const options = {};
                
                if (type === 'select') {
                    const optionTags = Array.from(card.querySelectorAll('.option-tag-text'))
                        .map(span => span.textContent);
                    options.choices = optionTags;
                }

                return {
                    field_label: card.querySelector('.field-label').value,
                    field_name: card.querySelector('.field-name').value,
                    field_type: type,
                    is_row_field: card.querySelector('.field-location').value === 'true',
                    is_required: card.querySelector('.field-required').value === 'true',
                    options: options
                };
            });

            const payload = {
                name: document.getElementById('name').value,
                description: document.getElementById('description').value,
                fields: fields
            };

            try {
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

    updateEmptyState();
});