/**
 * YouTube Chapter Generator Authentication Module
 *
 * This module handles user authentication using Google OAuth.
 */

// Initialize auth when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  // Wait for the store and API to be initialized
  if (window.YCG_STORE && window.YCG_API) {
    initAuth();
  } else {
    console.error("[Auth] Failed to initialize auth: YCG_STORE or YCG_API not available");
  }
});

/**
 * Initialize authentication
 */
async function initAuth() {
  console.log("[Auth] Initializing auth...");

  // Get references to the store and API
  const store = window.YCG_STORE;
  const api = window.YCG_API;

  // Load state from storage
  await store.loadFromStorage();

  // Check if we have a token and verify it
  const state = store.getState();
  if (state.auth.token) {
    console.log("[Auth] Found token in storage, verifying...");

    try {
      // Verify token with server
      const result = await api.verifyToken(state.auth.token);

      if (result.valid) {
        console.log("[Auth] Token is valid");

        // Get user info
        try {
          const userInfo = await api.getUserInfo();

          // Update user in store
          store.dispatch('auth', {
            type: 'LOGIN_SUCCESS',
            payload: {
              user: userInfo,
              token: state.auth.token
            }
          });

          // Update credits
          store.dispatch('credits', {
            type: 'SET_CREDITS',
            payload: {
              count: userInfo.credits || 0
            }
          });

          // Set active view to main
          store.dispatch('ui', {
            type: 'SET_ACTIVE_VIEW',
            payload: { view: 'main' }
          });

          // Save state to storage
          await store.saveToStorage();
        } catch (error) {
          console.error("[Auth] Error getting user info:", error);
          handleAuthError(store, error);
        }
      } else {
        console.log("[Auth] Token is invalid");
        handleAuthError(store, new Error("Invalid token"));
      }
    } catch (error) {
      console.error("[Auth] Error verifying token:", error);
      handleAuthError(store, error);
    }
  } else {
    console.log("[Auth] No token found in storage");

    // Initialize Google Sign-In
    initGoogleSignIn();
  }

  // Set up event listeners
  setupAuthEventListeners();

  console.log("[Auth] Initialization complete");
}

/**
 * Initialize Google Sign-In
 */
function initGoogleSignIn() {
  console.log("[Auth] Initializing Google Sign-In...");

  // Create Google Sign-In buttons
  const createGoogleButton = () => {
    const button = document.createElement('button');
    button.type = 'button';
    button.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" style="margin-right: 8px;">
        <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z"/>
        <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/>
        <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/>
        <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"/>
      </svg>
      Sign in with Google
    `;
    button.className = 'btn google-signin-btn-dynamic';
    button.style.width = 'auto';
    button.style.margin = '10px auto';
    button.addEventListener('click', handleGoogleSignIn);
    return button;
  };

  // Add buttons to the DOM
  const googleSignInButton1 = document.getElementById('google-signin-button');
  const googleSignInButton2 = document.getElementById('google-signin-button-auth');

  if (googleSignInButton1) {
    googleSignInButton1.innerHTML = '';
    googleSignInButton1.appendChild(createGoogleButton());
  }

  if (googleSignInButton2) {
    googleSignInButton2.innerHTML = '';
    googleSignInButton2.appendChild(createGoogleButton());
  }
}

/**
 * Set up authentication event listeners
 */
function setupAuthEventListeners() {
  // Get references to the store and UI
  const store = window.YCG_STORE;

  // Login button
  const loginBtn = document.getElementById('login-btn');
  if (loginBtn) {
    loginBtn.addEventListener('click', () => {
      store.dispatch('ui', {
        type: 'SET_ACTIVE_VIEW',
        payload: { view: 'auth' }
      });
    });
  }
}

/**
 * Handle Google Sign-In button click
 */
async function handleGoogleSignIn() {
  console.log("[Auth] Google Sign-In button clicked");

  // Get references to the store and API
  const store = window.YCG_STORE;
  const api = window.YCG_API;

  if (!store || !api) {
    console.error("[Auth] Store or API not available");
    if (window.YCG_UI) {
      window.YCG_UI.showNotification("Authentication service not available", "error");
    }
    return;
  }

  // Dispatch login start action
  store.dispatch('auth', { type: 'LOGIN_START' });

  try {
    // Launch Google Sign-In
    const token = await launchGoogleSignIn();

    if (!token) {
      throw new Error("Failed to get Google token");
    }

    console.log("[Auth] Got Google token, logging in...");

    // Login with Google
    const loginResult = await api.loginWithGoogle(token);

    if (!loginResult || !loginResult.access_token) {
      throw new Error("Failed to login with Google: No access token returned");
    }

    console.log("[Auth] Login result:", loginResult);
    console.log("[Auth] Login successful");

    // Extract user info and token
    const { access_token, user_id, email, name, picture, credits } = loginResult;

    // Update auth state
    store.dispatch('auth', {
      type: 'LOGIN_SUCCESS',
      payload: {
        user: {
          id: user_id,
          email,
          name,
          picture
        },
        token: access_token
      }
    });

    // Update credits
    store.dispatch('credits', {
      type: 'SET_CREDITS',
      payload: {
        count: credits || 0
      }
    });

    // Set active view to main
    store.dispatch('ui', {
      type: 'SET_ACTIVE_VIEW',
      payload: { view: 'main' }
    });

    // Save state to storage
    await store.saveToStorage();

    // Show success notification
    if (window.YCG_UI) {
      window.YCG_UI.showNotification("Successfully logged in!", "success");
    }
  } catch (error) {
    console.error("[Auth] Error during Google Sign-In:", error);
    handleAuthError(store, error);

    // Show error notification
    if (window.YCG_UI) {
      window.YCG_UI.showNotification(`Login failed: ${error.message}`, "error");
    }
  }
}

/**
 * Launch Google Sign-In
 * @returns {Promise<string>} The Google OAuth token
 */
function launchGoogleSignIn() {
  return new Promise((resolve, reject) => {
    try {
      console.log('[Auth] Requesting Google auth token...');

      // First try to clear any cached tokens
      chrome.identity.clearAllCachedAuthTokens(() => {
        console.log('[Auth] Cleared cached tokens');

        // Now get a fresh token
        chrome.identity.getAuthToken({ interactive: true }, (token) => {
          if (chrome.runtime.lastError) {
            console.error('[Auth] Chrome identity error:', chrome.runtime.lastError);
            reject(new Error(chrome.runtime.lastError.message));
            return;
          }

          if (!token) {
            console.error('[Auth] No token returned from Google');
            reject(new Error("Failed to get auth token"));
            return;
          }

          console.log('[Auth] Got Google auth token:', token.substring(0, 10) + '...');
          resolve(token);
        });
      });
    } catch (error) {
      console.error('[Auth] Error in launchGoogleSignIn:', error);
      reject(error);
    }
  });
}

/**
 * Handle authentication error
 * @param {Object} store - The state store
 * @param {Error} error - The error object
 */
function handleAuthError(store, error) {
  console.error("[Auth] Authentication error:", error);

  // Dispatch login failure action
  store.dispatch('auth', {
    type: 'LOGIN_FAILURE',
    payload: {
      error: error.message
    }
  });

  // Set active view to welcome
  store.dispatch('ui', {
    type: 'SET_ACTIVE_VIEW',
    payload: { view: 'welcome' }
  });

  // Save state to storage
  store.saveToStorage();
}
