/* pytarjas/static/js/forms/create.js */

document.addEventListener('DOMContentLoaded', function() {
    let formChanged = false;
    let questionCounter = 0;
    const questionsContainer = document.getElementById('questionsContainer');
    const formElement = document.getElementById('createFormForm');

    // --- 1. GLOBAL LISTENERS & TRACKING ---
    if (formElement) {
        formElement.addEventListener('input', () => { formChanged = true; });
    }

    window.addEventListener('beforeunload', function(e) {
        if (formChanged) {
            e.preventDefault();
            e.returnValue = '';
        }
    });

    // --- 2. EVENT DELEGATION (The Core Logic) ---
    // Instead of inline onclicks, we listen to events on the container
    
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

    // --- 3. HELPER FUNCTIONS ---

    function toggleQuestionCard(headerElement) {
        const card = headerElement.closest('.question-card');
        card.classList.toggle('collapsed');
    }

    function toggleChoicesSection(selectElement, questionId) {
        const choicesContainer = document.getElementById(`choices_container_${questionId}`);
        const optionsTextarea = document.getElementById(`options_wrapper_${questionId}`);
        
        if (selectElement.value === 'select') {
            choicesContainer.style.display = 'block';
            optionsTextarea.style.display = 'none';
            const list = document.getElementById(`choices_list_${questionId}`);
            if (list.children.length === 0) addChoiceInput(questionId);
        } 
        else if (selectElement.value === 'client_select') {
            choicesContainer.style.display = 'none';
            optionsTextarea.style.display = 'none';
        }
        else {
            choicesContainer.style.display = 'none';
            optionsTextarea.style.display = 'block';
        }
    }

    function addChoiceInput(questionId, value = '') {
        const list = document.getElementById(`choices_list_${questionId}`);
        const div = document.createElement('div');
        div.className = 'choice-item';
        div.innerHTML = `
          <span style="color: var(--color-text-tertiary);">•</span>
          <input type="text" class="form-control form-control-sm choice-input" value="${value}" placeholder="Escribe una opción (ej: Opción A)" required>
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
            
            // 1. Visible number
            const numberSpan = card.querySelector('.question-number');
            if (numberSpan) numberSpan.textContent = newOrder;
            
            // 2. Hidden input
            const orderInput = card.querySelector('.question-order-input');
            if (orderInput) orderInput.value = newOrder;
            
            // 3. Dropdown
            const reorderSelect = card.querySelector('.reorder-select');
            if (reorderSelect) reorderSelect.innerHTML = populateOrderDropdown(newOrder, totalCount);
            
            // 4. Buttons
            const moveUpBtn = card.querySelector('.move-up-btn');
            const moveDownBtn = card.querySelector('.move-down-btn');
            if (moveUpBtn) moveUpBtn.disabled = (index === 0);
            if (moveDownBtn) moveDownBtn.disabled = (index === cards.length - 1);
        });
        questionCounter = totalCount;
    }

    // --- 4. ADD / DELETE LOGIC ---

    function deleteQuestion(questionId) {
        showConfirm(
            '¿Estás seguro que deseas eliminar esta pregunta? La acción es irreversible si guardas el formulario.',
            () => {
                const card = document.querySelector(`[data-question-id="${questionId}"]`);
                if (card) {
                    card.remove();
                    formChanged = true;
                    updateQuestionCount();
                    
                    if (questionsContainer.children.length === 0) {
                        document.getElementById('bottomAddButtonWrapper').style.display = 'none';
                        questionsContainer.innerHTML = `
                            <div id="noQuestionsMessage" style="text-align: center; padding: var(--space-2xl); background-color: var(--color-bg-secondary); border-radius: var(--radius-md);">
                              <div style="font-size: 3rem; margin-bottom: var(--space-md); opacity: 0.3;">❓</div>
                              <p style="color: var(--color-text-secondary); margin-bottom: var(--space-lg);">
                                Este formulario aún no tiene preguntas. Haz clic en "Agregar Pregunta" para comenzar.
                              </p>
                              <button type="button" class="btn btn-success add-q-btn">➕ Agregar Pregunta</button>
                            </div>`;
                    }
                }
            },
            'Eliminar Pregunta', 'Eliminar', 'danger'
        );
    }

    window.addNewQuestion = function() {
        questionCounter++;
        
        const noQuestionsMsg = document.getElementById('noQuestionsMessage');
        if (noQuestionsMsg) noQuestionsMsg.remove();
        
        document.getElementById('bottomAddButtonWrapper').style.display = 'block';
        
        const tempId = 'new_' + Date.now();
        const currentQuestionCount = document.querySelectorAll('.question-card').length + 1;
        
        // REMOVED onclick attributes from this HTML block
        const questionHtml = `
          <div class="question-card" data-question-id="${tempId}">
            <div class="question-header">
              <div style="display: flex; align-items: center; gap: var(--space-md); flex: 1;">
                <span class="drag-handle">☰</span>
                <div style="flex: 1;">
                  <div style="font-weight: var(--font-weight-semibold); color: var(--color-text-primary);">
                    Pregunta #<span class="question-number">${currentQuestionCount}</span>
                  </div>
                </div>
                <button type="button" class="btn btn-sm btn-ghost delete-question-btn">🗑️</button>
              </div>
            </div>
            
            <div class="question-body">
              <input type="hidden" name="question_ids[]" value="${tempId}">
              
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md);">
                <div class="form-group" style="grid-column: 1 / -1;">
                  <label class="form-label">Texto de la Pregunta <span style="color: var(--color-danger);">*</span></label>
                  <input type="text" name="question_text_${tempId}" class="form-control" required placeholder="Ej: ¿Número de contenedor?">
                </div>
                
                <div class="form-group" style="grid-column: 1 / -1;">
                  <label class="form-label">Descripción de la Pregunta (Opcional)</label>
                  <textarea name="question_description_${tempId}" class="form-control" rows="2" placeholder="Ej: Registrar el valor del sello que se encuentra en la puerta."></textarea>
                  <small class="form-help">Este texto aparecerá bajo la pregunta en el formulario de campo.</small>
                </div>

                <div class="form-group">
                  <label class="form-label">Tipo de Pregunta <span style="color: var(--color-danger);">*</span></label>
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
                    <span style="font-weight: var(--font-weight-medium);">Esta pregunta es obligatoria</span>
                  </label>
                </div>
                
                <div id="choices_container_${tempId}" class="choices-container" style="display: none; grid-column: 1 / -1;">
                  <label class="form-label">Opciones de Selección <span style="color: var(--color-danger);">*</span></label>
                  <div id="choices_list_${tempId}"></div>
                  <button type="button" class="btn btn-sm btn-secondary add-choice-btn" style="margin-top: var(--space-sm);">
                    + Agregar Opción
                  </button>
                  <small class="form-help">Agrega las opciones que podrá seleccionar el usuario.</small>
                </div>

                <div class="form-group" id="options_wrapper_${tempId}" style="grid-column: 1 / -1;">
                  <label class="form-label">Opciones Avanzadas (JSON)</label>
                  <textarea name="question_options_${tempId}" class="form-control" rows="2" placeholder='{"maxlength": 50}' style="font-family: monospace;"></textarea>
                </div>
              </div>
            </div>
          </div>
        `;
        
        questionsContainer.insertAdjacentHTML('beforeend', questionHtml);
        formChanged = true;
        
        const newCard = questionsContainer.lastElementChild;
        const select = newCard.querySelector('select[name^="question_type_"]');
        toggleChoicesSection(select, tempId);
        
        newCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        updateQuestionCount();
    };

    // --- 5. INITIALIZATION & SUBMISSION ---

    // Listener for Empty State Button (since it's dynamically replaced)
    document.addEventListener('click', function(e) {
        if(e.target.classList.contains('add-q-btn')) {
            window.addNewQuestion();
        }
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

    // Form Submission
    formElement?.addEventListener('submit', function(e) {
        const cards = document.querySelectorAll('.question-card');
        let isValid = true;

        cards.forEach(card => {
            const qId = card.getAttribute('data-question-id');
            const typeSelect = card.querySelector(`select[name="question_type_${qId}"]`);
            const optionsTextarea = card.querySelector(`textarea[name="question_options_${qId}"]`);
            
            if (typeSelect.value === 'select') {
                const choices = [];
                card.querySelectorAll('.choice-input').forEach(input => {
                    if (input.value.trim()) choices.push(input.value.trim());
                });
                
                if (choices.length === 0) {
                    alert(`La pregunta #${card.querySelector('.question-number').textContent} debe tener al menos una opción.`);
                    isValid = false;
                    card.classList.remove('collapsed');
                    return;
                }
                
                let existingOpts = {};
                try {
                   if (optionsTextarea.value.trim()) existingOpts = JSON.parse(optionsTextarea.value);
                } catch (err) {}
                
                existingOpts.choices = choices;
                optionsTextarea.value = JSON.stringify(existingOpts);
            } 
            else if (typeSelect.value === 'client_select') {
                optionsTextarea.value = '';
            }
        });

        if (!isValid) {
            e.preventDefault();
            return;
        }

        const submitBtn = this.querySelector('button[type="submit"]');
        if(submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = '💾 Creando...';
        }
        formChanged = false;
    });

    // Run Initial Count (in case of edit/clone scenarios)
    updateQuestionCount();
});