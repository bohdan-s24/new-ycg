// YouTube Chapter Generator Authentication Module

// API endpoints
const AUTH_BASE_URL = "https://new-ycg.vercel.app/auth";
const LOGIN_ENDPOINT = `${AUTH_BASE_URL}/login`;
const GOOGLE_LOGIN_ENDPOINT = `${AUTH_BASE_URL}/login/google`;
const CONFIG_ENDPOINT = `${AUTH_BASE_URL}/config`;
const VERIFY_TOKEN_ENDPOINT = `${AUTH_BASE_URL}/verify`;
const USER_INFO_ENDPOINT = `${AUTH_BASE_URL}/user`;

// State
let currentUser = null;
let authToken = null;
let isAuthInitialized = false;

// Initialize auth
document.addEventListener("DOMContentLoaded", async function() {
  // Initialize auth only after DOM is fully loaded
  await initAuth();
});

// Initialize auth
async function initAuth() {
  console.log("Initializing auth...");
  
  // Get element references
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
  const termsLink = document.getElementById("terms-link");
  const privacyLink = document.getElementById("privacy-link");
  const authContainerElement = document.getElementById("auth-container");
  
  // Set up event listeners
  if (loginButton) loginButton.addEventListener("click", showAuthUI);
  if (userProfileElement) userProfileElement.addEventListener("click", toggleUserMenu);
  if (logoutLink) logoutLink.addEventListener("click", handleLogout);
  if (myAccountLink) myAccountLink.addEventListener("click", openMyAccount);
  if (buyCreditsLink) buyCreditsLink.addEventListener("click", openBuyCredits);
  if (termsLink) termsLink.addEventListener("click", openTerms);
  if (privacyLink) privacyLink.addEventListener("click", openPrivacy);
  
  // Close menu when clicking outside
  document.addEventListener("click", (e) => {
    if (userProfileElement && userMenuElement && 
        !userProfileElement.contains(e.target) && 
        !userMenuElement.contains(e.target)) {
      userMenuElement.classList.add("hidden");
    }
  });

  // Fetch Google Client ID and initialize Google Sign-In
  try {
    await initGoogleSignIn();
  } catch (error) {
    console.error("Failed to initialize Google Sign-In:", error);
    showError("Failed to initialize Google Sign-In. Please try reloading the extension.");
  }

  // Check if user is already logged in
  await checkAuthStatus();
  
  isAuthInitialized = true;
  console.log("Auth initialization complete");
}

// Initialize Google Sign-In by fetching the Client ID from the backend
async function initGoogleSignIn() {
  console.log("Initializing Google Sign-In...");
  try {
    // Add cache buster to prevent caching
    const cacheBuster = Date.now();
    const response = await fetch(`${CONFIG_ENDPOINT}?_=${cacheBuster}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch auth config: ${response.status}`);
    }
    
    const config = await response.json();
    console.log("Received config:", config);
    
    if (!config.data || !config.data.googleClientId) {
      throw new Error("Google Client ID not found in config response");
    }
    
    const googleClientId = config.data.googleClientId;
    console.log("Fetched Google Client ID from server:", googleClientId);
    
    // Update the Google Sign-In button with the fetched Client ID
    const gIdOnload = document.getElementById("g_id_onload");
    if (gIdOnload) {
      gIdOnload.setAttribute("data-client_id", googleClientId);
      console.log("Updated Google Sign-In button with Client ID");
      
      // Force Google Sign-In library to reinitialize
      if (window.google && window.google.accounts) {
        console.log("Reinitializing Google Sign-In...");
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: handleGoogleSignIn
        });
      } else {
        console.log("Google accounts library not loaded yet, will be initialized when script loads");
      }
    } else {
      console.error("Google Sign-In container (g_id_onload) not found in the DOM");
      throw new Error("Google Sign-In container not found");
    }
  } catch (error) {
    console.error("Error fetching Google Client ID:", error);
    throw error;
  }
}

// Check if the user is authenticated
async function checkAuthStatus() {
  try {
    console.log("Checking auth status...");
    
    // Try to get token from storage
    return new Promise((resolve) => {
      chrome.storage.sync.get(["authToken", "userInfo"], async (result) => {
        if (result.authToken) {
          authToken = result.authToken;
          console.log("Found auth token in storage");
          
          // If we have stored user info, use it immediately
          if (result.userInfo) {
            currentUser = result.userInfo;
            updateUIForLoggedInUser();
            console.log("User already logged in from stored info");
          }
          
          // Verify token with server and get fresh user data
          try {
            const response = await verifyToken(authToken);
            if (response.valid) {
              await fetchUserInfo();
              console.log("Token verified and user info refreshed");
            } else {
              // Token invalid or expired
              console.log("Token invalid or expired, logging out");
              handleLogout();
            }
          } catch (error) {
            console.error("Error verifying token:", error);
            // Don't log the user out immediately in case of server errors
          }
        } else {
          // No token found, user is logged out
          console.log("No auth token found, user is logged out");
          updateUIForLoggedOutUser();
        }
        
        resolve();
      });
    });
  } catch (error) {
    console.error("Error checking auth status:", error);
    updateUIForLoggedOutUser();
    throw error;
  }
}

// Global callback function for Google Sign-In
window.handleGoogleSignIn = async (response) => {
  try {
    console.log("Google Sign-In callback triggered");
    
    if (!response || !response.credential) {
      throw new Error("Invalid response from Google Sign-In");
    }
    
    console.log("Google Sign-In successful, received credential");
    
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
      const errorText = await loginResponse.text();
      console.error(`Login failed with status ${loginResponse.status}: ${errorText}`);
      throw new Error(`Login failed: ${loginResponse.status}`);
    }
    
    const loginData = await loginResponse.json();
    console.log("Received login response:", loginData);
    
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
    console.log("Auth token saved");
    
    // Get user info
    await fetchUserInfo();
    
    // Hide auth UI
    hideAuthUI();
    console.log("Login successful!");
    
  } catch (error) {
    console.error("Error during Google Sign-In:", error);
    showError("Failed to sign in with Google. Please try again.");
  }
};

// Show the auth UI
function showAuthUI() {
  const authContainerElement = document.getElementById("auth-container");
  if (!authContainerElement) {
    console.error("Auth container not found");
    return;
  }
  
  console.log("Showing auth UI");
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
  const authContainerElement = document.getElementById("auth-container");
  if (!authContainerElement) {
    console.error("Auth container not found");
    return;
  }
  
  console.log("Hiding auth UI");
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
  const userMenuElement = document.getElementById("user-menu");
  if (!userMenuElement) {
    console.error("User menu not found");
    return;
  }
  
  userMenuElement.classList.toggle("hidden");
}

// Update UI for logged in user
function updateUIForLoggedInUser() {
  if (!currentUser) return;
  
  const userAvatarElement = document.getElementById("user-avatar");
  const menuUserAvatarElement = document.getElementById("menu-user-avatar");
  const userNameElement = document.getElementById("user-name");
  const userEmailElement = document.getElementById("user-email");
  const loginButton = document.getElementById("login-btn");
  const userProfileElement = document.getElementById("user-profile");
  
  if (!userAvatarElement || !menuUserAvatarElement || !userNameElement || 
      !userEmailElement || !loginButton || !userProfileElement) {
    console.error("One or more user UI elements not found");
    return;
  }
  
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
  const loginButton = document.getElementById("login-btn");
  const userProfileElement = document.getElementById("user-profile");
  const userMenuElement = document.getElementById("user-menu");
  
  if (!loginButton || !userProfileElement || !userMenuElement) {
    console.error("One or more user UI elements not found");
    return;
  }
  
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
      console.error(`Token verification failed with status ${response.status}`);
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
  console.log("Logging out...");
  
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

// Show error message
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
