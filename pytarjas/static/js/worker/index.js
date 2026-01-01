/* pytarjas/static/js/worker/index.js */

document.addEventListener('DOMContentLoaded', function() {
    // --- 1. FRIENDLY DATES FORMATTING ---
    // This ensures all task dates in the worker's dashboard are readable.
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
                    // Displays as DD/MM/YYYY HH:MM
                    el.innerHTML = `<strong>📅 ${dateObj.toLocaleDateString('es-CL', options)}</strong>`;
                }
            }
        });
    }

    // --- 2. TASK FILTERING LOGIC ---
    const searchInput = document.getElementById('taskSearch');
    const statusFilter = document.getElementById('statusFilter');
    const taskCards = document.querySelectorAll('.task-card');

    function filterTasks() {
        const query = searchInput.value.toLowerCase();
        const status = statusFilter.value;

        taskCards.forEach(card => {
            const clientName = card.querySelector('.client-name').textContent.toLowerCase();
            const taskStatus = card.dataset.status;
            
            const matchesSearch = clientName.includes(query);
            const matchesStatus = (status === 'all' || taskStatus === status);

            if (matchesSearch && matchesStatus) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', filterTasks);
    }

    if (statusFilter) {
        statusFilter.addEventListener('change', filterTasks);
    }

    // Initialize formatting
    formatFriendlyDates();
});