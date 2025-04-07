// YouTube Chapter Generator Authentication Module

// Use configuration from config.js
const AUTH_BASE_URL = window.YCG_CONFIG.AUTH_BASE_URL;
const LOGIN_ENDPOINT = `${AUTH_BASE_URL}/login`;
const GOOGLE_LOGIN_ENDPOINT = `${AUTH_BASE_URL}/login/google`;
const CONFIG_ENDPOINT = `${AUTH_BASE_URL}/config`;
const VERIFY_TOKEN_ENDPOINT = `${AUTH_BASE_URL}/verify`;
const USER_INFO_ENDPOINT = `${AUTH_BASE_URL}/user`;

// Auth elements
const loginButton = document.getElementById("login-btn");
const userProfileElement = document.getElementById("user-profile");
const userAvatarElement = document.getElementById("user-avatar");
const menuUserAvatarElement = document.getElementById("menu-user-avatar");
const userMenuElement = document.getElementById("user-menu");
const userNameElement = document.getElementById("user-name");
const userEmailElement = document.getElementById("user-email");
const logoutLink = document.getElementById("logout-link");
const myAccountLink = document.getElementById("my-account-link");
const buyCreditsLink = document.getElementById("buy-credits-link");
const authContainerElement = document.getElementById("auth-container");
const termsLink = document.getElementById("terms-link");
const privacyLink = document.getElementById("privacy-link");

// State
let currentUser = null;
let authToken = null;
let isAuthInitialized = false;

// Initialize auth
document.addEventListener("DOMContentLoaded", initAuth);

function initAuth() {
  console.log("Initializing auth module...");
  
  // Set up event listeners
  loginButton.addEventListener("click", showAuthUI);
  userProfileElement.addEventListener("click", toggleUserMenu);
  logoutLink.addEventListener("click", handleLogout);
  myAccountLink.addEventListener("click", openMyAccount);
  buyCreditsLink.addEventListener("click", openBuyCredits);
  termsLink.addEventListener("click", openTerms);
  privacyLink.addEventListener("click", openPrivacy);
  
  // Close menu when clicking outside
  document.addEventListener("click", (e) => {
    if (!userProfileElement.contains(e.target) && !userMenuElement.contains(e.target)) {
      userMenuElement.classList.add("hidden");
    }
  });

  // Initialize Google Sign-In
  initGoogleSignIn();
  
  // Check if user is already logged in
  checkAuthStatus();
}

// Initialize Google Sign-In
function initGoogleSignIn() {
  console.log("Setting up Google Sign-In...");
  
  // First try to fetch the client ID from the backend
  fetch(CONFIG_ENDPOINT)
    .then(response => {
      if (!response.ok) {
        throw new Error(`Failed to fetch auth config: ${response.status}`);
      }
      return response.json();
    })
    .then(config => {
      if (config.success && config.data && config.data.googleClientId) {
        // Use the client ID from the backend
        setupGoogleSignIn(config.data.googleClientId);
      } else {
        // Fallback to the client ID from config.js
        setupGoogleSignIn(window.YCG_CONFIG.GOOGLE_CLIENT_ID);
      }
    })
    .catch(error => {
      console.error("Error fetching Google Client ID from backend:", error);
      // Fallback to the client ID from config.js
      setupGoogleSignIn(window.YCG_CONFIG.GOOGLE_CLIENT_ID);
    });
}

// Set up Google Sign-In with the provided client ID
function setupGoogleSignIn(clientId) {
  if (!clientId || clientId === "PLACEHOLDER_GOOGLE_CLIENT_ID") {
    console.error("No valid Google Client ID available");
    return;
  }
  
  console.log("Setting up Google Sign-In with client ID:", clientId);
  
  // Update the Google Sign-In button with the client ID
  const gIdOnload = document.getElementById("g_id_onload");
  if (gIdOnload) {
    gIdOnload.setAttribute("data-client_id", clientId);
    console.log("Updated Google Sign-In button with Client ID");
    
    // Force re-initialization of Google Sign-In
    if (window.google && window.google.accounts && window.google.accounts.id) {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleGoogleSignIn
      });
      console.log("Re-initialized Google Sign-In");
    } else {
      console.warn("Google Sign-In library not loaded yet");
    }
  } else {
    console.error("Google Sign-In container not found in the DOM");
  }
}

// Check if the user is authenticated
async function checkAuthStatus() {
  try {
    // Try to get token from storage
    chrome.storage.sync.get(["authToken", "userInfo"], async (result) => {
      if (result.authToken) {
        authToken = result.authToken;
        
        // If we have stored user info, use it immediately
        if (result.userInfo) {
          currentUser = result.userInfo;
          updateUIForLoggedInUser();
        }
        
        // Verify token with server and get fresh user data
        try {
          const response = await verifyToken(authToken);
          if (response.valid) {
            await fetchUserInfo();
          } else {
            // Token invalid or expired
            handleLogout();
          }
        } catch (error) {
          console.error("Error verifying token:", error);
          // Don't log the user out immediately in case of server errors
          // They can still use the app with the stored user info
        }
      } else {
        // No token found, user is logged out
        updateUIForLoggedOutUser();
      }
      
      isAuthInitialized = true;
    });
  } catch (error) {
    console.error("Error checking auth status:", error);
    updateUIForLoggedOutUser();
    isAuthInitialized = true;
  }
}

// Show the auth UI
function showAuthUI() {
  authContainerElement.classList.remove("hidden");
  
  // Hide other UI elements
  const otherElements = [
    document.getElementById("status"),
    document.getElementById("video-info"),
    document.getElementById("error-message"),
    document.querySelector(".generate-button-container"),
    document.getElementById("loading"),
    document.getElementById("chapters-container")
  ];
  
  otherElements.forEach(el => {
    if (el && !el.classList.contains("hidden")) {
      el.dataset.wasVisible = "true";
      el.classList.add("hidden");
    }
  });
}

// Hide the auth UI and restore previous state
function hideAuthUI() {
  authContainerElement.classList.add("hidden");
  
  // Restore previously visible elements
  const otherElements = [
    document.getElementById("status"),
    document.getElementById("video-info"),
    document.getElementById("error-message"),
    document.querySelector(".generate-button-container"),
    document.getElementById("loading"),
    document.getElementById("chapters-container")
  ];
  
  otherElements.forEach(el => {
    if (el && el.dataset.wasVisible === "true") {
      el.classList.remove("hidden");
      delete el.dataset.wasVisible;
    }
  });
}

// Toggle user menu visibility
function toggleUserMenu() {
  userMenuElement.classList.toggle("hidden");
}

// Update UI for logged in user
function updateUIForLoggedInUser() {
  if (!currentUser) return;
  
  // Update user profile
  userAvatarElement.src = currentUser.picture || "icons/user.png";
  menuUserAvatarElement.src = currentUser.picture || "icons/user.png";
  userNameElement.textContent = currentUser.name || "User";
  userEmailElement.textContent = currentUser.email || "";
  
  // Update visibility
  loginButton.classList.add("hidden");
  userProfileElement.classList.remove("hidden");
  
  // Update credits display
  if (currentUser.credits !== undefined) {
    const creditsCountElement = document.getElementById("credits-count");
    if (creditsCountElement) {
      creditsCountElement.textContent = currentUser.credits;
      
      // Also update in popup.js state if it exists
      if (window.userCredits !== undefined) {
        window.userCredits = currentUser.credits;
      }
    }
  }
}

// Update UI for logged out user
function updateUIForLoggedOutUser() {
  // Update visibility
  loginButton.classList.remove("hidden");
  userProfileElement.classList.add("hidden");
  userMenuElement.classList.add("hidden");
  
  // Reset credits to default
  const creditsCountElement = document.getElementById("credits-count");
  if (creditsCountElement) {
    creditsCountElement.textContent = "-";
  }
}

// Handle Google Sign In callback
window.handleGoogleSignIn = async (response) => {
  try {
    console.log("Google Sign-In successful");
    
    // Send the ID token to your server using the Google-specific endpoint
    const loginResponse = await fetch(GOOGLE_LOGIN_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        token: response.credential
      })
    });
    
    if (!loginResponse.ok) {
      throw new Error(`Login failed: ${loginResponse.status}`);
    }
    
    const loginData = await loginResponse.json();
    
    // Check for success and extract token from the response
    if (!loginData.success) {
      throw new Error(`Login failed: ${loginData.error || "Unknown error"}`);
    }
    
    // Our backend returns data in a format like {"success": true, "data": {...}}
    // Extract the token from the data object
    if (!loginData.data || !loginData.data.access_token) {
      throw new Error("Invalid response format: access_token not found");
    }
    
    // Save the auth token
    authToken = loginData.data.access_token;
    chrome.storage.sync.set({ authToken });
    
    // Get user info
    await fetchUserInfo();
    
    // Hide auth UI
    hideAuthUI();
    
  } catch (error) {
    console.error("Error during Google Sign-In:", error);
    showError("Failed to sign in with Google. Please try again.");
  }
};

// Verify the token with the server
async function verifyToken(token) {
  try {
    const response = await fetch(VERIFY_TOKEN_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ token })
    });
    
    if (!response.ok) {
      return { valid: false };
    }
    
    return await response.json();
  } catch (error) {
    console.error("Error verifying token:", error);
    return { valid: false };
  }
}

// Fetch user info from the server
async function fetchUserInfo() {
  try {
    if (!authToken) {
      throw new Error("No auth token available");
    }
    
    const response = await fetch(USER_INFO_ENDPOINT, {
      headers: {
        "Authorization": `Bearer ${authToken}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch user info: ${response.status}`);
    }
    
    const userData = await response.json();
    currentUser = userData;
    
    // Save user info to storage
    chrome.storage.sync.set({ userInfo: currentUser });
    
    // Update UI
    updateUIForLoggedInUser();
    
    return currentUser;
  } catch (error) {
    console.error("Error fetching user info:", error);
    throw error;
  }
}

// Handle logout
function handleLogout() {
  // Clear auth data
  authToken = null;
  currentUser = null;
  chrome.storage.sync.remove(["authToken", "userInfo"]);
  
  // Update UI
  updateUIForLoggedOutUser();
}

// Open My Account page in a new tab
function openMyAccount() {
  chrome.tabs.create({ url: "https://new-ycg.vercel.app/account" });
}

// Open Buy Credits page in a new tab
function openBuyCredits() {
  chrome.tabs.create({ url: "https://new-ycg.vercel.app/credits" });
}

// Open Terms of Service in a new tab
function openTerms() {
  chrome.tabs.create({ url: "https://new-ycg.vercel.app/terms" });
}

// Open Privacy Policy in a new tab
function openPrivacy() {
  chrome.tabs.create({ url: "https://new-ycg.vercel.app/privacy" });
}

// Show error message - reused from popup.js
function showError(message) {
  const errorMessageElement = document.getElementById("error-message");
  if (errorMessageElement) {
    errorMessageElement.textContent = message;
    errorMessageElement.classList.remove("hidden");
    const statusElement = document.getElementById("status");
    if (statusElement) {
      statusElement.classList.add("hidden");
    }
    console.error(`Error displayed: ${message}`);
  }
}

// Export functions and state for use in popup.js
window.auth = {
  isAuthenticated: () => !!authToken,
  getCurrentUser: () => currentUser,
  getAuthToken: () => authToken,
  isAuthInitialized: () => isAuthInitialized
};
