// YouTube Chapter Generator Content Script
console.log('YouTube Chapter Generator: Content script loaded');

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Content script received message:', request);
  
  if (request.action === 'getVideoInfo') {
    // Extract video ID and title
    const videoId = getVideoId();
    const videoTitle = getVideoTitle();
    
    console.log('Extracted video info:', { videoId, videoTitle });
    sendResponse({ 
      success: true, 
      videoId, 
      videoTitle 
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
                        document.querySelector('h1 .ytd-video-primary-info-renderer');
    
    return titleElement ? titleElement.textContent.trim() : 'Unknown Title';
  } catch (error) {
    console.error('Error extracting video title:', error);
    return 'Unknown Title';
  }
} 