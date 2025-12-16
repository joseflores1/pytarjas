/* pytarjas/static/js/worker/index.js */

document.addEventListener('DOMContentLoaded', function() {
    
    // --- CONNECTION STATUS ---
    const onlineIndicator = document.getElementById('online-status');
    const offlineIndicator = document.getElementById('offline-status');
    
    function updateConnectionStatus() {
        if (navigator.onLine) {
            if(onlineIndicator) onlineIndicator.style.display = 'flex';
            if(offlineIndicator) offlineIndicator.style.display = 'none';
        } else {
            if(onlineIndicator) onlineIndicator.style.display = 'none';
            if(offlineIndicator) offlineIndicator.style.display = 'flex';
        }
    }
    
    // Initial check
    updateConnectionStatus();
    
    // Listeners
    window.addEventListener('online', updateConnectionStatus);
    window.addEventListener('offline', updateConnectionStatus);
    
    // --- LAYOUT FIXES ---
    // Ensure anchor cards behave correctly
    document.querySelectorAll('.stat-card-link').forEach(link => {
        link.classList.add('card'); 
    });
});