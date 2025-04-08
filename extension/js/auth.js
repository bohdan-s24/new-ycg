// YouTube Chapter Generator Authentication Module

// API endpoints
// Use production server only
const AUTH_BASE_URL = "https://new-ycg.vercel.app/api";
const LOGIN_ENDPOINT = `${AUTH_BASE_URL}/auth/login`;
const GOOGLE_LOGIN_ENDPOINT = `${AUTH_BASE_URL}/auth/login/google`;
const CONFIG_ENDPOINT = `${AUTH_BASE_URL}/config`;
const VERIFY_TOKEN_ENDPOINT = `${AUTH_BASE_URL}/auth/verify`;
const USER_INFO_ENDPOINT = `${AUTH_BASE_URL}/auth/user`;

// State
let currentUser = null;
let authToken = null;
let user = null;

// Constants
const USER_KEY = 'ycg_user';

// DOM Elements
let loginBtn = null;
let settingsBtn = null;
let userProfile = null;
let userMenu = null;
let userAvatar = null;
let menuUserAvatar = null;
let userName = null;
let userEmail = null;
let creditsCount = null;
let creditsContainer = null;
let logoutLink = null;
let welcomeContainer = null;
let authContainer = null;
let mainContent = null;

// Initialize auth
document.addEventListener("DOMContentLoaded", async function() {
  // Initialize auth only after DOM is fully loaded
  await initAuth();
});

// Initialize auth
async function initAuth() {
  console.log("Initializing auth...");

  // Initialize DOM elements
  initDomElements();

  // Setup event listeners
  setupEventListeners();

  // Try to get user from localStorage
  await loadUserFromStorage();

  // Initialize Google Sign-In with Chrome's identity API
  await initGoogleSignIn();

  // Update UI based on auth state
  updateAuthUI();

  console.log("Auth initialization complete");
}

// Initialize Google Sign-In with Chrome's identity API
async function initGoogleSignIn() {
  console.log("[Auth] Initializing Google Sign-In with Chrome's identity API");

  try {
    // Find the Google Sign-In button containers
    const googleButtonContainer1 = document.getElementById('google-signin-button');
    const googleButtonContainer2 = document.getElementById('google-signin-button-auth');

    console.log("[Auth] Google button containers:", {
      'google-signin-button': !!googleButtonContainer1,
      'google-signin-button-auth': !!googleButtonContainer2
    });

    // Helper function to create a Google Sign-In button
    const createGoogleButton = () => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = 'Sign in with Google';
      button.style.padding = '8px 16px';
      button.style.borderRadius = '4px';
      button.style.backgroundColor = '#4285F4';
      button.style.color = 'white';
      button.style.border = 'none';
      button.style.cursor = 'pointer';
      button.style.fontSize = '14px';
      button.style.width = '240px';
      button.style.display = 'block';
      button.style.margin = '10px auto';

      // Add event listener safely
      button.addEventListener('click', () => {
        console.log("[Auth] Google Sign-In button clicked");
        handleGoogleSignIn();
      });

      return button;
    };

    // Helper function to add a button to a container
    const addButtonToContainer = (container, containerName) => {
      if (container) {
        try {
          // Clear any existing content
          container.innerHTML = '';

          // Create and add the button
          const button = createGoogleButton();
          container.appendChild(button);
          console.log(`[Auth] Added Google Sign-In button to ${containerName}`);
          return true;
        } catch (error) {
          console.error(`[Auth] Error adding button to ${containerName}:`, error);
          return false;
        }
      } else {
        console.warn(`[Auth] ${containerName} not found`);
        return false;
      }
    };

    // Add buttons to containers
    const container1Success = addButtonToContainer(googleButtonContainer1, 'container 1');
    const container2Success = addButtonToContainer(googleButtonContainer2, 'container 2');

    if (!container1Success && !container2Success) {
      console.error("[Auth] Failed to add Google Sign-In buttons to any container");
    }

    // Clear any cached tokens on initialization
    await clearGoogleAuthTokens();

    console.log("[Auth] Google Sign-In buttons initialization complete");
  } catch (error) {
    console.error("[Auth] Error initializing Google Sign-In:", error);
  }
}

// Clear Google auth token cache
async function clearGoogleAuthTokens() {
  console.log("[Auth] Clearing Google auth token cache");

  if (!chrome.identity) {
    console.error("[Auth] chrome.identity API is not available");
    return false;
  }

  return new Promise((resolve) => {
    try {
      chrome.identity.clearAllCachedAuthTokens(() => {
        if (chrome.runtime.lastError) {
          console.error("[Auth] Error clearing tokens:", chrome.runtime.lastError);
          resolve(false);
        } else {
          console.log("[Auth] Successfully cleared all cached auth tokens");
          resolve(true);
        }
      });
    } catch (error) {
      console.error("[Auth] Exception during clearAllCachedAuthTokens:", error);
      resolve(false);
    }
  });
}

// Handle Google Sign-In
async function handleGoogleSignIn() {
  try {
    console.log("[Auth] Attempting to get auth token from Chrome identity API");

    // Check if chrome.identity is available
    if (!chrome.identity) {
      console.error("[Auth] chrome.identity API is not available");
      displayError("Chrome identity API is not available. Make sure the extension has the identity permission.");
      return;
    }

    // Clear cached tokens first
    await clearGoogleAuthTokens();

    // Get the token from Chrome's identity API
    console.log("[Auth] Calling chrome.identity.getAuthToken");

    // First, try to remove any cached tokens that might be causing issues
    await new Promise((resolve) => {
      chrome.identity.removeCachedAuthToken({ token: '' }, resolve);
    });

    const tokenObj = await new Promise((resolve, reject) => {
      try {
        chrome.identity.getAuthToken({ interactive: true }, (token) => {
          if (chrome.runtime.lastError) {
            console.error("[Auth] Chrome identity error:", chrome.runtime.lastError);
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve(token);
          }
        });
      } catch (error) {
        console.error("[Auth] Exception during getAuthToken:", error);
        reject(error);
      }
    });

    // Check if we got a valid token
    if (!tokenObj) {
      throw new Error("Failed to get authentication token from Google");
    }

    const token = tokenObj;
    console.log("[Auth] Successfully got auth token:", token);

    // Exchange token with backend
    console.log(`[Auth] Sending token to backend: ${GOOGLE_LOGIN_ENDPOINT}`);
    let response;
    try {
      response = await fetch(GOOGLE_LOGIN_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          token: token,
          platform: 'chrome_extension'
        })
      });

      console.log(`[Auth] Backend response status: ${response.status}`);

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[Auth] Login failed: ${response.status}. Response: ${errorText}`);

        // Handle different error codes
        if (response.status === 403) {
          console.log("[Auth] Received 403 error, attempting to revoke token and retry");

          // Revoke the token
          await new Promise((resolve) => {
            chrome.identity.removeCachedAuthToken({ token }, () => {
              console.log("[Auth] Removed cached auth token");
              resolve();
            });
          });

          throw new Error(`Login failed: ${response.status}. Please try again.`);
        } else if (response.status === 404) {
          console.error("[Auth] API endpoint not found. Check server configuration.");
          throw new Error(`Backend API not found (404). Please check server configuration.`);
        } else {
          throw new Error(`Login failed: ${response.status}`);
        }
      }
    } catch (fetchError) {
      console.error("[Auth] Fetch error during token exchange:", fetchError);
      throw new Error(`Network error during login: ${fetchError.message}`);
    }

    const data = await response.json();
    console.log("[Auth] Backend response data:", data);

    if (!data.data || !data.data.access_token) {
      console.error("[Auth] Invalid response from server:", data);
      throw new Error("Invalid response from server");
    }

    // Save auth token
    const authToken = data.data.access_token;

    // Fetch user info with the new token
    console.log("[Auth] Authentication successful, fetching user info");
    const userInfoResponse = await fetch(USER_INFO_ENDPOINT, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    if (!userInfoResponse.ok) {
      console.error(`[Auth] User info fetch failed: ${userInfoResponse.status}`);
      throw new Error("Failed to get user information. Please try again.");
    }

    const userInfoData = await userInfoResponse.json();

    if (!userInfoData.data) {
      console.error("[Auth] Invalid user info response:", userInfoData);
      throw new Error("Invalid user data received. Please try again.");
    }

    // Check if user received their free credits (backend should handle this automatically)
    console.log("[Auth] User info received:", userInfoData.data);

    // Save user data to local storage
    user = {
      ...userInfoData.data,
      token: authToken
    };

    localStorage.setItem(USER_KEY, JSON.stringify(user));

    // Update UI
    updateAuthUI();

    console.log("[Auth] Google Sign-In completed successfully");

    // If this is a new user, show a welcome message
    if (data.data.new_user) {
      setTimeout(() => {
        alert(`Welcome to YouTube Chapter Generator! You've received ${user.credits} free credits to get started.`);
      }, 500); // Small delay to ensure UI is updated
    }
  } catch (error) {
    console.error("[Auth] Google Sign-In error:", error);
    displayError(error.message);
  }
}

// Initialize all DOM element references
function initDomElements() {
  console.log("[Auth] Initializing DOM elements");

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
  welcomeContainer = document.getElementById('welcome-container');
  authContainer = document.getElementById('auth-container');
  mainContent = document.getElementById('main-content');

  // Log which elements were found
  console.log("[Auth] Found DOM elements:", {
    loginBtn: !!loginBtn,
    settingsBtn: !!settingsBtn,
    userProfile: !!userProfile,
    userMenu: !!userMenu,
    userAvatar: !!userAvatar,
    menuUserAvatar: !!menuUserAvatar,
    userName: !!userName,
    userEmail: !!userEmail,
    creditsCount: !!creditsCount,
    creditsContainer: !!creditsContainer,
    logoutLink: !!logoutLink,
    welcomeContainer: !!welcomeContainer,
    authContainer: !!authContainer,
    mainContent: !!mainContent
  });

  console.log("[Auth] DOM elements initialized");
}

// Setup event listeners
function setupEventListeners() {
  console.log("[Auth] Setting up event listeners");

  // Helper function to safely add event listeners
  const safeAddEventListener = (element, eventType, handler) => {
    if (element) {
      element.addEventListener(eventType, handler);
      return true;
    }
    return false;
  };

  // Login button
  const loginBtnSuccess = safeAddEventListener(loginBtn, 'click', () => {
    console.log("[Auth] Login button clicked");
    toggleAuthContainer();
  });
  if (!loginBtnSuccess) {
    console.warn("[Auth] Login button element not found");
  }

  // Settings button
  const settingsBtnSuccess = safeAddEventListener(settingsBtn, 'click', () => {
    console.log("[Auth] Settings button clicked");
    toggleUserMenu();
  });
  if (!settingsBtnSuccess) {
    console.warn("[Auth] Settings button element not found");
  }

  // User profile
  const userProfileSuccess = safeAddEventListener(userProfile, 'click', () => {
    console.log("[Auth] User profile clicked");
    toggleUserMenu();
  });
  if (!userProfileSuccess) {
    console.warn("[Auth] User profile element not found");
  }

  // Logout link
  const logoutLinkSuccess = safeAddEventListener(logoutLink, 'click', (e) => {
    console.log("[Auth] Logout link clicked");
    e.preventDefault();
    logout();
  });
  if (!logoutLinkSuccess) {
    console.warn("[Auth] Logout link element not found");
  }

  // Close user menu when clicking outside
  document.addEventListener('click', (e) => {
    if (userMenu) {
      const isClickInsideMenu = userMenu.contains(e.target);
      const isClickOnSettingsBtn = settingsBtn && settingsBtn.contains(e.target);
      const isClickOnUserProfile = userProfile && userProfile.contains(e.target);

      if (!isClickInsideMenu && !isClickOnSettingsBtn && !isClickOnUserProfile) {
        userMenu.classList.add('hidden');
      }
    }
  });

  console.log("[Auth] Event listeners setup complete");
}

// Toggle the auth container visibility
function toggleAuthContainer() {
  console.log("[Auth] Toggling auth container");

  if (authContainer) {
    authContainer.classList.toggle('hidden');
  } else {
    console.warn("[Auth] Auth container element not found");
  }
}

// Toggle the user menu
function toggleUserMenu() {
  console.log("[Auth] Toggling user menu");

  if (userMenu) {
    userMenu.classList.toggle('hidden');
  } else {
    console.warn("[Auth] User menu element not found");
  }
}

// Load user from localStorage
async function loadUserFromStorage() {
  console.log("[Auth] Loading user from storage");

  const storedUser = localStorage.getItem(USER_KEY);

  if (!storedUser) {
    console.log("[Auth] No user found in storage");
    return;
  }

  try {
    user = JSON.parse(storedUser);
    console.log("[Auth] User loaded from storage");

    // Validate and refresh user data
    await refreshUserData();
  } catch (error) {
    console.error("[Auth] Error loading user from storage:", error);
    localStorage.removeItem(USER_KEY);
    user = null;
  }
}

// Refresh user data from backend
async function refreshUserData() {
  console.log("[Auth] Refreshing user data from backend");

  if (!user || !user.id || !user.token) {
    console.warn("[Auth] No valid user data to refresh");
    return false;
  }

  try {
    const response = await fetch(`${USER_INFO_ENDPOINT}`, {
      headers: {
        'Authorization': `Bearer ${user.token}`
      }
    });

    if (!response.ok) {
      console.error(`[Auth] Failed to refresh user data: ${response.status} ${response.statusText}`);

      // If unauthorized, logout
      if (response.status === 401) {
        console.log("[Auth] User unauthorized, logging out");
        logout();
      }

      return false;
    }

    const userData = await response.json();

    if (!userData || !userData.data) {
      console.error("[Auth] Invalid response when refreshing user data");
      return false;
    }

    // Update user data
    user = { ...user, ...userData.data };
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    console.log("[Auth] User data refreshed successfully");

    return true;
  } catch (error) {
    console.error("[Auth] Error refreshing user data:", error);
    return false;
  }
}

// Logout the user
function logout() {
  console.log("[Auth] Logging out user");

  // Clear user data
  user = null;
  localStorage.removeItem(USER_KEY);

  // Update UI
  updateAuthUI();

  console.log("[Auth] User logged out successfully");
}

// Update the UI based on auth state
function updateAuthUI() {
  console.log("[Auth] Updating auth UI");

  if (user) {
    console.log("[Auth] User is logged in, updating UI for authenticated state");
    console.log("[Auth] User data:", user);

    // Show authenticated UI elements
    if (loginBtn) loginBtn.classList.add('hidden');
    if (settingsBtn) settingsBtn.classList.remove('hidden');
    if (userProfile) userProfile.classList.remove('hidden');
    if (creditsContainer) creditsContainer.classList.remove('hidden');

    // Hide welcome and auth container
    if (welcomeContainer) welcomeContainer.classList.add('hidden');
    if (authContainer) authContainer.classList.add('hidden');

    // Show main content
    if (mainContent) {
      mainContent.classList.remove('hidden');
      console.log("[Auth] Main content is now visible");
    } else {
      console.error("[Auth] Main content element not found!");
    }

    // Update user info
    if (userAvatar) {
      if (user.picture) {
        userAvatar.src = user.picture;
      } else {
        console.log("[Auth] No user picture available, using default");
      }
    }

    if (menuUserAvatar) {
      if (user.picture) {
        menuUserAvatar.src = user.picture;
      }
    }

    if (userName) {
      userName.textContent = user.name || 'User';
      console.log("[Auth] Set user name to:", userName.textContent);
    }

    if (userEmail) {
      userEmail.textContent = user.email || '';
      console.log("[Auth] Set user email to:", userEmail.textContent);
    }

    // Update credits
    if (creditsCount) {
      creditsCount.textContent = user.credits !== undefined ? user.credits : '-';
      console.log("[Auth] Set credits count to:", creditsCount.textContent);
    } else {
      console.error("[Auth] Credits count element not found!");
    }

    // Give new users 3 free credits
    if (user.credits === undefined) {
      console.log("[Auth] User has no credits, initializing with 3 free credits");
      user.credits = 3;
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      if (creditsCount) {
        creditsCount.textContent = user.credits;
      }
    }
  } else {
    console.log("[Auth] No user logged in, updating UI for unauthenticated state");

    // Show unauthenticated UI elements
    if (loginBtn) loginBtn.classList.remove('hidden');
    if (settingsBtn) settingsBtn.classList.add('hidden');
    if (userProfile) userProfile.classList.add('hidden');
    if (creditsContainer) creditsContainer.classList.add('hidden');

    // Show welcome screen, hide auth container
    if (welcomeContainer) {
      welcomeContainer.classList.remove('hidden');
      // Add explicit styling to ensure Google button is visible
      const googleButtonContainer = document.getElementById('google-signin-button');
      if (googleButtonContainer) {
        googleButtonContainer.style.display = 'inline-flex !important';
        googleButtonContainer.style.justifyContent = 'center';
        googleButtonContainer.style.margin = '24px auto';
        googleButtonContainer.style.width = '100%';
        googleButtonContainer.style.maxWidth = '240px';
      }
    }
    if (authContainer) authContainer.classList.add('hidden');

    // Hide main content
    if (mainContent) mainContent.classList.add('hidden');
  }

  console.log("[Auth] Auth UI update complete");
}

// Display an error message
function displayError(message) {
  console.error(`[Auth] Error: ${message}`);

  // Find the error element
  const errorElement = document.getElementById('error-message');

  if (errorElement) {
    console.log("[Auth] Displaying error in error-message element");
    errorElement.textContent = message;
    errorElement.classList.remove('hidden');

    // Make sure the auth container is visible
    const authContainer = document.getElementById('auth-container');
    if (authContainer) {
      authContainer.classList.remove('hidden');
    }

    // Hide after 10 seconds
    setTimeout(() => {
      errorElement.classList.add('hidden');
    }, 10000);
  } else {
    // Fallback to alert if error element doesn't exist
    console.log("[Auth] Error element not found, using alert instead");
    alert(`Authentication Error: ${message}`);
  }
}

// Get the current user
function getCurrentUser() {
  return user;
}

// Check if user is logged in
function isLoggedIn() {
  return !!user;
}

// Export functions for external use
window.auth = {
  getCurrentUser,
  isLoggedIn,
  logout
};
