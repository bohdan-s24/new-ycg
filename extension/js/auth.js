// YouTube Chapter Generator Authentication Module

// API endpoints
const AUTH_BASE_URL = "https://new-ycg.vercel.app/api";
const LOGIN_ENDPOINT = `${AUTH_BASE_URL}/auth/login`;
const GOOGLE_LOGIN_ENDPOINT = `${AUTH_BASE_URL}/auth/login/google`;
const CONFIG_ENDPOINT = `${AUTH_BASE_URL}/config`;
const VERIFY_TOKEN_ENDPOINT = `${AUTH_BASE_URL}/auth/verify`;
const USER_INFO_ENDPOINT = `${AUTH_BASE_URL}/auth/user`;

// Google Client ID from manifest.json
const GOOGLE_CLIENT_ID = "373897257675-i561f2gcpv310b61bptj0ge2bmvdm03m.apps.googleusercontent.com";

// State
let currentUser = null;
let authToken = null;
let isAuthInitialized = false;

// Global variables
let googleClientId = null;
let user = null;

// Constants
const USER_KEY = 'ycg_user';
const CLIENT_ID_CACHE_KEY = 'ycg_google_client_id';
const CLIENT_ID_CACHE_EXPIRY = 3600000; // 1 hour in milliseconds

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
  
  // Initialize Google Sign-In
  await initGoogleSignIn();
  
  // Update UI based on auth state
  updateAuthUI();
  
  console.log("Auth initialization complete");
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
  
  if (loginBtn) {
    loginBtn.addEventListener('click', () => {
      console.log("[Auth] Login button clicked");
      toggleAuthContainer();
    });
  } else {
    console.warn("[Auth] Login button element not found");
  }
  
  if (settingsBtn) {
    settingsBtn.addEventListener('click', () => {
      console.log("[Auth] Settings button clicked");
      toggleUserMenu();
    });
  } else {
    console.warn("[Auth] Settings button element not found");
  }
  
  if (userProfile) {
    userProfile.addEventListener('click', () => {
      console.log("[Auth] User profile clicked");
      toggleUserMenu();
    });
  } else {
    console.warn("[Auth] User profile element not found");
  }
  
  if (logoutLink) {
    logoutLink.addEventListener('click', (e) => {
      console.log("[Auth] Logout link clicked");
      e.preventDefault();
      logout();
    });
  } else {
    console.warn("[Auth] Logout link element not found");
  }
  
  // Close user menu when clicking outside
  document.addEventListener('click', (e) => {
    if (userMenu && !userMenu.contains(e.target) && 
        settingsBtn && !settingsBtn.contains(e.target) && 
        userProfile && !userProfile.contains(e.target)) {
      userMenu.classList.add('hidden');
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

// Initialize Google Sign-In
async function initGoogleSignIn() {
  console.log("[Auth] Initializing Google Sign-In");
  
  // Find the Google Sign-In button container
  const googleButtonContainer = document.getElementById('google-signin-button');
  
  if (!googleButtonContainer) {
    console.error("[Auth] Google Sign-In button container not found");
    return;
  }
  
  console.log("[Auth] Google Sign-In button container found:", googleButtonContainer);
  
  // Load the Google Identity Services JavaScript library
  const script = document.createElement('script');
  script.src = "https://accounts.google.com/gsi/client";
  script.async = true;
  script.defer = true;
  document.head.appendChild(script);
  
  // Wait for the script to load
  script.onload = () => {
    console.log("[Auth] Google Identity Services library loaded");
    
    // Make handleGoogleSignIn available globally
    window.handleGoogleSignIn = handleGoogleSignIn;
    
    // Initialize the button
    google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: window.handleGoogleSignIn,
      auto_select: false,
      cancel_on_tap_outside: true,
    });
    
    // Render the button
    google.accounts.id.renderButton(
      googleButtonContainer, 
      { 
        theme: "outline",
        size: "large",
        type: "standard",
        text: "continue_with",
        shape: "rectangular",
        logo_alignment: "left",
        width: 240
      }
    );
    
    console.log("[Auth] Google Sign-In button rendered");
    
    // Add a small delay to ensure the button is visible
    setTimeout(() => {
      googleButtonContainer.style.display = "inline-flex !important";
      console.log("[Auth] Button container display set to inline-flex");
    }, 100);
  };
  
  script.onerror = () => {
    console.error("[Auth] Failed to load Google Identity Services library");
    googleButtonContainer.innerHTML = "Failed to load Google Sign-In";
  };
}

// Handler for Google Sign-In
// This function will be called by the Google Sign-In button
async function handleGoogleSignIn(response) {
  console.log("[Auth] Google Sign-In response received");
  
  try {
    const token = response.credential;
    
    if (!token) {
      console.error("[Auth] No credential token received from Google");
      displayError("Google Sign-In failed. Please try again.");
      return;
    }
    
    console.log("[Auth] Google token received, calling backend for authentication");
    
    // Show loading indicator
    const googleButton = document.getElementById('google-signin-button');
    if (googleButton) {
      googleButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Signing in...';
      googleButton.disabled = true;
    }
    
    try {
      // Send token to backend for verification and user creation/retrieval
      const response = await fetch(GOOGLE_LOGIN_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          token: token,
          platform: 'chrome_extension'
        })
      });
      
      // Parse response JSON
      let data;
      try {
        data = await response.json();
      } catch (jsonError) {
        console.error("[Auth] Failed to parse authentication response:", jsonError);
        throw new Error("Server returned invalid response. Please try again later.");
      }
      
      // Check if response is successful
      if (!response.ok) {
        console.error(`[Auth] Backend authentication failed: ${response.status}`, data);
        const errorMessage = data?.error || `Server error (${response.status}). Please try again later.`;
        throw new Error(errorMessage);
      }
      
      if (!data.data || !data.data.access_token) {
        console.error("[Auth] Invalid response format, missing access token:", data);
        throw new Error("Invalid server response. Please try again later.");
      }
      
      // Save auth token
      const authToken = data.data.access_token;
      const isNewUser = data.data.new_user || false;
      
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
        token: authToken,
        isNewUser: isNewUser
      };
      
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      
      // Update UI
      updateAuthUI();
      
      console.log("[Auth] Google Sign-In completed successfully");
      
      // If this is a new user, show a welcome message
      if (isNewUser) {
        setTimeout(() => {
          alert(`Welcome to YouTube Chapter Generator! You've received ${user.credits} free credits to get started.`);
        }, 500); // Small delay to ensure UI is updated
      }
    } catch (error) {
      console.error("[Auth] Google Sign-In processing error:", error);
      displayError(error.message || "Authentication failed. Please try again.");
    } finally {
      // Reset button state
      if (googleButton) {
        googleButton.innerHTML = '<span class="google-icon"></span> Continue with Google';
        googleButton.disabled = false;
      }
    }
  } catch (error) {
    console.error("[Auth] Google Sign-In error:", error);
    displayError("Google Sign-In failed. Please try again.");
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
  
  if (!user || !user.userId || !user.token) {
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
    
    // Show authenticated UI elements
    if (loginBtn) loginBtn.classList.add('hidden');
    if (settingsBtn) settingsBtn.classList.remove('hidden');
    if (userProfile) userProfile.classList.remove('hidden');
    if (creditsContainer) creditsContainer.classList.remove('hidden');
    
    // Hide welcome and auth container
    if (welcomeContainer) welcomeContainer.classList.add('hidden');
    if (authContainer) authContainer.classList.add('hidden');
    
    // Show main content
    if (mainContent) mainContent.classList.remove('hidden');
    
    // Update user info
    if (userAvatar && user.picture) userAvatar.src = user.picture;
    if (menuUserAvatar && user.picture) menuUserAvatar.src = user.picture;
    if (userName) userName.textContent = user.name || 'User';
    if (userEmail) userEmail.textContent = user.email || '';
    
    // Update credits
    if (creditsCount) {
      creditsCount.textContent = user.credits !== undefined ? user.credits : '-';
    }
    
    // Give new users 3 free credits
    if (user.credits === undefined) {
      user.credits = 3;
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      creditsCount.textContent = user.credits;
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
    errorElement.textContent = message;
    errorElement.classList.remove('hidden');
    
    // Hide after 5 seconds
    setTimeout(() => {
      errorElement.classList.add('hidden');
    }, 5000);
  } else {
    // Fallback to alert if error element doesn't exist
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
