/**
 * YouTube Chapter Generator API Service Module
 * 
 * This module provides a centralized API service for making network requests.
 * It handles authentication, error handling, and request formatting.
 */

// API endpoints
const API = {
  // Base URLs
  BASE_URL: window.YCG_CONFIG.API_BASE_URL,
  AUTH_BASE_URL: window.YCG_CONFIG.AUTH_BASE_URL,
  
  // Auth endpoints
  AUTH: {
    LOGIN_GOOGLE: `${window.YCG_CONFIG.AUTH_BASE_URL}/login/google`,
    VERIFY_TOKEN: `${window.YCG_CONFIG.AUTH_BASE_URL}/verify`,
    USER_INFO: `${window.YCG_CONFIG.AUTH_BASE_URL}/user`,
    CONFIG: `${window.YCG_CONFIG.AUTH_BASE_URL}/config`
  },
  
  // Chapters endpoints
  CHAPTERS: {
    GENERATE: `${window.YCG_CONFIG.API_BASE_URL}/chapters/generate`
  },
  
  // Credits endpoints
  CREDITS: {
    BALANCE: `${window.YCG_CONFIG.API_BASE_URL}/credits/balance`
  },
  
  // Payment endpoints
  PAYMENT: {
    PLANS: `${window.YCG_CONFIG.API_BASE_URL}/payment/plans`,
    CREATE_SESSION: `${window.YCG_CONFIG.API_BASE_URL}/payment/create-session`
  },
  
  // Health check
  HEALTH: {
    PING: `${window.YCG_CONFIG.API_BASE_URL}/health`
  }
};

/**
 * API Service class for making network requests
 */
class ApiService {
  constructor() {
    this.store = window.YCG_STORE;
    this.retryCount = 0;
    this.maxRetries = 3;
    this.retryDelay = 1000; // 1 second
  }
  
  /**
   * Get the authentication token from the store
   * @returns {string|null} The authentication token
   */
  getToken() {
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
        this.store.dispatch('auth', { type: 'LOGOUT' });
        
        // Save state to storage
        await this.store.saveToStorage();
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
    return this.request(API.AUTH.VERIFY_TOKEN, {
      method: 'POST',
      body: JSON.stringify({ token })
    });
  }
  
  /**
   * Get the current user's information
   * @returns {Promise<Object>} The user information
   */
  async getUserInfo() {
    return this.request(API.AUTH.USER_INFO, {}, true);
  }
  
  /**
   * Login with Google
   * @param {string} googleToken - The Google OAuth token
   * @returns {Promise<Object>} The login result
   */
  async loginWithGoogle(googleToken) {
    return this.request(API.AUTH.LOGIN_GOOGLE, {
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
    return this.request(API.CREDITS.BALANCE, {}, true);
  }
  
  /**
   * Generate chapters for a video
   * @param {string} videoId - The YouTube video ID
   * @param {string} videoTitle - The YouTube video title
   * @returns {Promise<Object>} The generated chapters
   */
  async generateChapters(videoId, videoTitle) {
    return this.request(API.CHAPTERS.GENERATE, {
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
    return this.request(API.PAYMENT.PLANS);
  }
  
  /**
   * Create a payment session
   * @param {string} planId - The payment plan ID
   * @returns {Promise<Object>} The payment session
   */
  async createPaymentSession(planId) {
    return this.request(API.PAYMENT.CREATE_SESSION, {
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
      await this.request(API.HEALTH.PING);
      return true;
    } catch (error) {
      console.error('[API] Ping failed:', error);
      return false;
    }
  }
}

// Create and export the API service
window.YCG_API = new ApiService();
