// pytarjas/static/js/auth.js
/**
 * Authentication helper for PWA
 * * This module handles authentication using the JSON API.
 * All functions are async and return promises.
 * * UPDATES: Changed login from username to email.
 */

const AUTH_API = {
  LOGIN: '/auth/login',
  LOGOUT: '/auth/logout',
  SESSION: '/auth/session'
};

/**
 * Login user with email and password
 * * @param {string} email - User's email
 * @param {string} password - User's password
 * @returns {Promise<Object>} User data if successful
 * @throws {Error} If authentication fails
 */
async function login(email, password) {
  try {
    const response = await fetch(AUTH_API.LOGIN, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      // IMPORTANT: Include credentials to maintain session cookies
      credentials: 'same-origin',
      body: JSON.stringify({
        // CHANGE: Send 'email' instead of 'username'
        email: email, 
        password: password
      })
    });

    const data = await response.json();

    if (response.ok && data.success) {
      // Login successful
      console.log('Login successful:', data.user);
      
      // Store user data in localStorage for offline access
      localStorage.setItem('user', JSON.stringify(data.user));
      
      return data.user;
    } else {
      // Login failed
      throw new Error(data.error || 'Login failed');
    }
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
}

/**
 * Logout current user
 * * @returns {Promise<boolean>} True if logout successful
 */
async function logout() {
  try {
    const response = await fetch(AUTH_API.LOGOUT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'same-origin'
    });

    const data = await response.json();

    if (response.ok && data.success) {
      // Clear local storage
      localStorage.removeItem('user');
      console.log('Logout successful');
      return true;
    } else {
      throw new Error(data.error || 'Logout failed');
    }
  } catch (error) {
    console.error('Logout error:', error);
    throw error;
  }
}

/**
 * Check if user is currently authenticated
 * * @returns {Promise<Object|null>} User data if authenticated, null otherwise
 */
async function checkSession() {
  try {
    const response = await fetch(AUTH_API.SESSION, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'same-origin'
    });

    const data = await response.json();

    if (response.ok && data.authenticated) {
      // Update localStorage with fresh user data
      localStorage.setItem('user', JSON.stringify(data.user));
      return data.user;
    } else {
      // Not authenticated
      localStorage.removeItem('user');
      return null;
    }
  } catch (error) {
    console.error('Session check error:', error);
    
    // If offline, try to get user from localStorage
    const cachedUser = localStorage.getItem('user');
    if (cachedUser) {
      console.log('Using cached user data (offline mode)');
      return JSON.parse(cachedUser);
    }
    
    return null;
  }
}

/**
 * Get currently logged in user from localStorage
 * Useful for offline mode
 * * @returns {Object|null} User data or null
 */
function getCurrentUser() {
  const userStr = localStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
}

/**
 * Check if user has specific role
 * * @param {string} role - Role to check (admin, worker, planner, client)
 * @returns {boolean} True if user has the role
 */
function hasRole(role) {
  const user = getCurrentUser();
  return user && user.role === role;
}

/**
 * Redirect to login page if not authenticated
 * Call this on page load for protected pages
 */
async function requireAuth() {
  const user = await checkSession();
  if (!user) {
    window.location.href = '/auth/login';
  }
  return user;
}

/**
 * Example: Login form handler
 * * HTML:
 * <form id="loginForm">
 * <input type="email" name="email" required>
 * <input type="password" name="password" required>
 * <button type="submit">Login</button>
 * <div id="error"></div>
 * </form>
 */
function setupLoginForm() {
  const form = document.getElementById('loginForm');
  const errorDiv = document.getElementById('error');
  
  if (!form) return;
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Clear previous errors
    errorDiv.textContent = '';
    
    // Get form data
    const formData = new FormData(form);
    // CHANGE: Get 'email' instead of 'username'
    const email = formData.get('email'); 
    const password = formData.get('password');
    
    try {
      // Show loading state
      const submitBtn = form.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Logging in...';
      
      // Attempt login
      const user = await login(email, password); // CHANGE: Pass email
      
      // Success! Redirect based on role
      if (user.role === 'admin') {
        window.location.href = '/admin';
      } else if (user.role === 'worker') {
        // NOTE: Redirection needs to be updated if the backend logic changes the target
        window.location.href = '/worker/'; 
      } else {
        window.location.href = '/';
      }
    } catch (error) {
      // Show error message
      errorDiv.textContent = error.message;
      errorDiv.style.color = 'red';
      
      // Re-enable submit button
      const submitBtn = form.querySelector('button[type="submit"]');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Login';
    }
  });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupLoginForm);
} else {
  setupLoginForm();
}

// Export functions for use in other modules
export {
  login,
  logout,
  checkSession,
  getCurrentUser,
  hasRole,
  requireAuth
};