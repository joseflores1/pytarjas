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

    // --- 2. FRIENDLY DATES ---
    function formatFriendlyDates() {
        document.querySelectorAll('.friendly-date').forEach(el => {
            const rawDate = el.textContent.trim();
            if (rawDate) {
                const dateObj = new Date(rawDate);
                if (!isNaN(dateObj.getTime())) {
                    const options = { 
                        year: 'numeric', 
                        month: '2-digit', 
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit'
                    };
                    el.innerHTML = `<strong>📅 ${dateObj.toLocaleDateString('es-CL', options)}</strong>`;
                }
            }
        });
    }
    formatFriendlyDates();

    // --- 3. VERIFICATION MODAL LOGIC ---
    const verificationModal = document.getElementById('verificationModal');
    const confirmVerificationBtn = document.getElementById('confirmVerificationBtn');
    const verificationRadios = document.querySelectorAll('.verify-radio');

    if (verificationModal) {
        verificationRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                const fieldName = this.name.replace('verify_', '');
                const correctionArea = document.getElementById(`correction_area_${fieldName}`);
                if (correctionArea) {
                    if (this.value === 'no') {
                        correctionArea.style.display = 'block';
                    } else {
                        correctionArea.style.display = 'none';
                    }
                }
            });
        });

        if (confirmVerificationBtn) {
            confirmVerificationBtn.addEventListener('click', function() {
                const items = document.querySelectorAll('.verification-item');
                let allAnswered = true;

                items.forEach(item => {
                    const radios = item.querySelectorAll('.verify-radio');
                    const isChecked = Array.from(radios).some(r => r.checked);
                    if (!isChecked) {
                        allAnswered = false;
                    }
                });

                if (allAnswered) {
                    saveTask('in_progress');
                } else {
                    alert('Por favor, responda todas las preguntas de verificación antes de continuar.');
                }
            });
        }
    }

    // --- 4. FILE RENDERING & HANDLING ---
    
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
        if (!displayBox) {
            return;
        }

        displayBox.innerHTML = ''; 

        if (paths.length > 0) {
            paths.forEach(path => {
                displayBox.innerHTML += renderFileItemHtml(path, questionId, qType);
            });
            displayBox.classList.remove('hidden-by-jinja');
            
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
        if (!pathInput) {
            return;
        }
        
        try {
            let existingPaths = JSON.parse(pathInput.value || '[]');
            const newPaths = existingPaths.filter(p => p !== pathToRemove);
            
            pathInput.value = JSON.stringify(newPaths);
            
            const uploader = document.getElementById(`file-upload-${questionId}`);
            const qType = uploader ? uploader.dataset.qType : 'file';
            
            renderFileItems(questionId, newPaths, qType);
            pathInput.dispatchEvent(new Event('change'));

        } catch (e) {
            console.error("Error removing file:", e);
        }
    }

    document.querySelectorAll('.file-path-input').forEach(input => {
        try {
            const qId = input.dataset.questionId;
            const uploader = document.getElementById(`file-upload-${qId}`);
            if (uploader) {
                const qType = uploader.dataset.qType;
                const paths = JSON.parse(input.value || '[]');
                if (paths.length > 0) {
                    renderFileItems(qId, paths, qType);
                }
            }
        } catch(e) { 
            console.error("Init files error:", e); 
        }
    });

    async function handleFileUpload(event) {
        const fileInput = event.target;
        const files = Array.from(fileInput.files);
        const questionId = fileInput.dataset.questionId;
        const qType = fileInput.dataset.qType;
        const pathInput = document.getElementById(`path-input-${questionId}`);
        
        if (files.length === 0) {
            return;
        }

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
        
        pathInput.dispatchEvent(new Event('change'));
        fileInput.value = '';

        if (allUploadsSuccessful) {
            indicator.classList.add('saved'); 
            text.textContent = `✓ Todos los ${files.length} archivos subidos.`;
        } else {
            text.textContent = `⚠️ Subida(s) fallida(s). Revise consola.`;
        }

        setTimeout(() => {
            indicator.classList.remove('show', 'saved');
        }, 4000); 
    }

    document.querySelectorAll('input[type="file"].file-input-uploader').forEach(input => {
        if (!input.disabled) {
            input.addEventListener('change', handleFileUpload);
        }
    });


    // --- 5. PROGRESS TRACKING ---
    function updateProgress() {
        const inputs = document.querySelectorAll('.response-input');
        const answered = new Set();
        inputs.forEach(i => {
           if (i.disabled || i.readOnly) {
               return;
           }

           if ((i.type === 'radio' || i.type === 'checkbox') && i.checked) {
               answered.add(i.name);
               return;
           }
           if (i.type === 'radio' || i.type === 'checkbox') {
               return;
           } 
           
           if (i.classList.contains('file-path-input')) {
               try {
                   const paths = JSON.parse(i.value || '[]');
                   if (paths.length > 0) {
                       answered.add(i.name);
                   }
                   return; 
               } catch(e) { 
                   return; 
               }
           }
           
           const trimmedValue = i.value.trim();
           if (i.type === 'number' && trimmedValue === '0') {
               return;
           } 
           if ((i.type === 'date' || i.type === 'datetime-local') && (trimmedValue === '0000-00-00' || !trimmedValue)) {
               return;
           }
           
           if (trimmedValue) {
               answered.add(i.name);
           }
        });
        const pct = (answered.size / totalQuestions) * 100;
        const progressBar = document.getElementById('progressBar');
        if (progressBar) {
            progressBar.style.width = pct + '%';
        }
        const progressText = document.getElementById('progressText');
        if (progressText) {
            progressText.textContent = `${answered.size} / ${totalQuestions}`;
        }
    }

    // --- 6. SAVING LOGIC ---
    function collectResponses() {
        const responses = {};
        document.querySelectorAll('.response-input').forEach(input => {
            const qId = input.name.replace('response_', '');
            if (input.type === 'radio') { 
                if (input.checked) {
                    responses[qId] = input.value;
                } 
            }
            else if (input.type !== 'file') {
                responses[qId] = input.value;
            }
        });
        return responses;
    }

    function collectVerifications() {
        const verifications = {};
        const items = document.querySelectorAll('.verification-item');
        items.forEach(item => {
            const radios = item.querySelectorAll('.verify-radio');
            const checkedRadio = Array.from(radios).find(r => r.checked);
            if (checkedRadio) {
                const fieldName = checkedRadio.name.replace('verify_', '');
                verifications[fieldName] = {
                    matches: (checkedRadio.value === 'yes'),
                    actual_value: document.getElementById(`actual_${fieldName}`)?.value || null
                };
            }
        });
        return verifications;
    }

    async function saveTask(statusChange = null) {
        const indicator = document.getElementById('saveIndicator');
        const text = document.getElementById('saveIndicatorText');
        indicator.classList.add('show'); 
        indicator.classList.remove('saved'); 
        text.textContent = 'Guardando datos...';
        
        try {
            const payload = { 
                responses: collectResponses(),
                verifications: collectVerifications()
            };
            if (statusChange) {
                payload.status = statusChange;
            }
            
            const res = await fetch(`/tasks/${taskId}/update`, {
                method: 'PATCH', 
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            
            if (res.ok) {
                indicator.classList.add('saved'); 
                text.textContent = '✓ Guardado';
                hasUnsavedChanges = false;
                
                if (statusChange) {
                    disableUnloadWarning(); 
                    window.location.reload(); 
                } else {
                     setTimeout(() => {
                         updateUiForStatusChange(taskStatus);
                     }, 50);
                }
                setTimeout(() => {
                    indicator.classList.remove('show', 'saved');
                }, 2000); 
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
                if (hasUnsavedChanges) {
                    saveTask();
                } 
            }, 5000);
        }
    }

    // --- 7. UI STATE UPDATER ---
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
            if (el) {
                el.style.display = show ? 'inline-block' : 'none';
            }
        };
        const toggleDisabled = (id, shouldDisable) => {
            const el = document.getElementById(id);
            if (!el) {
                return;
            }
            el.disabled = shouldDisable;
            if (shouldDisable) {
                el.setAttribute('disabled', 'true');
            }
            else {
                el.removeAttribute('disabled');
            }
        };

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

        const isLocked = isPending || (['completed', 'reviewed', 'approved'].includes(newStatus) && !canOverrideEdit);
        document.querySelectorAll('.response-input, .file-input-uploader').forEach(input => {
            if (isLocked) {
                input.setAttribute('disabled', 'true');
            }
            else {
                input.removeAttribute('disabled');
            }
        });
        
        updateProgress();
    }

    // --- 8. EVENT LISTENERS ---
    
    document.querySelectorAll('.response-input').forEach(input => {
        if (input.disabled || input.readOnly) {
            return;
        }
        if (input.type === 'file') {
            return;
        }

        input.addEventListener('change', () => {
            hasUnsavedChanges = true;
            updateProgress();
            scheduleAutoSave();
        });
        if (input.type !== 'radio' && input.type !== 'hidden') {
           input.addEventListener('input', () => { 
               hasUnsavedChanges = true; 
           });
        }
    });

    function disableUnloadWarning() {
        window.removeEventListener('beforeunload', beforeUnloadHandler);
        setTimeout(() => {
            window.addEventListener('beforeunload', beforeUnloadHandler);
        }, 500);
    }
    function beforeUnloadHandler(e) {
        if (hasUnsavedChanges && (taskStatus === 'in_progress' || canOverrideEdit)) { 
            e.preventDefault();
            e.returnValue = ''; 
        }
    }
    window.addEventListener('beforeunload', beforeUnloadHandler);

    const startBtn = document.getElementById('startBtn');
    if (startBtn) {
        startBtn.addEventListener('click', () => {
            if (verificationModal) {
                verificationModal.style.display = 'flex';
            } else {
                showConfirm(
                    '¿Estás seguro que deseas iniciar esta faena? El tiempo de llenado comenzará a contarse.',
                    () => {
                        saveTask('in_progress');
                    },
                    'Iniciar Faena', 'Sí, iniciar', 'primary'
                );
            }
        });
    }

    const saveBtn = document.getElementById('saveBtn');
    if (saveBtn) {
        saveBtn.addEventListener('click', () => {
            saveTask();
        });
    }

    const saveBtnOverride = document.getElementById('saveBtnOverride');
    if (saveBtnOverride) {
        saveBtnOverride.addEventListener('click', () => {
            saveTask();
        });
    }

    document.getElementById('backBtn').addEventListener('click', function(e) {
        e.preventDefault();
        const targetUrl = this.href;
        if (hasUnsavedChanges) {
            showConfirm('Hay cambios sin guardar. ¿Seguro que deseas salir?', 
                () => { 
                    disableUnloadWarning(); 
                    window.location.href = targetUrl; 
                }, 
                'Cambios sin guardar', 'Salir sin guardar', 'danger'
            );
        } else {
            window.location.href = targetUrl;
        }
    });

    // --- 9. VALIDATION MODAL LOGIC ---
    const validationModalBox = document.getElementById('validationModal');
    const missingQuestionsList = document.getElementById('missingQuestionsList');
    const completeBtn = document.getElementById('completeBtn');

    if (document.getElementById('closeValidationModalBtn')) {
        document.getElementById('closeValidationModalBtn').addEventListener('click', () => {
            validationModalBox.style.display = 'none';
        });
    }

    if (completeBtn) {
        completeBtn.addEventListener('click', () => {
            const cards = document.querySelectorAll('.question-card');
            let errors = [];
            
            cards.forEach(c => {
                c.classList.remove('error-highlight');
            });

            cards.forEach((card, index) => {
                let isRequired = false;
                let isAnswered = false;
                
                const radios = card.querySelectorAll('input[type="radio"]');
                if (radios.length > 0) {
                    if (radios[0].hasAttribute('required')) {
                        isRequired = true;
                        if (card.querySelector('input[type="radio"]:checked')) {
                            isAnswered = true;
                        }
                    }
                } 
                else if (card.querySelector('.file-path-input')) {
                    const fileInputPath = card.querySelector('.file-path-input');
                    if (fileInputPath.hasAttribute('data-required')) {
                        isRequired = true;
                        try {
                            const paths = JSON.parse(fileInputPath.value || '[]');
                            if (paths.length > 0) {
                                isAnswered = true;
                            }
                        } catch(e) {}
                    }
                }
                else {
                    const stdInput = card.querySelector('input:not([type="hidden"]), select, textarea');
                    if (stdInput && stdInput.hasAttribute('required')) {
                        isRequired = true;
                        if (stdInput.value.trim() !== '') {
                            isAnswered = true;
                        }
                    }
                }

                if (isRequired && !isAnswered) {
                     const textSpan = card.querySelector('.q-text-content');
                     let qText = 'Pregunta sin texto';
                     if (textSpan && textSpan.innerText.trim()) {
                         qText = textSpan.innerText.trim();
                     }
                     else {
                         const clone = card.querySelector('.question-text').cloneNode(true);
                         if (clone) {
                            clone.querySelectorAll('*').forEach(n => {
                                n.remove();
                            });
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
                         validationModalBox.style.display = 'none';
                    };
                    missingQuestionsList.appendChild(li);
                });
                validationModalBox.style.display = 'flex';
                return; 
            }

            if (!canOverrideEdit) { 
                const formToVerify = document.getElementById('taskForm');
                if (!formToVerify.checkValidity()) {
                    formToVerify.reportValidity();
                    return;
                }
            }
            
            showConfirm('¿Confirmas que has completado la tarea?', () => {
                saveTask('completed');
            }, 'Completar Tarea', 'Sí, completar', 'success');
        });
    }

    updateUiForStatusChange(taskStatus);
});