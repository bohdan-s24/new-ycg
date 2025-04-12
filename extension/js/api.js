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
    this.API = this.initApiEndpoints();
    
    this.store = window.YCG_STORE;
    this.retryCount = 0;
    this.maxRetries = 3;
    this.retryDelay = 1000; // 1 second
  }
  
  /**
   * Initialize API endpoints
   * @returns {Object} The API endpoints
   */
  initApiEndpoints() {
    const config = window.YCG_CONFIG;
    
    if (!config) {
      console.error('[API] YCG_CONFIG is not defined');
      return {};
    }
    
    return {
      // Base URLs
      BASE_URL: config.API_BASE_URL,
      AUTH_BASE_URL: config.AUTH_BASE_URL,
      
      // Auth endpoints
      AUTH: {
        LOGIN_GOOGLE: `${config.AUTH_BASE_URL}/login/google`,
        VERIFY_TOKEN: `${config.AUTH_BASE_URL}/verify`,
        USER_INFO: `${config.AUTH_BASE_URL}/user`,
        CONFIG: `${config.AUTH_BASE_URL}/config`
      },
      
      // Chapters endpoints
      CHAPTERS: {
        GENERATE: `${config.API_BASE_URL}/v1/chapters/generate`
      },
      
      // Credits endpoints
      CREDITS: {
        BALANCE: `${config.API_BASE_URL}/v1/credits/balance`
      },
      
      // Payment endpoints
      PAYMENT: {
        PLANS: `${config.API_BASE_URL}/v1/payment/plans`,
        CREATE_SESSION: `${config.API_BASE_URL}/v1/payment/create-session`
      },
      
      // Health check
      HEALTH: {
        PING: `${config.API_BASE_URL}/v1/health`
      }
    };
  }
  
  /**
   * Get the authentication token from the store
   * @returns {string|null} The authentication token
   */
  getToken() {
    if (!this.store) {
      console.error('[API] Store is not available');
      return null;
    }
    
    const state = this.store.getState();
    return state.auth.token;
  }
  
  /**
   * Make a network request with error handling and authentication
   * @param {string} url - The URL to request
   * @param {Object} options - The fetch options
   * @param {boolean} requiresAuth - Whether the request requires authentication
   * @returns {Promise<Object>} The response data
   */
  async request(url, options = {}, requiresAuth = false) {
    // Set default options
    const defaultOptions = {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    };
    
    // Merge options
    const mergedOptions = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers
      }
    };
    
    // Add authentication token if required
    if (requiresAuth) {
      const token = this.getToken();
      if (!token) {
        throw new Error('Authentication required but no token available');
      }
      
      mergedOptions.headers['Authorization'] = `Bearer ${token}`;
    }
    
    try {
      console.log(`[API] ${mergedOptions.method} request to ${url}`);
      
      // Make the request
      const response = await fetch(url, mergedOptions);
      
      // Handle non-JSON responses
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        if (!response.ok) {
          throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
        }
        return { success: response.ok };
      }
      
      // Parse JSON response
      const data = await response.json();
      
      // Handle API errors
      if (!response.ok) {
        const error = data.error || `HTTP Error: ${response.status}`;
        throw new Error(error);
      }
      
      return data;
    } catch (error) {
      // Handle network errors
      console.error(`[API] Error in ${url}:`, error);
      
      // Retry logic for network errors
      if (this.retryCount < this.maxRetries && this.isNetworkError(error)) {
        this.retryCount++;
        console.log(`[API] Retrying request (${this.retryCount}/${this.maxRetries})...`);
        
        // Wait before retrying
        await new Promise(resolve => setTimeout(resolve, this.retryDelay * this.retryCount));
        
        // Retry the request
        return this.request(url, options, requiresAuth);
      }
      
      // Reset retry count
      this.retryCount = 0;
      
      // Handle authentication errors
      if (this.isAuthError(error) && requiresAuth) {
        // Dispatch logout action
        if (this.store) {
          this.store.dispatch('auth', { type: 'LOGOUT' });
          
          // Save state to storage
          await this.store.saveToStorage();
        }
      }
      
      throw error;
    }
  }
  
  /**
   * Check if an error is a network error
   * @param {Error} error - The error to check
   * @returns {boolean} Whether the error is a network error
   */
  isNetworkError(error) {
    return (
      error.message.includes('Failed to fetch') ||
      error.message.includes('Network request failed') ||
      error.message.includes('network error') ||
      error.message.includes('Network Error')
    );
  }
  
  /**
   * Check if an error is an authentication error
   * @param {Error} error - The error to check
   * @returns {boolean} Whether the error is an authentication error
   */
  isAuthError(error) {
    return (
      error.message.includes('Authentication required') ||
      error.message.includes('Invalid token') ||
      error.message.includes('Token expired') ||
      error.message.includes('Unauthorized')
    );
  }
  
  /**
   * Verify a token with the server
   * @param {string} token - The token to verify
   * @returns {Promise<Object>} The verification result
   */
  async verifyToken(token) {
    return this.request(this.API.AUTH.VERIFY_TOKEN, {
      method: 'POST',
      body: JSON.stringify({ token })
    });
  }
  
  /**
   * Get the current user's information
   * @returns {Promise<Object>} The user information
   */
  async getUserInfo() {
    return this.request(this.API.AUTH.USER_INFO, {}, true);
  }
  
  /**
   * Login with Google
   * @param {string} googleToken - The Google OAuth token
   * @returns {Promise<Object>} The login result
   */
  async loginWithGoogle(googleToken) {
    return this.request(this.API.AUTH.LOGIN_GOOGLE, {
      method: 'POST',
      body: JSON.stringify({
        token: googleToken,
        platform: 'chrome_extension'
      })
    });
  }
  
  /**
   * Get the user's credit balance
   * @returns {Promise<Object>} The credit balance
   */
  async getCreditBalance() {
    return this.request(this.API.CREDITS.BALANCE, {}, true);
  }
  
  /**
   * Generate chapters for a video
   * @param {string} videoId - The YouTube video ID
   * @param {string} videoTitle - The YouTube video title
   * @returns {Promise<Object>} The generated chapters
   */
  async generateChapters(videoId, videoTitle) {
    return this.request(this.API.CHAPTERS.GENERATE, {
      method: 'POST',
      body: JSON.stringify({
        video_id: videoId,
        video_title: videoTitle
      })
    }, true);
  }
  
  /**
   * Get available payment plans
   * @returns {Promise<Object>} The payment plans
   */
  async getPaymentPlans() {
    return this.request(this.API.PAYMENT.PLANS);
  }
  
  /**
   * Create a payment session
   * @param {string} planId - The payment plan ID
   * @returns {Promise<Object>} The payment session
   */
  async createPaymentSession(planId) {
    return this.request(this.API.PAYMENT.CREATE_SESSION, {
      method: 'POST',
      body: JSON.stringify({ plan_id: planId })
    }, true);
  }
  
  /**
   * Check if the API is available
   * @returns {Promise<boolean>} Whether the API is available
   */
  async ping() {
    try {
      await this.request(this.API.HEALTH.PING);
      return true;
    } catch (error) {
      console.error('[API] Ping failed:', error);
      return false;
    }
  }
}

// Create and export the API service
document.addEventListener('DOMContentLoaded', () => {
  // Wait for the DOM to be loaded before creating the API service
  // This ensures that YCG_CONFIG and YCG_STORE are available
  if (window.YCG_CONFIG && window.YCG_STORE) {
    window.YCG_API = new ApiService();
    console.log('[API] API service initialized');
  } else {
    console.error('[API] Failed to initialize API service: YCG_CONFIG or YCG_STORE not available');
  }
});
