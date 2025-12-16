/* pytarjas/static/js/users/edit.js */

document.addEventListener('DOMContentLoaded', function() {
    
    // DELETE CONFIRMATION
    // We attach the listener to the form element identified by class
    const deleteForms = document.querySelectorAll('.delete-user-form');
    
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get username from data attribute for cleaner separation
            const username = this.dataset.username || 'este usuario';
            
            showConfirm(
                `¿Está seguro que desea eliminar al usuario "${username}"?\n\nEsta acción no se puede deshacer y eliminará todos los datos asociados.`,
                () => {
                    this.submit();
                },
                'Eliminar Usuario',
                'Sí, eliminar',
                'danger'
            );
        });
    });
});