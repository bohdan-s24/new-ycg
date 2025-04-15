/**
 * YouTube Chapter Generator Authentication Module
 *
 * This module handles user authentication using Google OAuth.
 */

// Initialize auth when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  console.log("[AUTH-DEBUG] DOM content loaded, checking for store and API")

  // Try to initialize with increasing delays
  const tryInit = (attempt = 1, maxAttempts = 5) => {
    console.log(`[AUTH-DEBUG] Auth initialization attempt ${attempt}/${maxAttempts}`)

    // Check if store is available (API is optional)
    if (window.YCG_STORE) {
      console.log("[AUTH-DEBUG] Store available, initializing auth")
      // Initialize with whatever services are available
      initAuth()
      return
    }

    if (attempt < maxAttempts) {
      const delay = 100 * Math.pow(2, attempt - 1) // Exponential backoff
      console.log(`[AUTH-DEBUG] Services not ready, retrying auth init in ${delay}ms`)
      setTimeout(() => tryInit(attempt + 1, maxAttempts), delay)
    } else {
      console.error("[AUTH-DEBUG] Failed to initialize auth after multiple attempts")
      console.log(
        "[AUTH-DEBUG] Available globals:",
        Object.keys(window).filter((key) => key.startsWith("YCG_")),
      )
    }
  }

  // Start initialization attempts
  tryInit()
})

/**
 * Initialize authentication
 */
async function initAuth() {
  console.log("[Auth] Initializing auth...")

  // Get references to the store and API
  const store = window.YCG_STORE
  const api = window.YCG_API

  // Check if API is available
  if (!api) {
    console.warn("[Auth] API service not available, limited functionality")
    // Initialize Google Sign-In even without API
    initGoogleSignIn()
    return
  }

  // Load state from storage
  const loadSuccess = await store.loadFromStorage()
  if (!loadSuccess) {
    console.warn("[Auth] Failed to load state from storage, starting fresh")
  }

  // Check if we have a token and verify it
  const state = store.getState()
  if (state.auth.token) {
    console.log("[Auth] Found token in storage, verifying...")

    try {
      // First, validate the token locally to avoid unnecessary server calls
      const isTokenValid = api.parseToken(state.auth.token) !== null;
      if (!isTokenValid) {
        console.log("[Auth] Token is invalid based on local validation")
        throw new Error("Invalid token format")
      }

      // Check if token is expired
      const isTokenExpired = api.isTokenExpiredOrExpiringSoon(state.auth.token);
      if (isTokenExpired) {
        console.log("[Auth] Token is expired or expiring soon")
        throw new Error("Token is expired")
      }

      console.log("[Auth] Token is valid based on local validation")

      // Try to verify with server, but don't fail if server is unavailable
      try {
        // Verify token with server with a short timeout
        console.log("[AUTH-DEBUG] Sending token verification request")
        const result = await Promise.race([
          api.verifyToken(state.auth.token),
          new Promise((_, reject) => setTimeout(() => reject(new Error("Verification timeout")), 5000))
        ]);

        console.log("[AUTH-DEBUG] Token verification response:", result)

        // Check if the result is valid
        const isValid =
          (result && (result.valid || result.fallback)) || // Direct format
          (result && result.data && (result.data.valid || result.data.fallback)) || // Nested format
          (result && result.success === true); // Success format

        if (isValid) {
          console.log(result.fallback || (result.data && result.data.fallback)
            ? "[Auth] Token is valid (using client-side validation due to server unavailability)"
            : "[Auth] Token is valid according to server")
        } else {
          console.log("[Auth] Token is invalid according to server")
          throw new Error("Invalid token according to server")
        }
      } catch (verifyError) {
        // If server verification fails, log but continue with local validation
        console.warn("[Auth] Server verification failed, continuing with local validation:", verifyError)
      }

      // Get user info - try server first, then fallback to cached data
      let userInfo;
      try {
        console.log("[AUTH-DEBUG] Fetching user info")
        userInfo = await Promise.race([
          api.getUserInfo(),
          new Promise((_, reject) => setTimeout(() => reject(new Error("User info timeout")), 5000))
        ]);
        console.log("[AUTH-DEBUG] User info received from server:", userInfo ? 'success' : 'failed')
      } catch (userInfoError) {
        console.warn("[Auth] Error getting user info from server, using cached data:", userInfoError)

        // Try to get user info from cached state
        if (state.auth.user) {
          userInfo = state.auth.user;
          console.log("[AUTH-DEBUG] Using cached user info")
        } else {
          // If no cached user info, try to extract from token
          userInfo = api.extractUserInfoFromToken();
          if (userInfo) {
            console.log("[AUTH-DEBUG] Using user info extracted from token")
          } else {
            console.error("[Auth] No user info available")
            throw new Error("No user info available")
          }
        }
      }

      // Update user in store
      store.dispatch("auth", {
        type: "LOGIN_SUCCESS",
        payload: {
          user: userInfo,
          token: state.auth.token,
        },
      })

      // Update credits - extract from the correct location in the response
      const creditsCount = userInfo && userInfo.data && userInfo.data.credits ?
        userInfo.data.credits :
        (userInfo && userInfo.credits ? userInfo.credits : 0);

      console.log("[AUTH-DEBUG] Setting credits count to:", creditsCount);

      store.dispatch("credits", {
        type: "SET_CREDITS",
        payload: {
          count: creditsCount,
        },
      })

      // Set active view to main
      store.dispatch("ui", {
        type: "SET_ACTIVE_VIEW",
        payload: { view: "main" },
      })

      // Save state to storage
      const saveSuccess = await store.saveToStorage()
      if (!saveSuccess) {
        console.warn("[Auth] Failed to save state to storage")
      }
    } catch (error) {
      console.error("[Auth] Error verifying token:", error)
      handleAuthError(store, error)
    }
  } else {
    console.log("[Auth] No token found in storage")

    // Initialize Google Sign-In
    initGoogleSignIn()
  }

  // Set up event listeners
  setupAuthEventListeners()

  console.log("[Auth] Initialization complete")
}

/**
 * Initialize Google Sign-In
 */
function initGoogleSignIn() {
  console.log("[Auth] Initializing Google Sign-In...")

  // Create Google Sign-In buttons
  const createGoogleButton = () => {
    const button = document.createElement("button")
    button.type = "button"
    button.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" style="margin-right: 8px;">
        <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z"/>
        <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/>
        <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/>
        <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"/>
      </svg>
      Continue with Google
    `
    button.className = "google-signin-btn-dynamic"
    button.addEventListener("click", handleGoogleSignIn)
    return button
  }

  // Add buttons to the DOM
  const googleSignInButton1 = document.getElementById("google-signin-button")
  const googleSignInButton2 = document.getElementById("google-signin-button-auth")

  if (googleSignInButton1) {
    googleSignInButton1.innerHTML = ""
    googleSignInButton1.appendChild(createGoogleButton())
  }

  if (googleSignInButton2) {
    googleSignInButton2.innerHTML = ""
    googleSignInButton2.appendChild(createGoogleButton())
  }
}

/**
 * Set up authentication event listeners
 */
function setupAuthEventListeners() {
  // Get references to the store and UI
  const store = window.YCG_STORE

  // Login button
  const loginBtn = document.getElementById("login-btn")
  if (loginBtn) {
    loginBtn.addEventListener("click", () => {
      store.dispatch("ui", {
        type: "SET_ACTIVE_VIEW",
        payload: { view: "auth" },
      })
    })
  }
}

/**
 * Handle Google Sign-In button click
 */
async function handleGoogleSignIn() {
  console.log("[AUTH-DEBUG] Google Sign-In button clicked")

  // Get references to the store and API
  const store = window.YCG_STORE
  const api = window.YCG_API

  console.log("[AUTH-DEBUG] Store available:", !!store)
  console.log("[AUTH-DEBUG] API available:", !!api)

  if (!store) {
    console.error("[Auth] Store not available")

    if (window.YCG_UI) {
      window.YCG_UI.showNotification("Authentication service not available", "error")
    }
    return
  }

  // If API is not available, show a message
  if (!api) {
    console.warn("[Auth] API not available, showing message to user")

    if (window.YCG_UI) {
      window.YCG_UI.showNotification("Server is not available. Please try again later.", "error")
    }
    return
  }

  // Dispatch login start action
  console.log('[AUTH-DEBUG] Dispatching LOGIN_START action')
  store.dispatch("auth", { type: "LOGIN_START" })

  // Debug: Log current state
  console.log('[AUTH-DEBUG] Current state after LOGIN_START:', JSON.stringify(store.getState().auth))

  try {
    // Show loading notification
    if (window.YCG_UI) {
      window.YCG_UI.showNotification("Connecting to Google...", "info")
    }

    // Launch Google Sign-In with timeout
    const googleSignInPromise = launchGoogleSignIn()
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => {
        reject(new Error("Google Sign-In timed out after 20 seconds"))
      }, 20000) // 20 second timeout
    })

    const token = await Promise.race([googleSignInPromise, timeoutPromise])

    if (!token) {
      throw new Error("Failed to get Google token")
    }

    console.log("[Auth] Got Google token, logging in...")

    // Show login in progress notification
    if (window.YCG_UI) {
      window.YCG_UI.showNotification("Logging in...", "info")
    }

    // Login with Google
    console.log('[AUTH-DEBUG] Calling API loginWithGoogle')
    const loginResult = await api.loginWithGoogle(token)

    console.log('[AUTH-DEBUG] Login API call completed, result:', loginResult ? 'success' : 'null/undefined')
    console.log('[AUTH-DEBUG] Login result structure:', JSON.stringify(loginResult))

    if (!loginResult) {
      throw new Error("Failed to login with Google: No response from server")
    }

    // Check for access_token in the response
    if (!loginResult.access_token) {
      console.error('[AUTH-DEBUG] Login result missing access_token:', loginResult)
      throw new Error("Failed to login with Google: No access token returned")
    }

    console.log("[AUTH-DEBUG] Login successful with token:", loginResult.access_token.substring(0, 10) + '...')

    // Log extracted user info
    console.log("[AUTH-DEBUG] Extracted user info:", {
      user_id: loginResult.user_id,
      email: loginResult.email,
      name: loginResult.name,
      picture: loginResult.picture ? 'present' : 'missing',
      credits: loginResult.credits
    });

    console.log("[AUTH-DEBUG] Login result details:", {
      access_token: loginResult.access_token ? `${loginResult.access_token.substring(0, 10)}...` : null,
      user_id: loginResult.user_id,
      email: loginResult.email,
      name: loginResult.name,
      picture: loginResult.picture ? 'present' : 'missing',
      credits: loginResult.credits
    })

    // Extract user info and token
    const { access_token, user_id, email, name, picture, credits } = loginResult

    // Update auth state
    store.dispatch("auth", {
      type: "LOGIN_SUCCESS",
      payload: {
        user: {
          id: user_id,
          email,
          name,
          picture,
        },
        token: access_token,
      },
    })

    // Update credits
    store.dispatch("credits", {
      type: "SET_CREDITS",
      payload: {
        count: credits || 0,
      },
    })

    // Set active view to main
    store.dispatch("ui", {
      type: "SET_ACTIVE_VIEW",
      payload: { view: "main" },
    })

    // Save state to storage
    await store.saveToStorage()

    // Show success notification
    if (window.YCG_UI) {
      window.YCG_UI.showNotification("Successfully logged in!", "success")
    }

    // Force UI update
    if (window.YCG_UI) {
      window.YCG_UI.updateUI(store.getState())
    }
  } catch (error) {
    console.error("[AUTH-DEBUG] Error during Google Sign-In:", error)
    console.log("[AUTH-DEBUG] Error details:", error)

    // Handle the error
    handleAuthError(store, error)

    // Show error notification
    if (window.YCG_UI) {
      window.YCG_UI.showNotification(`Login failed: ${error.message}`, "error")
    }

    // Force UI update
    if (window.YCG_UI) {
      window.YCG_UI.updateUI(store.getState())
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
      console.log("[Auth] Requesting Google auth token...")

      // Check if chrome is defined
      if (typeof chrome === "undefined" || !chrome.identity) {
        console.error("[Auth] Chrome identity API not available.")
        reject(new Error("Chrome identity API not available."))
        return
      }

      // Set a timeout for the entire operation
      const timeoutId = setTimeout(() => {
        console.error("[Auth] Google auth token request timed out")
        reject(new Error("Google authentication timed out"))
      }, 15000) // 15 second timeout

      // First try to clear any cached tokens
      chrome.identity.clearAllCachedAuthTokens(() => {
        console.log("[Auth] Cleared cached tokens")

        // Now get a fresh token
        chrome.identity.getAuthToken({ interactive: true }, (token) => {
          // Clear the timeout since we got a response
          clearTimeout(timeoutId)

          if (chrome.runtime.lastError) {
            console.error("[Auth] Chrome identity error:", chrome.runtime.lastError)
            reject(new Error(chrome.runtime.lastError.message))
            return
          }

          if (!token) {
            console.error("[Auth] No token returned from Google")
            reject(new Error("Failed to get auth token"))
            return
          }

          console.log("[Auth] Got Google auth token:", token.substring(0, 10) + "...")
          resolve(token)
        })
      })
    } catch (error) {
      console.error("[Auth] Error in launchGoogleSignIn:", error)
      reject(error)
    }
  })
}

/**
 * Handle authentication error
 * @param {Object} store - The state store
 * @param {Error} error - The error object
 */
function handleAuthError(store, error) {
  console.error("[AUTH-DEBUG] Authentication error:", error)
  console.log("[AUTH-DEBUG] Error details:", error)

  // Format error message for user display
  let userErrorMessage = "Authentication failed"

  // Classify the error for better user feedback
  if (error.message.includes("timed out") || error.message.includes("aborted")) {
    userErrorMessage = "Connection timed out. Please try again."
  } else if (error.message.includes("network") || error.message.includes("fetch")) {
    userErrorMessage = "Network error. Please check your connection and try again."
  } else if (error.message.includes("token") || error.message.includes("auth")) {
    userErrorMessage = "Authentication error. Please try logging in again."
  } else if (error.message.includes("Chrome identity") || error.message.includes("Google")) {
    userErrorMessage = "Google authentication error. Please try again."
  } else {
    // Use the original error message if it's user-friendly, otherwise use generic message
    userErrorMessage = error.message.length < 100 ? error.message : "Authentication failed. Please try again."
  }

  // Debug: Log state before error handling
  console.log('[AUTH-DEBUG] State before error handling:', {
    auth: store.getState().auth.isAuthenticated,
    view: store.getState().ui.activeView
  })

  // Dispatch login failure action with user-friendly error message
  console.log('[AUTH-DEBUG] Dispatching LOGIN_FAILURE action')
  store.dispatch("auth", {
    type: "LOGIN_FAILURE",
    payload: {
      error: userErrorMessage,
    },
  })

  // Set active view to welcome
  console.log('[AUTH-DEBUG] Dispatching SET_ACTIVE_VIEW action to show welcome view')
  store.dispatch("ui", {
    type: "SET_ACTIVE_VIEW",
    payload: { view: "welcome" },
  })

  // Debug: Log state after dispatching actions
  console.log('[AUTH-DEBUG] State after dispatching actions:', {
    auth: store.getState().auth.isAuthenticated,
    view: store.getState().ui.activeView
  })

  // Save state to storage
  console.log('[AUTH-DEBUG] Saving state to storage')
  store.saveToStorage()
  console.log('[AUTH-DEBUG] State saved to storage')

  // Debug: Log state after error
  console.log('[AUTH-DEBUG] State after error:', {
    auth: store.getState().auth,
    view: store.getState().ui.activeView
  })

  // Show error notification
  console.log('[AUTH-DEBUG] Showing error notification')
  if (window.YCG_UI) {
    window.YCG_UI.showNotification(`Authentication error: ${error.message}`, "error")
  }

  // Force UI update after error
  console.log('[AUTH-DEBUG] Forcing UI update after error')
  if (window.YCG_UI) {
    window.YCG_UI.updateUI(store.getState())
  }
}
