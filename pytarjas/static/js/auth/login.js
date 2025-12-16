/* pytarjas/static/js/auth/login.js */

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const submitBtn = document.getElementById('submitBtn');
    const submitText = document.getElementById('submitText');
    const emailInput = document.getElementById('email'); 
    const passwordInput = document.getElementById('password');

    // ===== 1. FORM SUBMISSION HANDLING =====
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            // Add loading state to button
            submitBtn.classList.add('btn-loading');
            submitBtn.disabled = true;
            submitText.textContent = 'Iniciando sesión...';
        });
    }
    
    // ===== 2. OFFLINE LOGIN WARNING =====
    function updateOnlineStatus() {
        if (navigator.onLine) {
            submitBtn.disabled = false;
            submitBtn.classList.remove('btn-secondary');
            submitBtn.classList.add('btn-primary');
            submitText.textContent = 'Iniciar Sesión';
            if(window.showToast) window.showToast('Conexión restaurada.', 'success');
        } else {
            // Show warning if offline
            if(window.showToast) {
                window.showToast(
                    'Sin conexión a internet. No puede iniciar sesión.', 
                    'warning',
                    5000
                );
            }
            // Disable form
            submitBtn.disabled = true;
            submitBtn.classList.add('btn-secondary');
            submitBtn.classList.remove('btn-primary');
            submitText.textContent = 'Sin conexión';
        }
    }

    // Check on load
    if (!navigator.onLine) updateOnlineStatus();

    // Listen for events
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    
    // ===== 3. VALIDATION ENHANCEMENT =====
    if (emailInput) {
        emailInput.addEventListener('blur', function() {
            if (this.value.trim() === '' || !this.checkValidity()) {
                this.classList.add('is-invalid');
            } else {
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            }
        });

        // Press Enter in email field to focus password
        emailInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                passwordInput.focus();
            }
        });
    }
    
    if (passwordInput) {
        passwordInput.addEventListener('blur', function() {
            if (this.value.trim() === '') {
                this.classList.add('is-invalid');
            } else {
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            }
        });
    }
    
    // ===== 4. PWA INSTALL PROMPT =====
    let deferredPrompt;
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        console.log('PWA install prompt available');
    });
    
    // ===== 5. SESSION CHECK =====
    fetch('/auth/session')
        .then(response => response.json())
        .then(data => {
            if (data.authenticated) {
                const role = data.user.role;
                const redirects = {
                    'admin': '/admin/',
                    'worker': '/worker/',
                    'planner': '/planner/',
                    'client': '/client/'
                };
                if (redirects[role]) {
                    window.location.href = redirects[role];
                }
            }
        })
        .catch(error => console.log('Not logged in'));
});