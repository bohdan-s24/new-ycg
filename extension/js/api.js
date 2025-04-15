/**
 * YouTube Chapter Generator API Service Module
 *
 * This module provides a centralized API service for making network requests.
 * It handles authentication, error handling, and request formatting.
 */

/**
 * API Service class for making network requests
 */
class ApiService {
  constructor() {
    // Initialize API endpoints
    this.API = this.initApiEndpoints()

    this.store = window.YCG_STORE

    // Request settings
    this.retryCount = 0
    this.maxRetries = 5 // Increased from 3
    this.retryDelay = 2000 // Increased from 1 second to 2 seconds
    this.timeout = 30000 // 30 seconds default timeout

    // Token refresh settings
    this.isRefreshing = false
    this.refreshPromise = null
    this.tokenRefreshInterval = null
    this.tokenRefreshBuffer = 5 * 60 * 1000 // Refresh token 5 minutes before expiry
    this.lastRefreshAttempt = 0 // Timestamp of last refresh attempt
    this.minRefreshInterval = 60 * 1000 // Minimum 1 minute between refresh attempts

    // Start token refresh monitoring if we have a token
    this.setupTokenRefreshMonitoring()
  }

  /**
   * Initialize API endpoints
   * @returns {Object} The API endpoints
   */
  initApiEndpoints() {
    const config = window.YCG_CONFIG

    if (!config) {
      console.error("[API] YCG_CONFIG is not defined")
      return {}
    }

    return {
      // Base URLs
      BASE_URL: config.API_BASE_URL,
      AUTH_BASE_URL: config.AUTH_BASE_URL,

      // Auth endpoints
      AUTH: {
        LOGIN_GOOGLE: `${config.AUTH_BASE_URL}/login/google`,
        VERIFY_TOKEN: `${config.AUTH_BASE_URL}/verify`,
        REFRESH_TOKEN: `${config.AUTH_BASE_URL}/refresh`,
        USER_INFO: `${config.AUTH_BASE_URL}/user`,
        CONFIG: `${config.AUTH_BASE_URL}/config`,
      },

      // Chapters endpoints
      CHAPTERS: {
        GENERATE: `${config.API_BASE_URL}/v1/chapters/generate`,
      },

      // Credits endpoints
      CREDITS: {
        BALANCE: `${config.API_BASE_URL}/v1/credits/balance`,
      },

      // Payment endpoints
      PAYMENT: {
        PLANS: `${config.API_BASE_URL}/v1/payment/plans`,
        CREATE_SESSION: `${config.API_BASE_URL}/v1/payment/create-session`,
      },

      // Health check
      HEALTH: {
        PING: `${config.API_BASE_URL}/v1/health`,
      },
    }
  }

  /**
   * Get the authentication token from the store
   * @returns {string|null} The authentication token
   */
  getToken() {
    if (!this.store) {
      console.error("[API] Store is not available")
      return null
    }

    const state = this.store.getState()
    return state.auth.token
  }

  /**
   * Make a network request with error handling and authentication
   * @param {string} url - The URL to request
   * @param {Object} options - The fetch options
   * @param {boolean} requiresAuth - Whether the request requires authentication
   * @param {number} timeout - Request timeout in milliseconds (default: 15000)
   * @param {boolean} shouldRefreshToken - Whether to attempt token refresh if needed
   * @returns {Promise<Object>} The response data
   */
  async request(url, options = {}, requiresAuth = false, timeout = 15000, shouldRefreshToken = true) {
    // Set default options
    const defaultOptions = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    }

    // Merge options
    const mergedOptions = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers,
      },
    }

    // Add authentication token if required
    if (requiresAuth) {
      // Check if token needs refresh before using it
      if (shouldRefreshToken) {
        try {
          await this.checkAndRefreshTokenIfNeeded()
        } catch (refreshError) {
          console.error(`[API] Token refresh failed:`, refreshError)
          // Continue with the current token, it might still work
        }
      }

      const token = this.getToken()
      if (!token) {
        throw new Error("Authentication required but no token available")
      }

      mergedOptions.headers["Authorization"] = `Bearer ${token}`
    }

    try {
      console.log(`[API] ${mergedOptions.method} request to ${url}`)

      // Use the class timeout if none is provided
      if (!timeout) {
        timeout = this.timeout
      }

      // Add timeout if not already set
      let timeoutId
      let controller
      if (!mergedOptions.signal) {
        controller = new AbortController()
        timeoutId = setTimeout(() => {
          console.log(`[API] Request timeout after ${timeout}ms for ${url}`)
          controller.abort(new DOMException('The operation was aborted due to timeout', 'TimeoutError'))
        }, timeout)
        mergedOptions.signal = controller.signal
      }

      // Make the request
      const response = await fetch(url, mergedOptions)

      // Clear the timeout if we set one
      if (timeoutId) {
        clearTimeout(timeoutId)
      }

      // Handle non-JSON responses
      const contentType = response.headers.get("content-type")
      if (!contentType || !contentType.includes("application/json")) {
        if (!response.ok) {
          console.error(`[API] Network error: ${response.status} ${response.statusText}`)
          throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`)
        }
        return { success: response.ok }
      }

      // Parse JSON response
      let data
      try {
        data = await response.json()
      } catch (parseError) {
        console.error(`[API] Error parsing JSON response:`, parseError)
        throw new Error(`Error parsing response: ${parseError.message}`)
      }

      // Handle API errors
      if (!response.ok) {
        const errorMessage = data.error || `HTTP Error: ${response.status}`
        console.error(`[API] API error:`, errorMessage, data)
        throw new Error(errorMessage)
      }

      console.log(`[API] Response data:`, data)
      return data
    } catch (error) {
      // Clear the timeout if we set one
      if (timeoutId) {
        clearTimeout(timeoutId)
      }

      // Classify and handle the error
      const errorType = this.classifyError(error)
      console.error(`[API] ${errorType} error in ${url}:`, error)

      // Handle based on error type
      switch (errorType) {
        case 'timeout':
          // For timeout errors, we'll retry with a longer timeout
          if (this.retryCount < this.maxRetries) {
            this.retryCount++
            console.log(`[API] Retrying timed out request (${this.retryCount}/${this.maxRetries})...`)

            // Wait before retrying with exponential backoff
            const delay = this.retryDelay * Math.pow(2, this.retryCount - 1)
            console.log(`[API] Waiting ${delay}ms before retry`)
            await new Promise((resolve) => setTimeout(resolve, delay))

            // Retry with a longer timeout
            const longerTimeout = timeout * 1.5 // Increase timeout by 50%
            return this.request(url, options, requiresAuth, longerTimeout, false) // Don't try to refresh token on retry
          }
          // Reset retry count if we're not retrying
          this.retryCount = 0
          throw new Error(`Request timed out: ${error.message || 'The operation took too long to complete'}`)

        case 'network':
          // Retry logic for network errors
          if (this.retryCount < this.maxRetries) {
            this.retryCount++
            console.log(`[API] Retrying network request (${this.retryCount}/${this.maxRetries})...`)

            // Wait before retrying with exponential backoff
            const delay = this.retryDelay * Math.pow(2, this.retryCount - 1)
            console.log(`[API] Waiting ${delay}ms before retry`)
            await new Promise((resolve) => setTimeout(resolve, delay))

            // Retry the request
            return this.request(url, options, requiresAuth, timeout, false) // Don't try to refresh token on retry
          }
          // Reset retry count if we're not retrying
          this.retryCount = 0
          throw new Error(`Network error after ${this.maxRetries} retries: ${error.message}`)

        case 'auth':
          if (requiresAuth) {
            // If token refresh failed or wasn't attempted, logout
            if (!shouldRefreshToken || url.includes('/refresh')) {
              console.log('[API] Authentication error, logging out')
              // Dispatch logout action
              if (this.store) {
                this.store.dispatch("auth", { type: "LOGOUT" })
                // Save state to storage
                await this.store.saveToStorage()
              }
              throw new Error(`Authentication failed: ${error.message}`)
            } else {
              // Try to refresh the token and retry the request
              try {
                console.log('[API] Attempting to refresh token and retry request')
                await this.refreshToken()
                // Retry the original request with the new token
                return this.request(url, options, requiresAuth, timeout, false) // Don't try to refresh token again
              } catch (refreshError) {
                console.error('[API] Token refresh failed:', refreshError)
                // Logout if refresh fails
                if (this.store) {
                  this.store.dispatch("auth", { type: "LOGOUT" })
                  await this.store.saveToStorage()
                }
                throw new Error(`Authentication failed: Unable to refresh token`)
              }
            }
          }
          throw error

        default:
          // For other errors, just throw them
          throw error
      }
    }
  }

  /**
   * Classify an error into specific types for better handling
   * @param {Error} error - The error to classify
   * @returns {string} The error type: 'network', 'auth', 'timeout', or 'unknown'
   */
  classifyError(error) {
    // Check for timeout errors
    if (error.name === 'AbortError' ||
        error.name === 'TimeoutError' ||
        (error instanceof DOMException && error.name === 'AbortError') ||
        error.message.includes('aborted') ||
        error.message.includes('timeout')) {
      return 'timeout'
    }

    // Check for network errors
    if (error.message.includes("Failed to fetch") ||
        error.message.includes("Network request failed") ||
        error.message.includes("network error") ||
        error.message.includes("Network Error") ||
        error.message.includes("net::") ||
        error.name === 'NetworkError') {
      return 'network'
    }

    // Check for authentication errors
    if (error.message.includes("Authentication required") ||
        error.message.includes("Invalid token") ||
        error.message.includes("Token expired") ||
        error.message.includes("Unauthorized") ||
        error.message.includes("Not authenticated") ||
        error.message.includes("JWT") ||
        error.message.includes("token") ||
        error.status === 401 ||
        error.status === 403) {
      return 'auth'
    }

    // Default to unknown error type
    return 'unknown'
  }

  /**
   * Parse a JWT token and return its payload
   * @param {string} token - The token to parse
   * @returns {Object|null} - The parsed token payload or null if invalid
   */
  parseToken(token) {
    if (!token) return null

    try {
      // Parse the JWT token
      const base64Url = token.split('.')[1]
      if (!base64Url) {
        console.error('[API] Invalid token format: missing payload segment')
        return null
      }

      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
      const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
      }).join(''))

      return JSON.parse(jsonPayload)
    } catch (error) {
      console.error('[API] Error parsing token:', error)
      return null
    }
  }

  /**
   * Check if a token is expired or about to expire
   * @param {string} token - The JWT token to check
   * @returns {boolean} Whether the token is expired or will expire soon
   */
  isTokenExpiredOrExpiringSoon(token) {
    if (!token) return true

    try {
      // Use the parseToken method to get the payload
      const payload = this.parseToken(token)
      if (!payload) return true

      // Check if token has expiration
      if (!payload.exp) return false

      // Get current time in seconds
      const currentTime = Math.floor(Date.now() / 1000)

      // Check if token is expired or will expire soon
      const expiresIn = payload.exp - currentTime

      // Use the tokenRefreshBuffer for determining when a token is expiring soon
      // Default to 5 minutes if not set
      const bufferInSeconds = this.tokenRefreshBuffer ? this.tokenRefreshBuffer / 1000 : 300
      const isExpiringSoon = expiresIn < bufferInSeconds

      if (isExpiringSoon) {
        const minutesLeft = Math.floor(expiresIn / 60)
        console.log(`[API] Token will expire in ${minutesLeft} minutes (${expiresIn} seconds)`)
      }

      return isExpiringSoon
    } catch (error) {
      console.error('[API] Error checking token expiration:', error)
      // If we can't parse the token, assume it's invalid
      return true
    }
  }

  /**
   * Verify a token with the server
   * @param {string} token - The token to verify
   * @returns {Promise<Object>} The verification result
   */
  async verifyToken(token) {
    try {
      console.log('[API] Verifying token...')

      // First, check if the token is valid by decoding it
      try {
        // Parse the JWT token to check if it's valid
        const base64Url = token.split('.')[1]
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
        }).join(''))

        const payload = JSON.parse(jsonPayload)

        // Check if token has expiration and is not expired
        if (payload.exp) {
          const currentTime = Math.floor(Date.now() / 1000)
          if (currentTime > payload.exp) {
            console.log('[API] Token is expired based on client-side validation')
            throw new Error('Token is expired')
          }
        }

        console.log('[API] Token is valid based on client-side validation')
      } catch (decodeError) {
        console.error('[API] Token is invalid based on client-side validation:', decodeError)
        throw new Error('Invalid token format')
      }

      // Check if token is expired or about to expire
      if (this.isTokenExpiredOrExpiringSoon(token)) {
        console.log('[API] Token is expiring soon, refreshing before verification')
        // Try to refresh the token first
        try {
          await this.refreshToken()
          // Get the new token after refresh
          token = this.getToken()
          if (!token) {
            throw new Error('No token available after refresh')
          }
        } catch (refreshError) {
          console.error('[API] Token refresh failed during verification:', refreshError)
          // Continue with verification using the original token
          // The server will reject it if it's invalid
        }
      }

      // Try to verify with the server, but don't fail if server is unavailable
      try {
        // Verify with a shorter timeout to avoid long waits
        const result = await this.request(
          this.API.AUTH.VERIFY_TOKEN,
          {
            method: "POST",
            body: JSON.stringify({ token }),
          },
          false, // Not requiring auth for this request
          5000,   // 5 second timeout - reduced further to avoid long waits
          false   // Don't try to refresh token for this request
        )

        // Check if the result has the expected format
        if (result && (result.valid || result.success || (result.data && result.data.valid))) {
          console.log('[API] Server verified token as valid')
          return result
        } else {
          console.warn('[API] Server returned unexpected response format:', result)
          // If the server response doesn't have the expected format but didn't error,
          // we'll still consider the token valid based on our client-side validation
          return { valid: true, fallback: true, serverResponse: result }
        }
      } catch (serverError) {
        // If server verification fails but client validation passed, we can still proceed
        // This handles cases where the server is down or timing out
        console.warn('[API] Server verification failed, but token appears valid:', serverError)

        // Check error type
        const errorType = this.classifyError(serverError)
        if (errorType === 'timeout' || errorType === 'network') {
          // For timeout or network errors, assume token is valid since we already validated it client-side
          console.log('[API] Using client-side validation as fallback due to server unavailability')
          return { valid: true, fallback: true }
        } else {
          // For other errors (like auth errors), the token is likely invalid
          throw serverError
        }
      }
    } catch (error) {
      console.error('[API] Token verification failed:', error)
      throw error
    }
  }

  /**
   * Get the current user's information
   * @returns {Promise<Object>} The user information
   */
  async getUserInfo() {
    try {
      console.log('[API] Getting user info...')

      // Try to get user info from server with a reasonable timeout
      const userInfo = await this.request(
        this.API.AUTH.USER_INFO,
        {},
        true, // Requires authentication
        10000, // 10 second timeout
        true   // Try to refresh token if needed
      )

      return userInfo
    } catch (error) {
      console.error('[API] Error getting user info:', error)

      // Check error type
      const errorType = this.classifyError(error)
      if (errorType === 'timeout' || errorType === 'network') {
        // For timeout or network errors, try to use cached user info
        console.log('[API] Server unavailable, trying to use cached user info')

        // Try to get user info from token
        const token = this.getToken()
        if (token) {
          try {
            // Parse the JWT token to get user info
            const base64Url = token.split('.')[1]
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
              return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
            }).join(''))

            const payload = JSON.parse(jsonPayload)

            // Extract basic user info from token
            if (payload.sub && payload.email) {
              console.log('[API] Using user info from token as fallback')
              return {
                id: payload.sub,
                email: payload.email,
                name: payload.name || payload.email.split('@')[0], // Use email username as fallback
                credits: 0, // Default to 0 credits when offline
                fallback: true // Indicate this is fallback data
              }
            }
          } catch (tokenError) {
            console.error('[API] Error extracting user info from token:', tokenError)
          }
        }
      }

      // If we can't get user info from token or it's not a network/timeout error, throw the original error
      throw error
    }
  }

  /**
   * Setup token refresh monitoring
   * This sets up a periodic check to refresh the token before it expires
   */
  setupTokenRefreshMonitoring() {
    // Get the token
    const token = this.getToken()
    if (!token) {
      console.log('[API] No token available, not setting up refresh monitoring')
      return
    }

    // Clear any existing interval
    if (this.tokenRefreshInterval) {
      clearInterval(this.tokenRefreshInterval)
    }

    // Set up a new interval to check token every 5 minutes
    // This is a good balance between keeping the token fresh and not making too many requests
    this.tokenRefreshInterval = setInterval(() => {
      this.checkAndRefreshTokenIfNeeded().catch(error => {
        console.error('[API] Background token refresh failed:', error)

        // If the error is critical, clear the interval to prevent further failures
        if (error.message && (
            error.message.includes('Invalid token') ||
            error.message.includes('No token available'))) {
          console.log('[API] Critical token error, stopping refresh monitoring')
          clearInterval(this.tokenRefreshInterval)
          this.tokenRefreshInterval = null
        }
      })
    }, 5 * 60 * 1000) // Check every 5 minutes

    console.log('[API] Token refresh monitoring started')
  }

  /**
   * Check if token needs refresh and refresh it if needed
   * @returns {Promise<void>}
   */
  async checkAndRefreshTokenIfNeeded() {
    // Get current token
    const token = this.getToken()
    if (!token) {
      throw new Error('No token available to check')
    }

    try {
      // Check if token is valid and parse expiration time
      const tokenData = this.parseToken(token)
      if (!tokenData || !tokenData.exp) {
        throw new Error('Invalid token format or missing expiration')
      }

      // Calculate time until expiration
      const now = Math.floor(Date.now() / 1000)
      const timeUntilExpiry = tokenData.exp - now
      const minutesUntilExpiry = Math.floor(timeUntilExpiry / 60)

      // Log token expiration status
      console.log(`[API] Token is valid for ${minutesUntilExpiry} more minutes`)

      // If token is expired, throw error
      if (timeUntilExpiry <= 0) {
        throw new Error('Token is expired')
      }

      // If token is about to expire (within our buffer time), refresh it
      const bufferInSeconds = this.tokenRefreshBuffer / 1000
      if (timeUntilExpiry <= bufferInSeconds) {
        console.log(`[API] Token will expire in ${minutesUntilExpiry} minutes, refreshing...`)
        await this.refreshToken()
      }
    } catch (error) {
      console.error('[API] Error checking token:', error)
      throw error
    }
  }

  /**
   * Refresh the authentication token
   * @returns {Promise<string>} The new token
   */
  async refreshToken() {
    // Check if we've attempted a refresh recently to prevent hammering the server
    const now = Date.now()
    if (now - this.lastRefreshAttempt < this.minRefreshInterval) {
      console.log(`[API] Token refresh attempted too recently, skipping (min interval: ${this.minRefreshInterval/1000}s)`)
      return null
    }

    // Update last refresh attempt timestamp
    this.lastRefreshAttempt = now

    // If already refreshing, return the existing promise
    if (this.isRefreshing && this.refreshPromise) {
      console.log('[API] Token refresh already in progress, waiting...')
      return this.refreshPromise
    }

    // Set refreshing state
    this.isRefreshing = true

    // Create a new refresh promise
    this.refreshPromise = new Promise(async (resolve, reject) => {
      try {
        console.log('[API] Refreshing token...')

        // Get current token
        const currentToken = this.getToken()
        if (!currentToken) {
          throw new Error('No token available to refresh')
        }

        // Validate token format before attempting refresh
        try {
          // Parse the JWT token to check if it's valid
          const base64Url = currentToken.split('.')[1]
          if (!base64Url) {
            throw new Error('Invalid token format')
          }
        } catch (parseError) {
          console.error('[API] Invalid token format, cannot refresh:', parseError)
          throw new Error('Invalid token format, cannot refresh')
        }

        // Call refresh endpoint with increased timeout
        const result = await this.request(
          this.API.AUTH.REFRESH_TOKEN,
          {
            method: 'POST',
            body: JSON.stringify({ token: currentToken }),
          },
          false, // Not requiring auth for this request
          30000, // 30 second timeout - increased from 20s
          false  // Don't try to refresh token for this request
        )

        // Check if we got a new token
        if (!result || !result.access_token) {
          throw new Error('Failed to refresh token: No new token returned')
        }

        console.log('[API] Token refreshed successfully')

        // Update token in store
        if (this.store) {
          const state = this.store.getState()
          this.store.dispatch('auth', {
            type: 'LOGIN_SUCCESS',
            payload: {
              user: state.auth.user,
              token: result.access_token,
            },
          })

          // Save to storage
          await this.store.saveToStorage()
        }

        resolve(result.access_token)
      } catch (error) {
        console.error('[API] Token refresh failed:', error)
        reject(error)
      } finally {
        // Reset refreshing state
        this.isRefreshing = false
        this.refreshPromise = null
      }
    })

    return this.refreshPromise
  }

  /**
   * Login with Google
   * @param {string} googleToken - The Google OAuth token
   * @returns {Promise<Object>} The login result
   */
  async loginWithGoogle(googleToken) {
    // Add retry logic specifically for login
    const maxRetries = 3
    const baseDelay = 1000 // 1 second

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        console.log(`[API] Login attempt ${attempt}/${maxRetries}`)

        // Use a longer timeout for login requests
        const controller = new AbortController()
        const timeoutId = setTimeout(() => {
          console.log('[API] Login request timed out after 20 seconds')
          controller.abort(new DOMException('Login request timed out', 'TimeoutError'))
        }, 20000) // 20 second timeout

        const result = await this.request(
          this.API.AUTH.LOGIN_GOOGLE,
          {
            method: "POST",
            body: JSON.stringify({
              token: googleToken,
              platform: "chrome_extension",
            }),
            signal: controller.signal,
          },
          false, // Not requiring auth for this request
          20000, // 20 second timeout
          false  // Don't try to refresh token for this request
        )

        clearTimeout(timeoutId)

        // Handle the nested response structure
        console.log('[API] Login response structure:', JSON.stringify(result))

        // Check if the response has a nested data structure
        if (result.success && result.data) {
          console.log('[API] Found nested data structure in login response')
          // Return the data object which contains the access_token

          // Start token refresh monitoring after successful login
          this.setupTokenRefreshMonitoring()

          return result.data
        }

        // Start token refresh monitoring after successful login
        this.setupTokenRefreshMonitoring()

        return result
      } catch (error) {
        console.error(`[API] Login attempt ${attempt} failed:`, error)

        if (attempt === maxRetries) {
          // Last attempt failed, throw the error
          throw error
        }

        // Wait before retrying with exponential backoff
        const delay = baseDelay * Math.pow(2, attempt - 1)
        console.log(`[API] Retrying login in ${delay}ms...`)
        await new Promise((resolve) => setTimeout(resolve, delay))
      }
    }
  }

  /**
   * Get the user's credit balance
   * @returns {Promise<Object>} The credit balance
   */
  async getCreditBalance() {
    return this.request(this.API.CREDITS.BALANCE, {}, true)
  }

  /**
   * Generate chapters for a video
   * @param {string} videoId - The YouTube video ID
   * @param {string} videoTitle - The YouTube video title
   * @returns {Promise<Object>} The generated chapters
   */
  async generateChapters(videoId, videoTitle) {
    return this.request(
      this.API.CHAPTERS.GENERATE,
      {
        method: "POST",
        body: JSON.stringify({
          video_id: videoId,
          video_title: videoTitle,
        }),
      },
      true,
    )
  }

  /**
   * Get available payment plans
   * @returns {Promise<Object>} The payment plans
   */
  async getPaymentPlans() {
    return this.request(this.API.PAYMENT.PLANS)
  }

  /**
   * Create a payment session
   * @param {string} planId - The payment plan ID
   * @returns {Promise<Object>} The payment session
   */
  async createPaymentSession(planId) {
    return this.request(
      this.API.PAYMENT.CREATE_SESSION,
      {
        method: "POST",
        body: JSON.stringify({ plan_id: planId }),
      },
      true,
    )
  }

  /**
   * Check if the API is available
   * @returns {Promise<boolean>} Whether the API is available
   */
  async ping() {
    try {
      await this.request(this.API.HEALTH.PING)
      return true
    } catch (error) {
      console.error("[API] Ping failed:", error)
      return false
    }
  }
}

// Create and export the API service
document.addEventListener("DOMContentLoaded", () => {
  // Wait for the DOM to be loaded before creating the API service
  // This ensures that YCG_CONFIG and YCG_STORE are available
  if (window.YCG_CONFIG && window.YCG_STORE) {
    window.YCG_API = new ApiService()
    console.log("[API] API service initialized")
  } else {
    console.error("[API] Failed to initialize API service: YCG_CONFIG or YCG_STORE not available")
  }
})
