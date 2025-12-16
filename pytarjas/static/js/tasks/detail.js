/* pytarjas/static/js/tasks/detail.js */

document.addEventListener('DOMContentLoaded', function() {
    // --- 1. INITIALIZATION & DATA EXTRACTION ---
    const formElement = document.getElementById('taskForm');
    const taskId = formElement.dataset.taskId;
    const totalQuestions = parseInt(formElement.dataset.totalQuestions);
    
    // Read state from data attributes
    let taskStatus = formElement.dataset.taskStatus;
    const canOverrideEdit = JSON.parse(formElement.dataset.canOverrideEdit);

    let hasUnsavedChanges = false;
    let saveTimeout;

    // --- 2. FILE RENDERING & HANDLING ---
    
    function renderFileItemHtml(path, questionId, qType) {
        const filename = path.split('/').pop();
        const icon = qType === 'photo' ? '📷' : '📄';
        const isImage = qType === 'photo' || path.match(/\.(jpg|jpeg|png|gif|webp)$/i);
        
        let html = `<div class="file-item-container" data-path="${path}">`;
        
        if (isImage) {
            html += `
              <div class="image-wrapper">
                  <a href="/${path}" target="_blank" title="Ver imagen en tamaño completo">
                      <img src="/${path}" alt="Foto adjunta" class="uploaded-image">
                  </a>
              </div>
            `;
        }
        
        html += `
          <div class="file-link-container">
              <span class="file-link-text">
                  <span style="font-size: var(--font-size-xl); margin-right: var(--space-sm);">${icon}</span>
                  Archivo subido: 
                  <a href="/${path}" target="_blank" title="Ver archivo">${filename}</a>
              </span>
              <button type="button" class="btn btn-sm btn-danger remove-file-btn" 
                      data-qid="${questionId}" data-path="${path}">
                  🗑️ Eliminar
              </button>
          </div>
        `;
        html += '</div>';
        return html;
    }

    function renderFileItems(questionId, paths, qType) {
        const displayBox = document.getElementById(`file-display-${questionId}`);
        if(!displayBox) return;

        displayBox.innerHTML = ''; 

        if (paths.length > 0) {
            paths.forEach(path => {
                displayBox.innerHTML += renderFileItemHtml(path, questionId, qType);
            });
            displayBox.classList.remove('hidden-by-jinja');
            
            // Re-attach listeners to new buttons
            displayBox.querySelectorAll('.remove-file-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    removeFile(this.dataset.qid, this.dataset.path);
                });
            });

        } else {
            displayBox.classList.add('hidden-by-jinja');
        }
    }
    
    window.removeFile = function(questionId, pathToRemove) {
        const pathInput = document.getElementById(`path-input-${questionId}`);
        if (!pathInput) return;
        
        try {
            let existingPaths = JSON.parse(pathInput.value || '[]');
            const newPaths = existingPaths.filter(p => p !== pathToRemove);
            
            pathInput.value = JSON.stringify(newPaths);
            
            // Determine QType from sibling uploader
            const uploader = document.getElementById(`file-upload-${questionId}`);
            const qType = uploader ? uploader.dataset.qType : 'file';
            
            renderFileItems(questionId, newPaths, qType);
            
            // Trigger change event to mark form as dirty
            pathInput.dispatchEvent(new Event('change'));

        } catch (e) {
            console.error("Error removing file:", e);
        }
    }

    // Initialize existing files on page load
    document.querySelectorAll('.file-path-input').forEach(input => {
        try {
            const qId = input.dataset.questionId; // We added this in HTML
            const uploader = document.getElementById(`file-upload-${qId}`);
            if (uploader) {
                const qType = uploader.dataset.qType;
                const paths = JSON.parse(input.value || '[]');
                if (paths.length > 0) {
                    renderFileItems(qId, paths, qType);
                }
            }
        } catch(e) { console.error("Init files error:", e); }
    });

    async function handleFileUpload(event) {
        const fileInput = event.target;
        const files = Array.from(fileInput.files);
        const questionId = fileInput.dataset.questionId;
        const qType = fileInput.dataset.qType;
        const pathInput = document.getElementById(`path-input-${questionId}`);
        
        if (files.length === 0) return;

        const indicator = document.getElementById('saveIndicator');
        const text = document.getElementById('saveIndicatorText');
        indicator.classList.add('show'); 
        indicator.classList.remove('saved'); 
        text.textContent = `Subiendo ${files.length} archivo(s)...`;
        
        let existingPaths = JSON.parse(pathInput.value || '[]');
        let allUploadsSuccessful = true;

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const formData = new FormData();
            formData.append('file', file);
            formData.append('question_id', questionId); 

            try {
                const res = await fetch(`/tasks/${taskId}/upload_file`, {
                    method: 'POST',
                    body: formData 
                });

                const data = await res.json();

                if (res.ok && data.success) {
                    existingPaths.push(data.path);
                    text.textContent = `✓ Archivo ${i + 1}/${files.length} subido...`;
                } else {
                    allUploadsSuccessful = false;
                    throw new Error(data.error || `Fallo en el servidor al subir el archivo ${file.name}.`);
                }

            } catch (e) {
                allUploadsSuccessful = false;
                console.error("File upload error:", e);
                break; 
            }
        }
        
        pathInput.value = JSON.stringify(existingPaths);
        renderFileItems(questionId, existingPaths, qType);
        
        // Trigger change for progress update
        pathInput.dispatchEvent(new Event('change'));
        fileInput.value = '';

        if (allUploadsSuccessful) {
            indicator.classList.add('saved'); 
            text.textContent = `✓ Todos los ${files.length} archivos subidos.`;
        } else {
            text.textContent = `⚠️ Subida(s) fallida(s). Revise consola.`;
        }

        setTimeout(() => indicator.classList.remove('show', 'saved'), 4000); 
    }

    // Attach listener to all file inputs
    document.querySelectorAll('input[type="file"].file-input-uploader').forEach(input => {
        if(!input.disabled) {
            input.addEventListener('change', handleFileUpload);
        }
    });


    // --- 3. PROGRESS TRACKING ---
    function updateProgress() {
        const inputs = document.querySelectorAll('.response-input');
        const answered = new Set();
        inputs.forEach(i => {
           if(i.disabled || i.readOnly) return; 

           if((i.type==='radio'||i.type==='checkbox') && i.checked) {
               answered.add(i.name);
               return;
           }
           if (i.type === 'radio' || i.type === 'checkbox') return; 
           
           if (i.classList.contains('file-path-input')) {
               try {
                   const paths = JSON.parse(i.value || '[]');
                   if (paths.length > 0) answered.add(i.name);
                   return; 
               } catch(e) { return; }
           }
           
           const trimmedValue = i.value.trim();
           if (i.type === 'number' && trimmedValue === '0') return; 
           if ((i.type === 'date' || i.type === 'datetime-local') && (trimmedValue === '0000-00-00' || !trimmedValue)) return;
           
           if (trimmedValue) answered.add(i.name);
        });
        const pct = (answered.size / totalQuestions) * 100;
        document.getElementById('progressBar').style.width = pct + '%';
        document.getElementById('progressText').textContent = `${answered.size} / ${totalQuestions}`;
    }

    // --- 4. SAVING LOGIC ---
    function collectResponses() {
        const responses = {};
        document.querySelectorAll('.response-input').forEach(input => {
            const qId = input.name.replace('response_', '');
            if(input.type==='radio') { 
                if(input.checked) responses[qId] = input.value; 
            }
            else if(input.type !== 'file') {
                responses[qId] = input.value;
            }
        });
        return responses;
    }

    async function saveTask(statusChange = null) {
        const indicator = document.getElementById('saveIndicator');
        const text = document.getElementById('saveIndicatorText');
        indicator.classList.add('show'); 
        indicator.classList.remove('saved'); 
        text.textContent = 'Guardando datos...';
        
        try {
            const payload = { responses: collectResponses() };
            if (statusChange) payload.status = statusChange;
            
            const res = await fetch(`/tasks/${taskId}/update`, {
                method: 'PATCH', 
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            
            if(res.ok) {
                indicator.classList.add('saved'); 
                text.textContent = '✓ Guardado';
                hasUnsavedChanges = false;
                
                if(statusChange) {
                    disableUnloadWarning(); 
                    window.location.reload(); 
                } else {
                     setTimeout(() => updateUiForStatusChange(taskStatus), 50);
                }
                setTimeout(() => indicator.classList.remove('show', 'saved'), 2000); 
            } else {
                const errorData = await res.json();
                throw new Error(errorData.error || 'Error saving data');
            }
        } catch(e) {
            text.textContent = `⚠️ Error: ${e.message}`;
            indicator.classList.add('show');
            indicator.classList.remove('saved');
        }
    }

    function scheduleAutoSave() {
        if (taskStatus === 'in_progress' || canOverrideEdit) {
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(() => { 
                if(hasUnsavedChanges) saveTask(); 
            }, 5000);
        }
    }

    // --- 5. UI STATE UPDATER ---
    function updateUiForStatusChange(newStatus) {
        taskStatus = newStatus;
        const statusBadge = document.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.className = `status-badge status-${newStatus}`;
            statusBadge.textContent = newStatus.replace('_', ' ');
        }

        const isFinalizedAndOverride = ['completed', 'reviewed', 'approved'].includes(newStatus) && canOverrideEdit;
        const isInProgress = newStatus === 'in_progress';
        const isPending = newStatus === 'pending';

        const toggleDisplay = (id, show) => {
            const el = document.getElementById(id);
            if(el) el.style.display = show ? 'inline-block' : 'none';
        };
        const toggleDisabled = (id, shouldDisable) => {
            const el = document.getElementById(id);
            if(!el) return;
            el.disabled = shouldDisable;
            if(shouldDisable) el.setAttribute('disabled', 'true');
            else el.removeAttribute('disabled');
        };

        // BUTTONS
        toggleDisplay('startBtn', isPending);
        toggleDisabled('startBtn', !isPending); 

        toggleDisplay('saveBtn', isInProgress);
        toggleDisabled('saveBtn', isPending && !canOverrideEdit); 

        toggleDisplay('completeBtn', isInProgress);
        toggleDisabled('completeBtn', !isInProgress); 

        if (document.getElementById('saveBtnOverride')) {
            toggleDisplay('saveBtnOverride', isFinalizedAndOverride);
            toggleDisabled('saveBtnOverride', false);
        }

        // INPUT LOCKING
        const isLocked = isPending || (['completed', 'reviewed', 'approved'].includes(newStatus) && !canOverrideEdit);
        document.querySelectorAll('.response-input, .file-input-uploader').forEach(input => {
            if (isLocked) input.setAttribute('disabled', 'true');
            else input.removeAttribute('disabled');
        });
        
        updateProgress();
    }

    // --- 6. EVENT LISTENERS ---
    
    // Change detection
    document.querySelectorAll('.response-input').forEach(input => {
        if(input.disabled || input.readOnly) return;
        if(input.type === 'file') return; // Handled by uploader

        input.addEventListener('change', () => {
            hasUnsavedChanges = true;
            updateProgress();
            scheduleAutoSave();
        });
        if(input.type!=='radio' && input.type!=='hidden') {
           input.addEventListener('input', () => { hasUnsavedChanges = true; });
        }
    });

    // Unload Warning
    function disableUnloadWarning() {
        window.removeEventListener('beforeunload', beforeUnloadHandler);
        setTimeout(() => window.addEventListener('beforeunload', beforeUnloadHandler), 500);
    }
    function beforeUnloadHandler(e) {
        if (hasUnsavedChanges && (taskStatus === 'in_progress' || canOverrideEdit)) { 
            e.preventDefault();
            e.returnValue = ''; 
        }
    }
    window.addEventListener('beforeunload', beforeUnloadHandler);

    // Button Click Handlers
    const startBtn = document.getElementById('startBtn');
    if (startBtn) startBtn.addEventListener('click', () => {
        showConfirm(
            '¿Estás seguro que deseas iniciar esta faena? El tiempo de llenado comenzará a contarse.',
            () => saveTask('in_progress'),
            'Iniciar Faena', 'Sí, iniciar', 'primary'
        );
    });

    const saveBtn = document.getElementById('saveBtn');
    if (saveBtn) saveBtn.addEventListener('click', () => saveTask());

    const saveBtnOverride = document.getElementById('saveBtnOverride');
    if (saveBtnOverride) saveBtnOverride.addEventListener('click', () => saveTask());

    document.getElementById('backBtn').addEventListener('click', function(e) {
        e.preventDefault();
        const targetUrl = this.href;
        if (hasUnsavedChanges) {
            showConfirm('Hay cambios sin guardar. ¿Seguro que deseas salir?', 
                () => { disableUnloadWarning(); window.location.href = targetUrl; }, 
                'Cambios sin guardar', 'Salir sin guardar', 'danger'
            );
        } else {
            window.location.href = targetUrl;
        }
    });

    // --- 7. VALIDATION MODAL LOGIC ---
    const validationModal = document.getElementById('validationModal');
    const missingQuestionsList = document.getElementById('missingQuestionsList');
    const completeBtn = document.getElementById('completeBtn');

    if(document.getElementById('closeValidationModalBtn')) {
        document.getElementById('closeValidationModalBtn').addEventListener('click', () => {
            validationModal.style.display = 'none';
        });
    }

    if (completeBtn) completeBtn.addEventListener('click', () => {
        const cards = document.querySelectorAll('.question-card');
        let errors = [];
        
        cards.forEach(c => c.classList.remove('error-highlight'));

        cards.forEach((card, index) => {
            let isRequired = false;
            let isAnswered = false;
            
            // 1. Radio
            const radios = card.querySelectorAll('input[type="radio"]');
            if (radios.length > 0) {
                if (radios[0].hasAttribute('required')) {
                    isRequired = true;
                    if (card.querySelector('input[type="radio"]:checked')) isAnswered = true;
                }
            } 
            // 2. Files
            else if (card.querySelector('.file-path-input')) {
                const fileInput = card.querySelector('.file-path-input');
                if (fileInput.hasAttribute('data-required')) {
                    isRequired = true;
                    try {
                        const paths = JSON.parse(fileInput.value || '[]');
                        if (paths.length > 0) isAnswered = true;
                    } catch(e) {}
                }
            }
            // 3. Standard
            else {
                const stdInput = card.querySelector('input:not([type="hidden"]), select, textarea');
                if (stdInput && stdInput.hasAttribute('required')) {
                    isRequired = true;
                    if (stdInput.value.trim() !== '') isAnswered = true;
                }
            }

            if (isRequired && !isAnswered) {
                 const textSpan = card.querySelector('.q-text-content');
                 let qText = 'Pregunta sin texto';
                 if (textSpan && textSpan.innerText.trim()) qText = textSpan.innerText.trim();
                 else {
                     // Fallback
                     const clone = card.querySelector('.question-text').cloneNode(true);
                     if(clone) {
                        clone.querySelectorAll('*').forEach(n => n.remove());
                        qText = clone.textContent.trim() || 'Pregunta #' + (index + 1);
                     }
                 }
                 errors.push({ id: card.id, text: qText, index: index + 1 });
                 card.classList.add('error-highlight');
            }
        });

        if (errors.length > 0) {
            missingQuestionsList.innerHTML = '';
            errors.forEach(err => {
                const li = document.createElement('li');
                li.innerHTML = `<span><strong>#${err.index}:</strong> ${err.text}</span> <span>➡️</span>`;
                li.onclick = () => {
                     document.getElementById(err.id).scrollIntoView({behavior: 'smooth', block: 'center'});
                     validationModal.style.display = 'none';
                };
                missingQuestionsList.appendChild(li);
            });
            validationModal.style.display = 'flex';
            return; 
        }

        if(!canOverrideEdit) { 
            const form = document.getElementById('taskForm');
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }
        }
        
        showConfirm('¿Confirmas que has completado la tarea?', () => saveTask('completed'), 'Completar Tarea', 'Sí, completar', 'success');
    });

    // Run initial UI update
    updateUiForStatusChange(taskStatus);
});