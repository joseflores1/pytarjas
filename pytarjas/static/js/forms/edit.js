/* pytarjas/static/js/forms/edit.js */

document.addEventListener('DOMContentLoaded', function() {
    let formChanged = false;
    let questionCounter = 0; // Will be initialized based on DOM
    const questionsContainer = document.getElementById('questionsContainer');
    const formElement = document.getElementById('editFormForm');

    // --- 1. GLOBAL LISTENERS ---
    if (formElement) {
        formElement.addEventListener('input', () => { formChanged = true; });
    }

    window.addEventListener('beforeunload', function(e) {
        if (formChanged) {
            e.preventDefault();
            e.returnValue = '';
        }
    });

    // --- 2. EVENT DELEGATION ---
    if (questionsContainer) {
        // CLICK Delegation
        questionsContainer.addEventListener('click', function(e) {
            const target = e.target;

            // A. Toggle Card
            if (target.closest('.question-header') && !target.closest('button')) {
                toggleQuestionCard(target.closest('.question-header'));
            }
            
            // B. Delete Question
            if (target.closest('.delete-question-btn')) {
                e.stopPropagation();
                const card = target.closest('.question-card');
                deleteQuestion(card.dataset.questionId);
            }

            // C. Move Up/Down
            if (target.closest('.move-up-btn')) {
                const card = target.closest('.question-card');
                moveQuestion(card.dataset.questionId, -1);
            }
            if (target.closest('.move-down-btn')) {
                const card = target.closest('.question-card');
                moveQuestion(card.dataset.questionId, 1);
            }

            // D. Add Choice Option
            if (target.closest('.add-choice-btn')) {
                const card = target.closest('.question-card');
                addChoiceInput(card.dataset.questionId);
            }

            // E. Remove Choice Option
            if (target.closest('.remove-choice-btn')) {
                target.closest('.choice-item').remove();
            }
        });

        // CHANGE Delegation
        questionsContainer.addEventListener('change', function(e) {
            const target = e.target;

            // F. Question Type Change
            if (target.name && target.name.startsWith('question_type_')) {
                const card = target.closest('.question-card');
                toggleChoicesSection(target, card.dataset.questionId);
            }

            // G. Reorder Select Change
            if (target.classList.contains('reorder-select')) {
                handleQuickReorder(target);
            }
        });
    }

    // --- 3. DOM MANIPULATION FUNCTIONS ---

    function toggleQuestionCard(header) {
        header.closest('.question-card').classList.toggle('collapsed');
    }

    function toggleChoicesSection(select, qId) {
        const choicesContainer = document.getElementById(`choices_container_${qId}`);
        const optionsWrapper = document.getElementById(`options_wrapper_${qId}`);
        
        if (select.value === 'select') {
            choicesContainer.classList.remove('hidden');
            optionsWrapper.classList.add('hidden');
            
            const list = document.getElementById(`choices_list_${qId}`);
            if (list.children.length === 0) addChoiceInput(qId);
        } 
        else if (select.value === 'client_select') {
            choicesContainer.classList.add('hidden');
            optionsWrapper.classList.add('hidden');
        }
        else {
            choicesContainer.classList.add('hidden');
            optionsWrapper.classList.remove('hidden');
        }
    }

    function addChoiceInput(qId, value = '') {
        const list = document.getElementById(`choices_list_${qId}`);
        const div = document.createElement('div');
        div.className = 'choice-item';
        div.innerHTML = `
          <span style="color: var(--color-text-tertiary);">•</span>
          <input type="text" class="form-control form-control-sm choice-input" value="${value}" placeholder="Opción" required>
          <button type="button" class="btn btn-sm btn-ghost text-danger remove-choice-btn" title="Eliminar opción">🗑️</button>
        `;
        list.appendChild(div);
    }

    function populateOrderDropdown(currentOrder, totalCount) {
        let options = '';
        for (let i = 1; i <= totalCount; i++) {
            options += `<option value="${i}" ${i === currentOrder ? 'selected' : ''}>#${i}</option>`;
        }
        return options;
    }

    function handleQuickReorder(selectElement) {
        const newOrder = parseInt(selectElement.value);
        const card = selectElement.closest('.question-card');
        const cards = Array.from(questionsContainer.querySelectorAll('.question-card'));
        const currentOrder = cards.indexOf(card) + 1;
        
        if (newOrder === currentOrder) return;
        
        const targetIndex = newOrder - 1;
        const targetCard = cards[targetIndex];
        
        if (newOrder > currentOrder) targetCard.after(card);
        else targetCard.before(card);

        formChanged = true;
        updateQuestionCount();
    }

    function moveQuestion(id, direction) {
        const currentCard = document.querySelector(`[data-question-id="${id}"]`);
        if (!currentCard) return;

        const cards = Array.from(questionsContainer.querySelectorAll('.question-card'));
        const currentIndex = cards.indexOf(currentCard);
        const newIndex = currentIndex + direction;

        if (newIndex < 0 || newIndex >= cards.length) return;

        const targetCard = cards[newIndex];
        if (direction === -1) questionsContainer.insertBefore(currentCard, targetCard);
        else if (direction === 1) questionsContainer.insertBefore(currentCard, targetCard.nextSibling);

        formChanged = true;
        updateQuestionCount();
    }

    function updateQuestionCount() {
        const cards = document.querySelectorAll('.question-card');
        const totalCount = cards.length;
        
        cards.forEach((card, index) => {
            const newOrder = index + 1;
            
            // Update UI number
            const numberSpan = card.querySelector('.question-number');
            if (numberSpan) numberSpan.textContent = newOrder;
            
            // Update hidden input
            const orderInput = card.querySelector('.question-order-input');
            if (orderInput) orderInput.value = newOrder;
            
            // Update Dropdown
            const reorderSelect = card.querySelector('.reorder-select');
            if (reorderSelect) reorderSelect.innerHTML = populateOrderDropdown(newOrder, totalCount);
            
            // Update buttons
            const moveUpBtn = card.querySelector('.move-up-btn');
            const moveDownBtn = card.querySelector('.move-down-btn');
            if (moveUpBtn) moveUpBtn.disabled = (index === 0);
            if (moveDownBtn) moveDownBtn.disabled = (index === cards.length - 1);
        });
        questionCounter = totalCount;
    }

    function deleteQuestion(id) {
        showConfirm(
            '¿Estás seguro que deseas eliminar esta pregunta? La acción se confirmará al guardar el formulario.',
            () => {
                const card = document.querySelector(`[data-question-id="${id}"]`);
                if (card) {
                    card.remove();
                    formChanged = true;
                    updateQuestionCount();
                    
                    if (questionsContainer.children.length === 0) {
                        const noMsg = document.getElementById('noQuestionsMessage');
                        if (noMsg) noMsg.style.display = 'block';
                        else {
                            // Re-inject empty state if completely empty
                            questionsContainer.innerHTML = `
                                <div id="noQuestionsMessage" style="text-align: center; padding: var(--space-2xl);">
                                    <p>No hay preguntas.</p>
                                </div>`;
                        }
                    }
                }
            },
            'Eliminar Pregunta', 'Eliminar', 'danger'
        );
    }

    // --- 4. EXPOSED FUNCTIONS (Add New) ---
    // Exposed to window because the "Add Question" button might be outside the container logic
    window.addNewQuestion = function() {
        questionCounter++;
        const noMsg = document.getElementById('noQuestionsMessage');
        if (noMsg) noMsg.remove(); // Remove empty state
        
        const tempId = 'new_' + Date.now();
        const currentQuestionCount = document.querySelectorAll('.question-card').length + 1;
        
        const html = `
          <div class="question-card" data-question-id="${tempId}">
            <div class="question-header">
              <div style="display: flex; align-items: center; gap: var(--space-md); flex: 1;">
                <span class="drag-handle">☰</span>
                <div style="flex: 1;">
                  <div style="font-weight: var(--font-weight-semibold); color: var(--color-text-primary);">
                    Pregunta #<span class="question-number">${currentQuestionCount}</span>
                  </div>
                  <div style="color: var(--color-text-secondary); font-size: var(--font-size-sm);">Nueva</div>
                </div>
                <button type="button" class="btn btn-sm btn-ghost delete-question-btn">🗑️</button>
              </div>
            </div>
            
            <div class="question-body">
              <input type="hidden" name="question_ids[]" value="${tempId}">
              
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md);">
                <div class="form-group" style="grid-column: 1 / -1;">
                  <label class="form-label">Texto <span style="color: var(--color-danger);">*</span></label>
                  <input type="text" name="question_text_${tempId}" class="form-control" required>
                </div>
                
                <div class="form-group" style="grid-column: 1 / -1;">
                  <label class="form-label">Descripción de la Pregunta (Opcional)</label>
                  <textarea name="question_description_${tempId}" class="form-control" rows="2" placeholder="Ej: Registrar el valor del sello que se encuentra en la puerta."></textarea>
                  <small class="form-help">Este texto aparecerá bajo la pregunta en el formulario de campo.</small>
                </div>

                <div class="form-group">
                  <label class="form-label">Tipo <span style="color: var(--color-danger);">*</span></label>
                  <select name="question_type_${tempId}" class="form-control" required>
                    <option value="text" selected>📝 Texto Corto</option>
                    <option value="textarea">📄 Texto Largo</option>
                    <option value="number">🔢 Número</option>
                    <option value="date">📅 Fecha</option>
                    <option value="datetime">🕐 Fecha y Hora</option>
                    <option value="photo">📷 Fotografía</option>
                    <option value="boolean">✓ Sí/No (Radio)</option>
                    <option value="select">📋 Selección Múltiple</option>
                    <option value="file">📁 Archivo</option>
                    <option value="client_select">🏢 Selector de Cliente</option>
                  </select>
                </div>
                
                <div class="form-group">
                  <label class="form-label">Orden</label>
                  <div style="display: flex; gap: var(--space-sm); align-items: center;">
                    <input type="hidden" name="question_order_${tempId}" class="question-order-input" value="${currentQuestionCount}" required min="1">
                    <select name="question_new_order_${tempId}" class="form-control form-control-sm reorder-select"></select>
                    <button type="button" class="btn btn-sm btn-secondary move-up-btn" title="Mover Arriba">▲</button>
                    <button type="button" class="btn btn-sm btn-secondary move-down-btn" title="Mover Abajo">▼</button>
                  </div>
                </div>
                
                <div class="form-group" style="grid-column: 1 / -1;">
                  <label style="display: flex; align-items: center; gap: var(--space-sm); cursor: pointer;">
                    <input type="checkbox" name="question_required_${tempId}" value="true" checked style="width: 20px; height: 20px;">
                    <span style="font-weight: var(--font-weight-medium);">Obligatoria</span>
                  </label>
                </div>
                
                <div id="choices_container_${tempId}" class="choices-container hidden">
                  <label class="form-label">Opciones de Selección <span style="color: var(--color-danger);">*</span></label>
                  <div id="choices_list_${tempId}"></div>
                  <button type="button" class="btn btn-sm btn-secondary add-choice-btn" style="margin-top: var(--space-sm);">
                    + Agregar Opción
                  </button>
                </div>

                <div class="form-group raw-options-wrapper" id="options_wrapper_${tempId}">
                  <label class="form-label">Opciones Avanzadas (JSON)</label>
                  <textarea name="question_options_${tempId}" class="form-control" rows="2" style="font-family: monospace;"></textarea>
                </div>
              </div>
            </div>
          </div>
        `;
        
        questionsContainer.insertAdjacentHTML('beforeend', html);
        formChanged = true;
        
        // Initialize state for new card
        const newCard = questionsContainer.lastElementChild;
        const select = newCard.querySelector('select');
        toggleChoicesSection(select, tempId);
        
        newCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        updateQuestionCount(); // Re-index
    }

    // --- 5. SUBMISSION HANDLER ---
    if (formElement) {
        formElement.addEventListener('submit', function(e) {
            const cards = document.querySelectorAll('.question-card');
            let isValid = true;

            cards.forEach(card => {
                const qId = card.dataset.questionId;
                const typeSelect = card.querySelector(`select[name="question_type_${qId}"]`);
                const optionsArea = card.querySelector(`textarea[name="question_options_${qId}"]`);
                
                if (typeSelect.value === 'select') {
                    const choices = [];
                    card.querySelectorAll('.choice-input').forEach(input => {
                        if (input.value.trim()) choices.push(input.value.trim());
                    });
                    
                    if (choices.length === 0) {
                        alert(`La pregunta #${card.querySelector('.question-number').textContent} debe tener opciones.`);
                        isValid = false;
                        card.classList.remove('collapsed');
                        return;
                    }
                    
                    let opts = {};
                    try { if (optionsArea.value.trim()) opts = JSON.parse(optionsArea.value); } catch(err) {}
                    opts.choices = choices;
                    optionsArea.value = JSON.stringify(opts);
                } 
                else if (typeSelect.value === 'client_select') {
                    optionsArea.value = '';
                }
            });

            if (!isValid) e.preventDefault();
            else {
                formChanged = false;
                const submitBtn = this.querySelector('button[type="submit"]');
                if(submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.textContent = '💾 Guardando...';
                }
            }
        });
    }

    // --- 6. INITIALIZATION & CANCEL ---
    
    // Initial Collapse & Count
    updateQuestionCount();
    document.querySelectorAll('.question-card').forEach(card => {
        card.classList.add('collapsed');
        // Ensure proper choice visibility for pre-loaded questions
        const qId = card.dataset.questionId;
        const select = card.querySelector(`select[name="question_type_${qId}"]`);
        if(select) toggleChoicesSection(select, qId);
    });

    // Handle Cancel
    function handleCancel(e) {
        e.preventDefault();
        const targetUrl = this.href;
        if (formChanged) {
            showConfirm(
                'Tienes cambios sin guardar. ¿Seguro que deseas salir?',
                () => { formChanged = false; window.location.href = targetUrl; },
                'Descartar Cambios', 'Sí, salir', 'danger'
            );
        } else {
            window.location.href = targetUrl;
        }
    }
    
    document.getElementById('cancelButton')?.addEventListener('click', handleCancel);
    document.getElementById('headerBackBtn')?.addEventListener('click', handleCancel);
});