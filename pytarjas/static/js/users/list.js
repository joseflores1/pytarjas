/* pytarjas/static/js/users/list.js */

document.addEventListener('DOMContentLoaded', function() {
    
    // --- 1. DELETE CONFIRMATION ---
    document.querySelectorAll('.delete-user-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const username = this.dataset.username;
            
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

    // --- 2. KEYBOARD SHORTCUTS ---
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            // Find the create button by its href pattern
            const createBtn = document.querySelector('a[href*="/users/create"]');
            if (createBtn) {
                window.location.href = createBtn.href;
            }
        }
    });

    // --- 3. CURRENT USER HIGHLIGHT ---
    const currentUserBadges = document.querySelectorAll('.badge-info');
    currentUserBadges.forEach(function(badge) {
        const row = badge.closest('tr');
        if (row) {
            row.classList.add('current-user-row');
        }
    });
});