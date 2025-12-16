/* pytarjas/static/js/tasks/create.js */

document.addEventListener('DOMContentLoaded', function() {
    let formChanged = false;
    const taskForm = document.getElementById('createTaskForm');
    const formSelect = document.getElementById('form_id');

    // Track changes
    taskForm?.addEventListener('change', function() {
      formChanged = true;
    });

    // Preview Logic
    function showFormPreview() {
      const select = document.getElementById('form_id');
      const preview = document.getElementById('formPreview');
      const selectedOption = select.options[select.selectedIndex];
      
      if (selectedOption.value) {
        const name = selectedOption.dataset.name;
        const description = selectedOption.dataset.description;
        const type = selectedOption.dataset.type;
        
        document.getElementById('previewName').textContent = name;
        document.getElementById('previewDescription').textContent = description || 'Sin descripción';
        document.getElementById('previewType').textContent = type || 'Sin tipo';
        
        preview.classList.add('visible');
      } else {
        preview.classList.remove('visible');
      }
    }
    
    // Attach change listener to the select dropdown
    if(formSelect) {
        formSelect.addEventListener('change', showFormPreview);
    }

    // Validation & Submission
    taskForm?.addEventListener('submit', function(e) {
      const formId = document.getElementById('form_id').value;
      
      if (!formId) {
        e.preventDefault();
        alert('Por favor seleccione un formulario');
        document.getElementById('form_id').focus();
        return false;
      }
      
      const submitBtn = this.querySelector('button[type="submit"]');
      if(submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = '⏳ Creando...';
      }
      
      // Allow submission without warning
      formChanged = false;
    });

    // --- HANDLE CANCEL WITH MODAL ---
    function handleCancel(e) {
      e.preventDefault();
      const targetUrl = this.href;
      
      if (formChanged) {
        showConfirm(
          'Has seleccionado opciones pero no has creado la tarea. ¿Deseas salir y descartar la selección?',
          () => {
            formChanged = false; // Bypass check
            window.location.href = targetUrl;
          },
          'Descartar Tarea',
          'Sí, salir',
          'danger'
        );
      } else {
        window.location.href = targetUrl;
      }
    }

    document.getElementById('cancelBtn')?.addEventListener('click', handleCancel);
    document.getElementById('headerBackBtn')?.addEventListener('click', handleCancel);

    // Browser native fallback
    window.addEventListener('beforeunload', function(e) {
      if (formChanged) {
        e.preventDefault();
        e.returnValue = '';
      }
    });
});