/* pytarjas/static/js/users/create.js */

document.addEventListener('DOMContentLoaded', function() {
    let formChanged = false;
    const formElement = document.getElementById('createUserForm');

    // --- 1. CHANGE TRACKING ---
    if (formElement) {
        formElement.addEventListener('input', () => { formChanged = true; });
    }

    // --- 2. CANCEL HANDLER ---
    function handleCancel(e) {
        e.preventDefault();
        const targetUrl = this.href;
        
        if (formChanged) {
            showConfirm(
                'Ha ingresado datos para el nuevo usuario. ¿Desea salir y perder estos datos?',
                () => {
                    formChanged = false; // Bypass check
                    window.location.href = targetUrl;
                },
                'Descartar Usuario',
                'Sí, salir',
                'danger'
            );
        } else {
            window.location.href = targetUrl;
        }
    }

    const cancelBtn = document.getElementById('cancelBtn');
    const headerBackBtn = document.getElementById('headerBackBtn');
    if (cancelBtn) cancelBtn.addEventListener('click', handleCancel);
    if (headerBackBtn) headerBackBtn.addEventListener('click', handleCancel);

    // Browser native fallback
    window.addEventListener('beforeunload', function(e) {
        if (formChanged) {
            e.preventDefault();
            e.returnValue = '';
        }
    });

    // --- 3. PASSWORD VISIBILITY TOGGLE ---
    const toggleButtons = document.querySelectorAll('.toggle-password-btn');
    toggleButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const fieldId = this.dataset.target;
            togglePasswordVisibility(fieldId);
        });
    });

    function togglePasswordVisibility(fieldId) {
        const field = document.getElementById(fieldId);
        const icon = document.getElementById(fieldId + '-toggle-icon');
        if (field.type === 'password') {
            field.type = 'text';
            icon.textContent = '🙈';
        } else {
            field.type = 'password';
            icon.textContent = '👁️';
        }
    }

    // --- 4. VALIDATION HELPERS ---
    function calculatePasswordStrength(password) {
        let strength = 0;
        if (password.length >= 8) strength++;
        if (password.length >= 12) strength++;
        if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
        if (/\d/.test(password)) strength++;
        if (/[^a-zA-Z\d]/.test(password)) strength++;
        return Math.min(strength, 4);
    }

    function updatePasswordStrength() {
        const passwordInput = document.getElementById('password');
        const strengthDiv = document.getElementById('password-strength');
        const strengthText = document.getElementById('strength-text');
        
        if (!passwordInput) return;
        const password = passwordInput.value;
        
        if (password.length === 0) {
            strengthDiv.style.display = 'none';
            return;
        }
        
        strengthDiv.style.display = 'block';
        const strength = calculatePasswordStrength(password);
        
        // Reset bars
        for (let i = 1; i <= 4; i++) {
            document.getElementById('strength-bar-' + i).className = 'strength-bar';
        }
        
        const levels = ['weak', 'fair', 'good', 'strong'];
        const texts = ['Débil', 'Aceptable', 'Buena', 'Fuerte'];
        const colors = ['var(--color-danger)', '#f59e0b', '#3b82f6', 'var(--color-secondary)'];
        
        for (let i = 1; i <= strength; i++) {
            document.getElementById('strength-bar-' + i).classList.add('active-' + levels[strength - 1]);
        }
        
        strengthText.textContent = 'Fortaleza: ' + texts[strength - 1];
        strengthText.style.color = colors[strength - 1];
    }

    function checkPasswordMatch() {
        const password = document.getElementById('password').value;
        const confirm = document.getElementById('password_confirm').value;
        const matchMessage = document.getElementById('password-match-message');
        
        if (confirm === '') {
            matchMessage.textContent = '';
            matchMessage.style.color = '';
            return;
        }
        
        if (password === confirm) {
            matchMessage.textContent = '✓ Las contraseñas coinciden';
            matchMessage.style.color = 'var(--color-secondary)';
        } else {
            matchMessage.textContent = '✗ Las contraseñas no coinciden';
            matchMessage.style.color = 'var(--color-danger)';
        }
    }

    function validateUsername() {
        const username = document.getElementById('username');
        const feedback = document.getElementById('username-feedback');
        const pattern = /^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s_-]+$/;
        
        if (username.value.length > 0 && !pattern.test(username.value)) {
            username.classList.add('is-invalid');
            feedback.textContent = 'Solo se permiten letras, números, espacios, guiones y guiones bajos (incluye tildes)';
            return false;
        } else if (username.value.length > 0 && username.value.length < 3) {
            username.classList.add('is-invalid');
            feedback.textContent = 'Mínimo 3 caracteres';
            return false;
        } else {
            username.classList.remove('is-invalid');
            feedback.textContent = '';
            return true;
        }
    }

    function validateEmail() {
        const email = document.getElementById('email');
        const feedback = document.getElementById('email-feedback');
        const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        
        if (email.value.length > 0 && !pattern.test(email.value)) {
            email.classList.add('is-invalid');
            feedback.textContent = 'Ingrese un correo electrónico válido';
            return false;
        } else {
            email.classList.remove('is-invalid');
            feedback.textContent = '';
            return true;
        }
    }

    // --- 5. ATTACH INPUT LISTENERS ---
    const passwordInput = document.getElementById('password');
    const confirmInput = document.getElementById('password_confirm');
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');

    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            updatePasswordStrength();
            checkPasswordMatch();
        });
    }
    if (confirmInput) confirmInput.addEventListener('input', checkPasswordMatch);
    if (usernameInput) usernameInput.addEventListener('input', validateUsername);
    if (emailInput) emailInput.addEventListener('input', validateEmail);

    // --- 6. SUBMISSION HANDLER ---
    if (formElement) {
        formElement.addEventListener('submit', function(e) {
            const username = document.getElementById('username');
            const email = document.getElementById('email');
            const password = document.getElementById('password');
            const confirm = document.getElementById('password_confirm');
            const role = document.getElementById('role');
            
            let isValid = true;
            
            if (username.value.trim() === '' || !validateUsername()) {
                username.classList.add('is-invalid');
                isValid = false;
            }
            if (email.value.trim() === '' || !validateEmail()) {
                email.classList.add('is-invalid');
                isValid = false;
            }
            if (role.value === '') {
                role.classList.add('is-invalid');
                isValid = false;
            }
            if (password.value.length < 8) {
                password.classList.add('is-invalid');
                document.getElementById('password-feedback').textContent = 'La contraseña debe tener al menos 8 caracteres';
                isValid = false;
            }
            if (password.value !== confirm.value) {
                confirm.classList.add('is-invalid');
                document.getElementById('password-confirm-feedback').textContent = 'Las contraseñas no coinciden';
                isValid = false;
            }
            
            if (!isValid) {
                e.preventDefault();
                alert('Por favor, corrija los errores en el formulario antes de continuar.');
                return false;
            }
            
            formChanged = false;
            
            const submitBtn = document.getElementById('submitBtn');
            if(submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '⏳ Creando Usuario...';
                submitBtn.classList.add('btn-loading');
            }
        });
    }
});