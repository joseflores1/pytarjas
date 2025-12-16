/* pytarjas/static/js/main.js */

document.addEventListener('DOMContentLoaded', function() {
    
    // --- THEME TOGGLE LOGIC ---
    // Note: Initialization happens in <head> to prevent flicker
    const html = document.documentElement;
    const themeBtn = document.getElementById('themeToggle');
    
    function setTheme(theme) {
        html.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        const icon = document.getElementById('themeIcon');
        if(icon) icon.textContent = theme === 'dark' ? '🌙' : '☀';
    }
    
    // Set initial icon based on what the <head> script set
    const currentTheme = html.getAttribute('data-theme') || 'light';
    const icon = document.getElementById('themeIcon');
    if(icon) icon.textContent = currentTheme === 'dark' ? '🌙' : '☀';

    if(themeBtn) {
        themeBtn.addEventListener('click', () => {
            const newTheme = html.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
            setTheme(newTheme);
        });
    }

    // --- NAVBAR TOGGLE ---
    const toggle = document.getElementById('navbarToggle');
    const nav = document.getElementById('navbarNav');
    if(toggle && nav) toggle.addEventListener('click', () => nav.classList.toggle('active'));

    // --- OFFLINE BANNER ---
    const banner = document.getElementById('offlineBanner');
    if(banner) {
        window.addEventListener('online', () => banner.style.display = 'none');
        window.addEventListener('offline', () => banner.style.display = 'flex');
    }
    
    // --- SERVICE WORKER ---
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => navigator.serviceWorker.register('/service-worker.js').catch(console.error));
    }
    
    // --- TOAST NOTIFICATIONS ---
    window.showToast = (msg, type='info') => {
      const box = document.getElementById('toastContainer');
      if(!box) return;
      const div = document.createElement('div');
      div.className = `toast toast-${type}`;
      div.innerText = msg;
      box.appendChild(div);
      setTimeout(() => div.remove(), 3000);
    };

    // --- GLOBAL CONFIRMATION MODAL LOGIC ---
    let confirmCallback = null;
    const modal = document.getElementById('confirmationModal');
    const confirmBtn = document.getElementById('modalConfirmBtn');

    window.showConfirm = function(message, onConfirm, title="Confirmación", confirmText="Confirmar", confirmType="primary") {
      if(!modal) return;
      
      document.getElementById('modalTitle').textContent = title;
      document.getElementById('modalMessage').textContent = message;
      
      confirmBtn.textContent = confirmText;
      confirmBtn.className = 'btn';
      
      if (confirmType === 'danger') confirmBtn.classList.add('btn-danger');
      else if (confirmType === 'success') confirmBtn.classList.add('btn-success');
      else confirmBtn.classList.add('btn-primary');
      
      confirmCallback = onConfirm;
      modal.style.display = 'flex';
    };

    window.closeModal = function() {
      if(modal) modal.style.display = 'none';
      confirmCallback = null;
    };
    
    // Expose for inline onclick handlers (e.g. close button)
    window.closeModal = window.closeModal;

    if(confirmBtn) {
        confirmBtn.addEventListener('click', function() {
            if (confirmCallback) confirmCallback();
            closeModal();
        });
    }

    // --- LOGOUT CONFIRMATION ---
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', function(e) {
        e.preventDefault();
        const url = this.href;
        
        showConfirm(
          '¿Está seguro que desea cerrar sesión?',
          () => {
            window.location.href = url;
          },
          'Cerrar Sesión',
          'Salir',
          'primary' 
        );
      });
    }
});