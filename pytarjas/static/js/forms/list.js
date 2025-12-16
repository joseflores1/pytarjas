/* pytarjas/static/js/forms/list.js */

document.addEventListener('DOMContentLoaded', function() {
    
    // --- 1. GLOBAL CONFIRMATION HANDLER ---
    // Note: The function needs to be exposed to the global scope 
    // because it is called via inline 'onsubmit' in the HTML.
    window.confirmDeactivate = function(e, formName) {
        e.preventDefault(); // Stop immediate submission
        const form = e.target;
        
        showConfirm(
          `¿Está seguro que desea desactivar el formulario "${formName}"?\n\nEl formulario dejará de estar disponible para nuevas tareas, pero no se eliminarán los datos históricos.`,
          () => {
            form.submit(); // Resume submission on confirm
          },
          'Desactivar Formulario',
          'Sí, desactivar',
          'danger'
        );
        
        return false;
    };
  
    // --- 2. KEYBOARD SHORTCUTS ---
    document.addEventListener('keydown', function(e) {
      // Ctrl/Cmd + N to create new form
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        // Look for the create button URL or build it
        const createBtn = document.querySelector('a[href*="/forms/create"]');
        if (createBtn) {
            window.location.href = createBtn.href;
        }
      }
    });
    
    // --- 3. HOVER EFFECTS ---
    // (CSS handles basic hover, but if JS logic is needed for complex animations, add here)
    // The previous CSS hover logic has been moved to list.css for better performance.
});