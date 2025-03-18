// YouTube Chapter Generator Content Script
console.log('YouTube Chapter Generator: Content script loaded');

// Keep track of when the content script was loaded
const CONTENT_SCRIPT_LOADED_TIME = Date.now();

// Set up a ping interval to keep the message port alive
setInterval(() => {
  // Just log to keep the connection open
  console.log(`Content script alive: ${Math.floor((Date.now() - CONTENT_SCRIPT_LOADED_TIME)/1000)}s`);
}, 10000);

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Content script received message:', request);
  
  try {
    if (request.action === 'getVideoInfo') {
      // Extract video ID and title
      const videoInfo = getVideoInfo();
      
      console.log('Extracted video info:', videoInfo);
      
      if (!videoInfo.videoId) {
        sendResponse({ 
          success: false, 
          error: 'Could not extract video ID from the current page.' 
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
        error: 'Unknown action requested' 
      });
    }
  } catch (error) {
    console.error('Error processing message:', error);
    sendResponse({ 
      success: false, 
      error: `Error in content script: ${error.message}` 
    });
  }
  
  // Need to return true to indicate we'll send a response asynchronously
  return true;
});

// Function to extract all video information
function getVideoInfo() {
  try {
    // Get the video ID using multiple methods
    const videoId = getVideoId();
    
    // Get the video title
    const videoTitle = getVideoTitle();
    
    return {
      videoId,
      videoTitle,
      url: window.location.href,
      timestamp: Date.now()
    };
  } catch (error) {
    console.error('Error getting video info:', error);
    return {
      videoId: null,
      videoTitle: 'Unknown Title',
      error: error.message
    };
  }
}

// Function to extract video ID from URL
function getVideoId() {
  try {
    // Method 1: Extract from URL
    const url = window.location.href;
    const urlObj = new URL(url);
    const videoId = urlObj.searchParams.get('v');
    
    if (videoId) {
      return videoId;
    }
    
    // Method 2: Try to extract from various elements in the page
    const videoElement = document.querySelector('ytd-watch-flexy');
    if (videoElement && videoElement.getAttribute('video-id')) {
      return videoElement.getAttribute('video-id');
    }
    
    // Method 3: Try to get from canonical link
    const canonicalLink = document.querySelector('link[rel="canonical"]');
    if (canonicalLink) {
      const canonicalUrl = new URL(canonicalLink.href);
      const idFromCanonical = canonicalUrl.searchParams.get('v');
      if (idFromCanonical) {
        return idFromCanonical;
      }
      
      // Check if it's in path format
      const matches = canonicalLink.href.match(/youtube\.com\/watch\/([a-zA-Z0-9_-]+)/);
      if (matches && matches[1]) {
        return matches[1];
      }
    }
    
    // Method 4: Try to extract from page content
    const ytInitialData = window.ytInitialData || {};
    if (ytInitialData && ytInitialData.currentVideoEndpoint && ytInitialData.currentVideoEndpoint.watchEndpoint) {
      return ytInitialData.currentVideoEndpoint.watchEndpoint.videoId;
    }
    
    console.error('No video ID found in URL or page content');
    return null;
  } catch (error) {
    console.error('Error extracting video ID:', error);
    return null;
  }
}

// Function to extract video title
function getVideoTitle() {
  try {
    // Method 1: Look for the title in different places depending on YouTube's layout
    const titleSelectors = [
      'h1.title yt-formatted-string',
      'h1.title',
      'h1 .ytd-video-primary-info-renderer',
      'h1.ytd-video-primary-info-renderer',
      '#title h1',
      '#title .ytd-video-primary-info-renderer',
      '#container h1'
    ];
    
    for (const selector of titleSelectors) {
      const element = document.querySelector(selector);
      if (element && element.textContent.trim()) {
        return element.textContent.trim();
      }
    }
    
    // Method 2: Try to get from document title
    if (document.title && document.title.includes(' - YouTube')) {
      return document.title.replace(' - YouTube', '');
    }
    
    // Method 3: Try to get from ytInitialData
    const ytInitialData = window.ytInitialData || {};
    if (ytInitialData && 
        ytInitialData.contents && 
        ytInitialData.contents.twoColumnWatchNextResults &&
        ytInitialData.contents.twoColumnWatchNextResults.results &&
        ytInitialData.contents.twoColumnWatchNextResults.results.results &&
        ytInitialData.contents.twoColumnWatchNextResults.results.results.contents) {
      
      const contents = ytInitialData.contents.twoColumnWatchNextResults.results.results.contents;
      for (const content of contents) {
        if (content.videoPrimaryInfoRenderer && content.videoPrimaryInfoRenderer.title) {
          const title = content.videoPrimaryInfoRenderer.title.runs[0].text;
          if (title) return title;
        }
      }
    }
    
    console.warn('Could not find video title using common selectors');
    return 'Unknown Title';
  } catch (error) {
    console.error('Error extracting video title:', error);
    return 'Unknown Title';
  }
} 