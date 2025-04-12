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
    this.store = window.YCG_STORE
    this.lastCheckTime = 0
    this.checkInterval = 1000 // 1 second
  }

  /**
   * Initialize the video service
   */
  init() {
    console.log("[Video] Initializing video service")

    // Check for video when popup is opened
    this.checkForVideo()

    console.log("[Video] Video service initialized")
  }

  /**
   * Check if the current tab is a YouTube video page
   * @returns {Promise<void>}
   */
  async checkForVideo() {
    // Throttle checks to avoid too many messages
    const now = Date.now()
    if (now - this.lastCheckTime < this.checkInterval) {
      return
    }
    this.lastCheckTime = now

    console.log("[Video] Checking for YouTube video")

    try {
      // Query for the active tab
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true })
      const currentTab = tabs[0]

      if (!currentTab) {
        throw new Error("No active tab found")
      }

      // Check if the tab is a YouTube page
      const isYouTube = currentTab.url && currentTab.url.includes("youtube.com")

      if (!isYouTube) {
        this.store.dispatch("video", {
          type: "SET_VIDEO_ERROR",
          payload: { error: "Please navigate to a YouTube video page" },
        })
        return
      }

      // Send message to content script
      const response = await chrome.tabs.sendMessage(currentTab.id, { action: "getVideoInfo" })

      if (!response || !response.success) {
        const error = response?.error || "Failed to get video information"
        this.store.dispatch("video", {
          type: "SET_VIDEO_ERROR",
          payload: { error },
        })
        return
      }

      // Update video info in store
      this.store.dispatch("video", {
        type: "SET_VIDEO_INFO",
        payload: {
          id: response.videoId,
          title: response.videoTitle,
        },
      })

      console.log("[Video] Video found:", response.videoId, response.videoTitle)
    } catch (error) {
      console.error("[Video] Error checking for video:", error)

      // Check if this is a "Could not establish connection" error
      if (error.message.includes("Could not establish connection") || error.message.includes("Connection failed")) {
        // This is expected when not on a YouTube page
        console.log("[Video] Not on a YouTube page or content script not loaded")
        this.store.dispatch("video", {
          type: "SET_VIDEO_ERROR",
          payload: { error: "Please navigate to a YouTube video and refresh the page" },
        })
      } else {
        this.store.dispatch("video", {
          type: "SET_VIDEO_ERROR",
          payload: { error: error.message },
        })
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
      window.YCG_VIDEO = new VideoService()
      console.log("[Video] Video service created")
    } else {
      console.error("[Video] Failed to create video service: YCG_STORE not available")
    }
  } else {
    console.warn("[Video] Chrome API not available. Running outside of extension context?")
  }
})
