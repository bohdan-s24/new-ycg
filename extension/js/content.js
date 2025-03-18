// YouTube Chapter Generator Content Script
console.log('YouTube Chapter Generator: Content script loaded');

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Content script received message:', request);
  
  try {
    if (request.action === 'getVideoInfo') {
      // Extract video ID and title
      const videoId = getVideoId();
      const videoTitle = getVideoTitle();
      
      console.log('Extracted video info:', { videoId, videoTitle });
      
      if (!videoId) {
        sendResponse({ 
          success: false, 
          error: 'Could not extract video ID from the current page.' 
        });
        return true;
      }
      
      sendResponse({ 
        success: true, 
        videoId, 
        videoTitle 
      });
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

// Function to extract video ID from URL
function getVideoId() {
  try {
    const url = window.location.href;
    const urlObj = new URL(url);
    const videoId = urlObj.searchParams.get('v');
    
    if (!videoId) {
      console.error('No video ID found in URL:', url);
    }
    
    return videoId;
  } catch (error) {
    console.error('Error extracting video ID:', error);
    return null;
  }
}

// Function to extract video title
function getVideoTitle() {
  try {
    // Look for the title in different places depending on YouTube's layout
    const titleElement = document.querySelector('h1.title yt-formatted-string') ||
                        document.querySelector('h1.title') ||
                        document.querySelector('h1 .ytd-video-primary-info-renderer') ||
                        document.querySelector('h1.ytd-video-primary-info-renderer');
    
    const title = titleElement ? titleElement.textContent.trim() : 'Unknown Title';
    console.log('Extracted video title:', title);
    return title;
  } catch (error) {
    console.error('Error extracting video title:', error);
    return 'Unknown Title';
  }
} 