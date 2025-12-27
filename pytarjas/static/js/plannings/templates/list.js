/* pytarjas/static/js/plannings/templates_list.js */

document.addEventListener('DOMContentLoaded', function() {
    const deleteForms = document.querySelectorAll('.delete-template-form');

    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const confirmed = confirm('¿Está seguro de que desea eliminar esta plantilla? Esta acción no se puede deshacer y fallará si la plantilla está siendo usada por planificaciones activas.');
            
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });
});