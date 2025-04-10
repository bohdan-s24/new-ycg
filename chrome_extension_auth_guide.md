# Chrome Extension Authentication Flow Guide

This guide explains the authentication flow for the YouTube Chapter Generator Chrome extension, focusing on Google Sign-In integration.

## Overview

The authentication flow follows these steps:

1. User clicks the extension icon to open the popup
2. User sees the welcome screen with a "Sign in with Google" button
3. User clicks the button to initiate Google authentication
4. Chrome Identity API handles the OAuth flow
5. The extension sends the token to the backend
6. The backend verifies the token and creates/retrieves the user
7. The extension receives a JWT token and user data
8. The extension updates the UI to show the authenticated state

## Implementation Details

### 1. Initial UI State

When the extension popup opens, it checks for existing authentication:

```javascript
async function initAuth() {
  initDomElements();
  setupEventListeners();
  await loadUserFromStorage();
  updateAuthUI();
}
```

### 2. Google Sign-In Button

The Google Sign-In button is created dynamically:

```javascript
function initGoogleSignInButtons() {
  const createGoogleButton = () => {
    const button = document.createElement('button');
    button.innerHTML = `<svg>...</svg> Sign in with Google`;
    button.className = 'btn google-signin-btn-dynamic';
    button.addEventListener('click', handleGoogleSignIn);
    return button;
  };
  
  // Add buttons to containers
  if (googleSignInButton1) {
    googleSignInButton1.innerHTML = '';
    googleSignInButton1.appendChild(createGoogleButton());
  }
}
```

### 3. Google Authentication

When the user clicks the Sign-In button:

```javascript
async function handleGoogleSignIn() {
  // Clear any existing tokens
  await clearGoogleAuthTokens();
  
  // Get a new token from Chrome Identity API
  const token = await new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ interactive: true }, (token) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else if (!token) {
        reject(new Error("No token received from Google."));
      } else {
        resolve(token);
      }
    });
  });
  
  // Send token to backend
  const response = await fetch(GOOGLE_LOGIN_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: token, platform: 'chrome_extension' })
  });
  
  // Parse response
  const data = JSON.parse(await response.text());
  
  // Save token and user info
  authToken = data.data.access_token;
  const userInfo = await fetchUserInfo(authToken);
  localStorage.setItem(USER_KEY, JSON.stringify(currentUser));
  
  // Update UI
  updateAuthUI();
}
```

### 4. UI Update After Authentication

After successful authentication, the UI is updated:

```javascript
function updateAuthUI() {
  if (currentUser && authToken) {
    // Show logged-in UI
    loginBtn.classList.add('hidden');
    settingsBtn.classList.remove('hidden');
    userProfile.classList.remove('hidden');
    creditsContainer.classList.remove('hidden');
    welcomeContainer?.classList.add('hidden');
    authContainer.classList.add('hidden');
    mainContent?.classList.remove('hidden');
    
    // Update user details
    userAvatar.src = currentUser.picture || 'icons/user.png';
    userName.textContent = currentUser.name || 'User';
    userEmail.textContent = currentUser.email || '';
    creditsCount.textContent = currentUser.credits !== undefined ? currentUser.credits : '-';
  } else {
    // Show logged-out UI
    loginBtn.classList.remove('hidden');
    settingsBtn.classList.add('hidden');
    userProfile.classList.add('hidden');
    creditsContainer.classList.add('hidden');
    
    // Show welcome screen
    welcomeContainer.classList.remove('hidden');
    authContainer.classList.add('hidden');
    mainContent.classList.add('hidden');
  }
}
```

### 5. Token Storage and Validation

The token is stored in localStorage and validated on startup:

```javascript
async function loadUserFromStorage() {
  const storedUserData = localStorage.getItem(USER_KEY);
  if (!storedUserData) {
    currentUser = null;
    authToken = null;
    return;
  }
  
  try {
    const storedUser = JSON.parse(storedUserData);
    if (!storedUser || !storedUser.token) {
      logout();
      return;
    }
    
    authToken = storedUser.token;
    
    // Validate token and refresh user info
    const refreshedUser = await fetchUserInfo(authToken);
    if (refreshedUser) {
      currentUser = refreshedUser;
      localStorage.setItem(USER_KEY, JSON.stringify(currentUser));
    } else {
      logout();
    }
  } catch (error) {
    logout();
  }
}
```

### 6. Logout

The logout function clears the token and updates the UI:

```javascript
function logout() {
  currentUser = null;
  authToken = null;
  localStorage.removeItem(USER_KEY);
  
  // Revoke Google token
  if (chrome.identity) {
    chrome.identity.getAuthToken({ interactive: false }, function(token) {
      if (token) {
        chrome.identity.removeCachedAuthToken({ token });
      }
    });
  }
  
  updateAuthUI();
}
```

## Common Issues and Solutions

### 1. Authentication State Not Persisting

**Problem**: User logs in but the extension doesn't remember the authentication state after closing and reopening.

**Solution**: Ensure the token is properly stored in localStorage:

```javascript
localStorage.setItem(USER_KEY, JSON.stringify({
  ...userInfo,
  token: authToken
}));
```

### 2. UI Not Updating After Login

**Problem**: Backend authentication succeeds but the UI doesn't update to show the logged-in state.

**Solution**: Ensure the updateAuthUI function is called after successful login and that all UI elements are properly referenced:

```javascript
// After successful login
updateAuthUI();

// Check that elements exist
if (!loginBtn || !settingsBtn || !userProfile) {
  console.error("Critical UI elements missing");
}
```

### 3. Token Validation Failing

**Problem**: The token is stored but fails validation on startup.

**Solution**: Implement proper error handling in the token validation process:

```javascript
try {
  const response = await fetch(VERIFY_TOKEN_ENDPOINT, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  if (!response.ok) {
    console.warn("Token validation failed");
    return null;
  }
  
  return await response.json();
} catch (error) {
  console.error("Error validating token:", error);
  return null;
}
```

### 4. Chrome Identity API Issues

**Problem**: Chrome Identity API fails to get a token.

**Solution**: Ensure the manifest.json has the correct permissions and OAuth2 configuration:

```json
{
  "permissions": ["identity"],
  "oauth2": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "scopes": [
      "https://www.googleapis.com/auth/userinfo.email",
      "https://www.googleapis.com/auth/userinfo.profile"
    ]
  }
}
```

## Best Practices

1. **Clear Token Cache**: Always clear the token cache before requesting a new token to avoid using expired tokens:

```javascript
chrome.identity.clearAllCachedAuthTokens(() => {
  // Request new token
});
```

2. **Error Handling**: Implement comprehensive error handling for all authentication steps:

```javascript
try {
  // Authentication code
} catch (error) {
  console.error("Authentication error:", error);
  displayError(error.message);
}
```

3. **UI Feedback**: Provide clear feedback to the user during the authentication process:

```javascript
// Show loading state
loadingElement.classList.remove('hidden');

try {
  // Authentication code
} finally {
  // Hide loading state
  loadingElement.classList.add('hidden');
}
```

4. **Token Refresh**: Implement token refresh logic to handle expired tokens:

```javascript
async function refreshToken() {
  // Clear existing token
  await clearGoogleAuthTokens();
  
  // Get new token
  const newToken = await getGoogleToken();
  
  // Exchange for app token
  const appToken = await exchangeToken(newToken);
  
  // Update storage
  authToken = appToken;
  localStorage.setItem(USER_KEY, JSON.stringify({
    ...currentUser,
    token: appToken
  }));
}
```

## Conclusion

By following this guide, you should be able to implement a robust authentication flow for your Chrome extension using Google Sign-In. Remember to handle all edge cases and provide clear feedback to the user throughout the process.
