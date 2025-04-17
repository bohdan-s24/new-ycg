/**
 * YouTube Chapter Generator Content Script
 * 
 * This script runs in the context of YouTube pages and communicates with the popup.
 */

console.log("[Content] YouTube Chapter Generator: Content script loaded");

// Keep track of when the content script was loaded
const CONTENT_SCRIPT_LOADED_TIME = Date.now();

// Set up a ping interval to keep the message port alive (every 30 seconds)
setInterval(() => {
  console.log(`[Content] Content script alive: ${Math.floor((Date.now() - CONTENT_SCRIPT_LOADED_TIME)/1000)}s`);
}, 30000);

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("[Content] Received message:", request);
  
  try {
    if (request.action === "getVideoInfo") {
      // Extract video ID and title
      const videoInfo = getVideoInfo();
      
      console.log("[Content] Extracted video info:", videoInfo);
      
      if (!videoInfo.videoId) {
        sendResponse({ 
          success: false, 
          error: "Could not extract video ID. Make sure you are on a YouTube video page." 
        });
      } else {
        sendResponse({ 
          success: true, 
          videoId: videoInfo.videoId, 
          videoTitle: videoInfo.videoTitle 
        });
      }
    } else {
      sendResponse({ 
        success: false, 
        error: "Unknown action requested" 
      });
    }
  } catch (error) {
    console.error("[Content] Error processing message:", error);
    sendResponse({ 
      success: false, 
      error: `Error in content script: ${error.message}` 
    });
  }
  
  // Return true to indicate we'll send a response asynchronously
  return true;
});

/**
 * Extract video information from the current page
 * @returns {Object} The video ID and title
 */
function getVideoInfo() {
  try {
    // Get video ID from URL
    const url = window.location.href;
    const videoId = extractVideoId(url);
    
    // Get video title
    let videoTitle = "";
    
    // Try different methods to get the title
    // Method 1: From the page title
    const pageTitle = document.title;
    if (pageTitle && !pageTitle.includes("YouTube")) {
      videoTitle = pageTitle.replace(" - YouTube", "");
    }
    
    // Method 2: From the video element
    if (!videoTitle) {
      const titleElement = document.querySelector("h1.title.style-scope.ytd-video-primary-info-renderer");
      if (titleElement) {
        videoTitle = titleElement.textContent.trim();
      }
    }
    
    // Method 3: From meta tags
    if (!videoTitle) {
      const metaTitle = document.querySelector("meta[property=\"og:title\"]");
      if (metaTitle) {
        videoTitle = metaTitle.getAttribute("content");
      }
    }
    
    // Method 4: From structured data
    if (!videoTitle) {
      const scriptElements = document.querySelectorAll("script[type=\"application/ld+json\"]");
      for (const script of scriptElements) {
        try {
          const data = JSON.parse(script.textContent);
          if (data && data.name) {
            videoTitle = data.name;
            break;
          }
        } catch (e) {
          console.error("[Content] Error parsing JSON-LD:", e);
        }
      }
    }
    
    return {
      videoId,
      videoTitle: videoTitle || "Unknown Title"
    };
  } catch (error) {
    console.error("[Content] Error getting video info:", error);
    return {
      videoId: null,
      videoTitle: null
    };
  }
}

/**
 * Extract video ID from a YouTube URL
 * @param {string} url - The YouTube URL
 * @returns {string|null} The video ID or null if not found
 */
function extractVideoId(url) {
  try {
    // Handle different YouTube URL formats
    
    // Format: youtube.com/watch?v=VIDEO_ID
    const watchMatch = url.match(/youtube\.com\/watch\?v=([^&]+)/);
    if (watchMatch) return watchMatch[1];
    
    // Format: youtu.be/VIDEO_ID
    const shortMatch = url.match(/youtu\.be\/([^?&]+)/);
    if (shortMatch) return shortMatch[1];
    
    // Format: youtube.com/embed/VIDEO_ID
    const embedMatch = url.match(/youtube\.com\/embed\/([^?&]+)/);
    if (embedMatch) return embedMatch[1];
    
    // Format: youtube.com/v/VIDEO_ID
    const vMatch = url.match(/youtube\.com\/v\/([^?&]+)/);
    if (vMatch) return vMatch[1];
    
    return null;
  } catch (error) {
    console.error("[Content] Error extracting video ID:", error);
    return null;
  }
}
