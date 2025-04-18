/**
 * YouTube Chapter Generator Video Service Module
 *
 * This module provides a service for interacting with YouTube videos.
 * It handles communication with the content script to get video information.
 */

/**
 * Video Service class for interacting with YouTube videos
 */
class VideoService {
  constructor() {
    this.store = window.YCG_STORE;
    this.lastCheckTime = 0;
    this.checkInterval = 1000; // 1 second
    this.isInitialized = false;
    this.authStateListener = this.handleAuthStateChange.bind(this);
  }

  /**
   * Initialize the video service
   */
  init() {
    if (this.isInitialized) {
      console.log("[Video] Video service already initialized");
      return;
    }

    console.log("[Video] Initializing video service");

    // Set up auth state change listener
    if (this.store) {
      console.log("[Video] Setting up auth state change listener");
      this.store.subscribe(this.authStateListener);
    }

    // Only check for video if user is logged in
    if (this.isUserLoggedIn()) {
      console.log("[Video] User is logged in, checking for video");
      this.checkForVideo();
    } else {
      console.log("[Video] User is not logged in, skipping video check");
    }

    this.isInitialized = true;
    console.log("[Video] Video service initialized");
  }

  /**
   * Handle auth state changes
   */
  handleAuthStateChange() {
    if (!this.store) return;

    const state = this.store.getState();
    const isLoggedIn = state && state.auth && state.auth.isAuthenticated && state.auth.token;

    // Check for video when user logs in
    if (isLoggedIn) {
      console.log("[Video] Auth state changed: User is logged in, checking for video");
      this.checkForVideo();
    } else {
      console.log("[Video] Auth state changed: User is not logged in");
    }
  }

  /**
   * Check if the user is logged in
   * @returns {boolean} Whether the user is logged in
   */
  isUserLoggedIn() {
    if (!this.store) return false;

    const state = this.store.getState();
    return state && state.auth && state.auth.isAuthenticated && state.auth.token;
  }

  /**
   * Check if the current tab is a YouTube video page
   * @returns {Promise<void>}
   */
  async checkForVideo() {
    // Throttle checks to avoid too many messages
    const now = Date.now();
    if (now - this.lastCheckTime < this.checkInterval) {
      return;
    }
    this.lastCheckTime = now;

    console.log("[Video] Checking for YouTube video");

    try {
      // Query for the active tab
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      const currentTab = tabs[0];

      if (!currentTab) {
        throw new Error("No active tab found");
      }

      // Check if the tab is a YouTube page
      const isYouTube = currentTab.url && currentTab.url.includes("youtube.com");

      if (!isYouTube) {
        this.store.dispatch("video", {
          type: "SET_VIDEO_ERROR",
          payload: { error: "Please navigate to a YouTube video page" },
        });
        return;
      }

      // Variable to store video response
      let videoResponse = null;

      // Send message to content script with timeout
      try {
        // Create a promise that will reject after a timeout
        const timeoutPromise = new Promise((_, reject) => {
          setTimeout(() => {
            reject(new Error("Content script communication timed out"));
          }, 5000); // 5 second timeout
        });

        // Create the message promise
        const messagePromise = new Promise((resolve) => {
          chrome.tabs.sendMessage(currentTab.id, { action: "getVideoInfo" }, (response) => {
            // Check for chrome runtime error
            if (chrome.runtime.lastError) {
              console.warn("[Video] Chrome runtime error:", chrome.runtime.lastError);
              resolve({ success: false, error: chrome.runtime.lastError.message });
            } else {
              resolve(response || { success: false, error: "No response from content script" });
            }
          });
        });

        // Race the message against the timeout
        videoResponse = await Promise.race([messagePromise, timeoutPromise]);

        if (!videoResponse || !videoResponse.success) {
          const error = videoResponse?.error || "Failed to get video information";
          this.store.dispatch("video", {
            type: "SET_VIDEO_ERROR",
            payload: { error },
          });
          return;
        }

        // Update video info in store
        console.log("[Video] Dispatching SET_VIDEO_INFO", videoResponse.videoId, videoResponse.videoTitle);
        this.store.dispatch("video", {
          type: "SET_VIDEO_INFO",
          payload: {
            id: videoResponse.videoId,
            title: videoResponse.videoTitle,
          },
        });
        console.log("[Video] State after dispatch:", this.store.getState().video);

        console.log("[Video] Video found:", videoResponse.videoId, videoResponse.videoTitle);
      } catch (timeoutError) {
        console.error("[Video] Content script communication error:", timeoutError);
        this.store.dispatch("video", {
          type: "SET_VIDEO_ERROR",
          payload: { error: "Communication with YouTube page timed out. Please refresh the page." },
        });
        return;
      }
    } catch (error) {
      console.error("[Video] Error checking for video:", error);

      // Check if this is a "Could not establish connection" error
      if (error.message.includes("Could not establish connection") || error.message.includes("Connection failed")) {
        // This is expected when not on a YouTube page
        console.log("[Video] Not on a YouTube page or content script not loaded");
        this.store.dispatch("video", {
          type: "SET_VIDEO_ERROR",
          payload: { error: "Please navigate to a YouTube video and refresh the page" },
        });
      } else {
        this.store.dispatch("video", {
          type: "SET_VIDEO_ERROR",
          payload: { error: error.message },
        });
      }
    }
  }
}

// Create and export the video service
document.addEventListener("DOMContentLoaded", () => {
  // Wait for the DOM to be loaded before creating the video service
  // This ensures that YCG_STORE is available
  if (typeof chrome !== "undefined" && chrome.tabs) {
    if (window.YCG_STORE) {
      window.YCG_VIDEO = new VideoService();
      console.log("[Video] Video service created");
    } else {
      console.error("[Video] Failed to create video service: YCG_STORE not available");
    }
  } else {
    console.warn("[Video] Chrome API not available. Running outside of extension context?");
  }
});
