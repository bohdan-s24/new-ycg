// YouTube Chapter Generator Authentication Module

// API endpoints (Corrected based on Flask structure and vercel.json)
const AUTH_BASE_URL = window.YCG_CONFIG.AUTH_BASE_URL; // Should be https://.../auth
const LOGIN_ENDPOINT = `${AUTH_BASE_URL}/login`;
const GOOGLE_LOGIN_ENDPOINT = `${AUTH_BASE_URL}/login/google`;
const CONFIG_ENDPOINT = `${AUTH_BASE_URL}/config`;
const VERIFY_TOKEN_ENDPOINT = `${AUTH_BASE_URL}/verify`;
const USER_INFO_ENDPOINT = `${AUTH_BASE_URL}/user`;
// Note: Ensure popup.js uses correct base URL for its endpoints if needed

// State
let currentUser = null; // Use this consistently
let authToken = null;
// let user = null; // Removed redundant variable

// Constants
const USER_KEY = 'ycg_user_data'; // Key for localStorage (changed for clarity)

// DOM Elements (initialized in initDomElements)
let loginBtn, settingsBtn, userProfile, userMenu, userAvatar, menuUserAvatar, userName, userEmail, creditsCount, creditsContainer, logoutLink, welcomeContainer, authContainer, mainContent, googleSignInButton1, googleSignInButton2;

// Initialize auth
document.addEventListener("DOMContentLoaded", initAuth); // Removed async here, initAuth handles async parts

// Initialize auth
async function initAuth() {
  console.log("[Auth] Initializing auth...");
  initDomElements();
  setupEventListeners();
  await loadUserFromStorage(); // Tries to load and validate currentUser
  // Don't init Google Sign-In buttons here, do it based on logged-out state in updateAuthUI
  updateAuthUI(); // Initial UI update based on loaded state
  console.log("[Auth] Initialization complete. Initial currentUser state:", currentUser);
}

// Initialize Google Sign-In buttons (called by updateAuthUI when needed)
function initGoogleSignInButtons() {
  console.log("[Auth] Initializing Google Sign-In buttons...");
  try {
    const createGoogleButton = () => {
        const button = document.createElement('button');
        button.type = 'button';
        button.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" style="margin-right: 8px;"><path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z"/><path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/><path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/><path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"/></svg> Sign in with Google`;
        button.className = 'btn google-signin-btn-dynamic'; // Use a specific class
        button.style.width = 'auto';
        button.style.margin = '10px auto';
        button.addEventListener('click', handleGoogleSignIn);
        return button;
    };

    // Find the Google sign-in button containers
    const googleSignInButton1 = document.getElementById('google-signin-button');
    const googleSignInButton2 = document.getElementById('google-signin-button-auth');

    console.log("[Auth] Google button containers:", {
      'google-signin-button': !!googleSignInButton1,
      'google-signin-button-auth': !!googleSignInButton2
    });

    // Add buttons to both containers
    if (googleSignInButton1) {
      googleSignInButton1.innerHTML = '';
      googleSignInButton1.appendChild(createGoogleButton());
      console.log("[Auth] Added Google Sign-In button to container 1");
    }

    if (googleSignInButton2) {
      googleSignInButton2.innerHTML = '';
      googleSignInButton2.appendChild(createGoogleButton());
      console.log("[Auth] Added Google Sign-In button to container 2");
    }

    console.log("[Auth] Google Sign-In buttons initialization complete.");
  } catch (error) {
    console.error("[Auth] Error initializing Google Sign-In buttons:", error);
  }
}

// Clear Google auth token cache
async function clearGoogleAuthTokens() {
  console.log("[Auth] Clearing Google auth token cache");
  if (!chrome.identity) { console.error("[Auth] chrome.identity API is not available"); return false; }
  return new Promise((resolve) => {
    try {
      chrome.identity.clearAllCachedAuthTokens(() => {
        if (chrome.runtime.lastError) { console.error("[Auth] Error clearing tokens:", chrome.runtime.lastError); resolve(false); }
        else { console.log("[Auth] Successfully cleared all cached auth tokens"); resolve(true); }
      });
    } catch (error) { console.error("[Auth] Exception during clearAllCachedAuthTokens:", error); resolve(false); }
  });
}

// Handle Google Sign-In button click
async function handleGoogleSignIn() {
  console.log("[Auth] Google Sign-In button clicked");
  // Show loading state on button? (Need button reference)
  try {
    if (!chrome.identity) {
      console.error("[Auth] chrome.identity API is not available");
      return displayError("Chrome identity API is not available.");
    }

    // Clear any existing tokens first
    console.log("[Auth] Clearing Google auth token cache");
    await clearGoogleAuthTokens();

    console.log("[Auth] Attempting chrome.identity.getAuthToken...");
    const token = await new Promise((resolve, reject) => {
      chrome.identity.getAuthToken({ interactive: true }, (token) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message || "Unknown Chrome Identity error"));
        } else if (!token) {
           reject(new Error("No token received from Google."));
        }
         else {
          resolve(token);
        }
      });
    });
    console.log("[Auth] Received OAuth token from Chrome identity.");

    console.log(`[Auth] Sending token to backend: ${GOOGLE_LOGIN_ENDPOINT}`);

    // Log token prefix for debugging (not the full token for security)
    const tokenPrefix = token.substring(0, 10);
    console.log(`[Auth] Token prefix: ${tokenPrefix}...`);

    let response;
    let data;

    try {
      response = await fetch(GOOGLE_LOGIN_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token, platform: 'chrome_extension' })
      });

      console.log(`[Auth] Backend response status: ${response.status}`);

      const responseText = await response.text();
      console.log(`[Auth] Backend response text: ${responseText.substring(0, 100)}...`);

      if (!response.ok) {
        console.error(`[Auth] Backend login failed: ${response.status} ${responseText}`);
        // Attempt to revoke token if backend failed
        chrome.identity.removeCachedAuthToken({ token }, () => console.log("[Auth] Revoked potentially invalid token after backend error."));

        if (response.status === 500) {
          throw new Error(`Server error (500). Please try again later or contact support.`);
        } else {
          throw new Error(`Backend login failed (${response.status}). Check server logs.`);
        }
      }

      // Parse the response text as JSON
      try {
        data = JSON.parse(responseText);
      } catch (jsonError) {
        console.error("[Auth] Failed to parse response as JSON:", jsonError);
        throw new Error("Invalid response format from server.");
      }
    } catch (fetchError) {
      console.error("[Auth] Fetch error during token exchange:", fetchError);
      throw new Error(`Network error during login: ${fetchError.message}`);
    }

    console.log("[Auth] Backend response data:", data);
    if (!data.success || !data.data || !data.data.access_token) {
      throw new Error("Invalid response format from backend.");
    }

    authToken = data.data.access_token;
    console.log("[Auth] Received app token from backend.");

    // Fetch user info immediately after getting token
    const userInfo = await fetchUserInfo(authToken); // Pass token directly
    if (!userInfo) {
        throw new Error("Failed to fetch user info after login.");
    }

    // Save combined info (token is now part of currentUser)
    localStorage.setItem(USER_KEY, JSON.stringify(currentUser));
    console.log("[Auth] User data saved to localStorage.");

    updateAuthUI(); // Update UI to logged-in state
    console.log("[Auth] Google Sign-In successful!");

  } catch (error) {
    console.error("[Auth] Google Sign-In error:", error);
    displayError(error.message || "An unknown error occurred during sign-in.");
  } finally {
     // Hide loading state on button?
  }
}

// Initialize all DOM element references
function initDomElements() {
  loginBtn = document.getElementById('login-btn');
  settingsBtn = document.getElementById('settings-btn');
  userProfile = document.getElementById('user-profile');
  userMenu = document.getElementById('user-menu');
  userAvatar = document.getElementById('user-avatar');
  menuUserAvatar = document.getElementById('menu-user-avatar');
  userName = document.getElementById('user-name');
  userEmail = document.getElementById('user-email');
  creditsCount = document.getElementById('credits-count');
  creditsContainer = document.getElementById('credits-badge');
  logoutLink = document.getElementById('logout-link');
  welcomeContainer = document.getElementById('welcome-container'); // Assuming this exists for initial view
  authContainer = document.getElementById('auth-container');
  mainContent = document.getElementById('main-content'); // Assuming this holds the main app UI
  googleSignInButton1 = document.getElementById('google-signin-button'); // Check if this ID exists
  googleSignInButton2 = document.getElementById('google-signin-button-auth'); // Check if this ID exists
  console.log("[Auth] DOM elements initialized.");
}

// Setup event listeners
function setupEventListeners() {
  console.log("[Auth] Setting up event listeners...");
  const safeAddEventListener = (element, eventType, handler) => {
    if (element) { element.addEventListener(eventType, handler); return true; }
    console.warn(`[Auth] Element not found for ${eventType} listener.`);
    return false;
  };

  safeAddEventListener(loginBtn, 'click', showAuthUI); // Show the auth container
  // Google button listener is added dynamically in initGoogleSignInButtons
  safeAddEventListener(settingsBtn, 'click', toggleUserMenu);
  safeAddEventListener(userProfile, 'click', toggleUserMenu);
  safeAddEventListener(logoutLink, 'click', (e) => { e.preventDefault(); logout(); });

  // Close user menu when clicking outside
  document.addEventListener('click', (e) => {
    if (userMenu && settingsBtn && userProfile && !userMenu.contains(e.target) && !settingsBtn.contains(e.target) && !userProfile.contains(e.target)) {
      userMenu.classList.add('hidden');
    }
  });
  console.log("[Auth] Event listeners setup complete.");
}

// Show the auth UI view
function showAuthUI() {
  console.log("[Auth] showAuthUI called.");
  if (authContainer) {
      authContainer.classList.remove('hidden');
      authContainer.style.display = 'block'; // Ensure it's block
      console.log("[Auth] Auth container made visible.");
      // Initialize buttons *after* container is visible
      initGoogleSignInButtons();
  } else {
      console.error("[Auth] Auth container not found!");
  }
  if (welcomeContainer) welcomeContainer.classList.add('hidden');
  if (mainContent) mainContent.classList.add('hidden');
}

// Hide the auth UI view
function hideAuthUI() {
    console.log("[Auth] hideAuthUI called.");
    if (authContainer) {
        authContainer.classList.add('hidden');
        authContainer.style.display = 'none'; // Explicitly hide
    }
    // Decide what to show instead (main content or welcome)
    if (mainContent) mainContent.classList.remove('hidden');
    else if (welcomeContainer) welcomeContainer.classList.remove('hidden');
}


// Toggle the user menu
function toggleUserMenu() {
  if (userMenu) userMenu.classList.toggle('hidden');
  else console.warn("[Auth] User menu element not found");
}

// Load user from localStorage and validate token
async function loadUserFromStorage() {
  console.log("[Auth] Loading user from storage...");
  const storedUserData = localStorage.getItem(USER_KEY);
  if (!storedUserData) {
    console.log("[Auth] No user data found in storage.");
    currentUser = null;
    authToken = null;
    return;
  }

  try {
    const storedUser = JSON.parse(storedUserData);
    if (!storedUser || !storedUser.token) {
        console.warn("[Auth] Invalid user data in storage.");
        logout(); // Clear invalid data
        return;
    }
    console.log("[Auth] User data found in storage:", storedUser.email);
    authToken = storedUser.token; // Set token first

    // Validate token and refresh user info
    const refreshedUser = await fetchUserInfo(authToken);
    if (refreshedUser) {
        currentUser = refreshedUser; // Assign validated & refreshed data
        localStorage.setItem(USER_KEY, JSON.stringify(currentUser)); // Update storage
        console.log("[Auth] User validated and refreshed.");
    } else {
        console.warn("[Auth] Token validation/refresh failed. Logging out.");
        logout(); // Logout if token is invalid or refresh fails
    }
  } catch (error) {
    console.error("[Auth] Error loading user from storage:", error);
    logout(); // Clear storage on error
  }
}

// Fetch user info from the server using a provided token
async function fetchUserInfo(tokenToUse) {
  console.log("[Auth] Fetching user info from backend...");
  if (!tokenToUse) {
    console.error("[Auth] fetchUserInfo called without a token.");
    return null;
  }

  try {
    const response = await fetch(USER_INFO_ENDPOINT, {
      headers: { 'Authorization': `Bearer ${tokenToUse}` }
    });
    console.log(`[Auth] User info response status: ${response.status}`);

    if (!response.ok) {
      // If unauthorized (401), the token is bad
      if (response.status === 401) {
         console.warn("[Auth] Unauthorized fetching user info. Token likely expired/invalid.");
         return null; // Indicate failure
      }
      throw new Error(`Failed to fetch user info: ${response.status}`);
    }

    const userData = await response.json();
    if (!userData.success || !userData.data) {
      console.error("[Auth] Invalid user info response format:", userData);
      throw new Error("Invalid user data received.");
    }

    console.log("[Auth] User info fetched successfully:", userData.data);
    // Return the user data along with the token used to fetch it
    return { ...userData.data, token: tokenToUse };

  } catch (error) {
    console.error("[Auth] Error fetching user info:", error);
    return null; // Indicate failure
  }
}

// Logout the user
function logout() {
  console.log("[Auth] Logging out user...");
  currentUser = null;
  authToken = null;
  localStorage.removeItem(USER_KEY);

  // Also revoke any Google tokens
  if (chrome.identity) {
      chrome.identity.getAuthToken({ interactive: false }, function(token) {
        if (token) {
          chrome.identity.removeCachedAuthToken({ token }, () => {
             console.log("[Auth] Cleared cached Google token on logout.");
          });
          // Also try revoking, although it might require user interaction
          // fetch(`https://accounts.google.com/o/oauth2/revoke?token=${token}`);
        }
      });
  }

  updateAuthUI(); // Update UI to logged-out state
  console.log("[Auth] User logged out successfully.");
}

// Update the UI based on auth state
function updateAuthUI() {
  console.log("[Auth] Updating auth UI. Current user:", currentUser);

  // Ensure DOM elements are available
  if (!loginBtn || !settingsBtn || !userProfile || !creditsContainer || !welcomeContainer || !authContainer || !mainContent) {
      console.warn("[Auth] Some UI elements not found during updateAuthUI. Re-initializing...");
      initDomElements(); // Try finding them again
      // Re-check if elements are found now
      if (!loginBtn || !settingsBtn || !userProfile || !creditsContainer || !welcomeContainer || !authContainer || !mainContent) {
          console.error("[Auth] Critical UI elements missing. Cannot update UI properly.");
          return; // Exit if elements are still missing
      }
  }


  if (currentUser && authToken) { // Check for currentUser AND authToken
    console.log("[Auth] Rendering logged-in state.");
    loginBtn.classList.add('hidden');
    settingsBtn.classList.remove('hidden');
    userProfile.classList.remove('hidden');
    creditsContainer.classList.remove('hidden');
    welcomeContainer?.classList.add('hidden'); // Hide welcome if it exists
    authContainer.classList.add('hidden'); // Hide auth form
    mainContent?.classList.remove('hidden'); // Show main app content if it exists

    // Update user details in profile and menu
    const picture = currentUser.picture || 'icons/user.png';
    if (userAvatar) userAvatar.src = picture;
    if (menuUserAvatar) menuUserAvatar.src = picture;
    if (userName) userName.textContent = currentUser.name || 'User';
    if (userEmail) userEmail.textContent = currentUser.email || '';
    if (creditsCount) creditsCount.textContent = currentUser.credits !== undefined ? currentUser.credits : '-';

  } else {
    console.log("[Auth] Rendering logged-out state.");
    loginBtn.classList.remove('hidden');
    settingsBtn.classList.add('hidden');
    userProfile.classList.add('hidden');
    creditsContainer.classList.add('hidden');
    if (userMenu) userMenu.classList.add('hidden'); // Ensure menu is hidden

    // Show initial screen (e.g., welcome or auth form)
    // Let's default to showing the auth form if logged out
    authContainer.classList.remove('hidden');
    authContainer.style.display = 'block'; // Ensure it's visible
    if (welcomeContainer) welcomeContainer.classList.add('hidden');
    if (mainContent) mainContent.classList.add('hidden');

    // Ensure Google Sign-In buttons are ready/visible in the auth container
    initGoogleSignInButtons();
  }
  console.log("[Auth] Auth UI update complete.");
}


// Display an error message
function displayError(message) {
  console.error(`[Auth] Error: ${message}`);
  const isServerError = message.includes('Server') || message.includes('500');
  const errorElement = document.getElementById('error-message');

  if (errorElement) {
    let displayMessage = message;
    if (isServerError) {
      displayMessage = "The server is currently experiencing issues. Please try again later.";
    } else if (message.includes("404")) {
        displayMessage = "Cannot reach the server (404). Please check your connection or contact support.";
    } else if (message.includes("403")) {
         displayMessage = "Authentication failed (403). Please try signing in again.";
    } else if (message.includes("token")) {
         displayMessage = "Failed to get authentication token. Please ensure you are signed into Chrome.";
    }

    errorElement.textContent = displayMessage;
    errorElement.classList.remove('hidden');

    // Show auth container on login errors
    if (message.toLowerCase().includes('login') || message.toLowerCase().includes('sign-in')) {
       if (authContainer) authContainer.classList.remove('hidden');
    }

    // Auto-hide error message
    setTimeout(() => {
      if (errorElement) errorElement.classList.add('hidden');
    }, 10000);
  } else {
    console.warn("[Auth] Error element not found, using alert.");
    alert(`Authentication Error: ${message}`);
  }
}

// Get the current user data
function getCurrentUser() {
  return currentUser;
}

// Check if user is logged in
function isLoggedIn() {
  return !!currentUser && !!authToken;
}

// Export functions for external use
window.auth = {
  getCurrentUser,
  isLoggedIn,
  logout
};
