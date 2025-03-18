// YouTube Chapter Generator Popup Script

// API endpoints
const API_BASE_URL = 'https://new-ycg.vercel.app/api';
const GENERATE_CHAPTERS_ENDPOINT = `${API_BASE_URL}/generate-chapters`;
const PING_ENDPOINT = `${API_BASE_URL}`;

// Elements
const statusElement = document.getElementById('status');
const videoInfoElement = document.getElementById('video-info');
const videoTitleElement = document.getElementById('video-title');
const videoIdElement = document.getElementById('video-id');
const errorMessageElement = document.getElementById('error-message');
const generateButton = document.getElementById('generate-btn');
const loadingElement = document.getElementById('loading');
const chaptersContainerElement = document.getElementById('chapters-container');
const chaptersContentElement = document.getElementById('chapters-content');
const copyButton = document.getElementById('copy-btn');
const regenerateButton = document.getElementById('regenerate-btn');
const debugInfoElement = document.getElementById('debug-info');
const debugTitleElement = document.getElementById('debug-title');
const debugContentElement = document.getElementById('debug-content');

// State variables
let currentVideoId = null;
let currentVideoTitle = null;
let isGenerating = false;
let debugInfo = [];

// Initialize
document.addEventListener('DOMContentLoaded', init);

function init() {
  // Set up event listeners
  generateButton.addEventListener('click', handleGenerateClick);
  copyButton.addEventListener('click', handleCopyClick);
  regenerateButton.addEventListener('click', handleRegenerateClick);
  
  // Set up debug section toggle
  if (debugTitleElement) {
    debugTitleElement.addEventListener('click', function() {
      if (debugContentElement) {
        debugContentElement.classList.toggle('visible');
      }
    });
  }
  
  // Check API server status first
  checkApiStatus()
    .then(() => {
      // Check if we're on a YouTube video page
      getCurrentTabInfo();
    })
    .catch(error => {
      showError(`API server is not accessible: ${error.message}. Please check your internet connection and the server status.`);
    });
}

// Check API server status
async function checkApiStatus() {
  try {
    addDebugInfo('Checking API status...');
    
    const response = await fetch(PING_ENDPOINT, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API server returned status ${response.status}: ${errorText}`);
    }
    
    const data = await response.json();
    addDebugInfo(`API server is online. CORS headers configured: ${JSON.stringify(data.cors_headers || {})}`);
    addDebugInfo(`Webshare proxy status: ${JSON.stringify(data.proxy_status || {})}`);
    
    return data;
  } catch (error) {
    addDebugInfo(`API status check failed: ${error.message}`);
    throw error;
  }
}

// Get information about the current tab
function getCurrentTabInfo() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const currentTab = tabs[0];
    
    if (!currentTab || !currentTab.url || !currentTab.url.includes('youtube.com/watch')) {
      showError('Please open a YouTube video page to use this extension.');
      return;
    }
    
    // Send message to content script to get video info
    try {
      addDebugInfo(`Requesting video info from tab ${currentTab.id}`);
      chrome.tabs.sendMessage(currentTab.id, { action: 'getVideoInfo' }, (response) => {
        if (chrome.runtime.lastError) {
          console.error('Error sending message:', chrome.runtime.lastError.message);
          addDebugInfo(`Communication error: ${chrome.runtime.lastError.message}`);
          showError('Could not communicate with YouTube page. Please refresh the page and try again.');
          return;
        }
        
        if (response && response.success) {
          addDebugInfo(`Received video info: ID=${response.videoId}, title="${response.videoTitle?.substring(0, 30)}..."`);
          handleVideoInfo(response.videoId, response.videoTitle);
        } else {
          addDebugInfo(`Failed to get video info: ${response?.error || 'Unknown error'}`);
          showError('Could not extract video information. Please make sure you are on a YouTube video page.');
        }
      });
    } catch (error) {
      console.error('Error in getCurrentTabInfo:', error);
      addDebugInfo(`Unexpected error: ${error.message}`);
      showError('An unexpected error occurred. Please refresh the page and try again.');
    }
  });
}

// Handle the video information received from content script
function handleVideoInfo(videoId, videoTitle) {
  if (!videoId) {
    showError('Could not determine the video ID. Please make sure you are on a YouTube video page.');
    return;
  }
  
  currentVideoId = videoId;
  currentVideoTitle = videoTitle || 'Unknown Title';
  
  // Update UI
  statusElement.classList.add('hidden');
  videoInfoElement.classList.remove('hidden');
  videoTitleElement.textContent = currentVideoTitle;
  videoIdElement.textContent = `Video ID: ${currentVideoId}`;
  generateButton.disabled = false;
}

// Generate chapters
async function generateChapters() {
  if (!currentVideoId || isGenerating) return;
  
  isGenerating = true;
  
  // Update UI
  showLoading(true);
  hideError();
  
  try {
    addDebugInfo(`Sending request to generate chapters for video ID: ${currentVideoId}`);
    
    // First check API status
    await checkApiStatus();
    
    // Try first with standard fetch
    try {
      addDebugInfo(`Fetch request to ${GENERATE_CHAPTERS_ENDPOINT} with video_id=${currentVideoId}`);
      
      const response = await fetch(GENERATE_CHAPTERS_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          video_id: currentVideoId
        }),
      });
      
      addDebugInfo(`Response status: ${response.status} ${response.statusText}`);
      
      // Log response headers for debugging
      const responseHeaders = {};
      response.headers.forEach((value, key) => {
        responseHeaders[key] = value;
      });
      addDebugInfo(`Response headers: ${JSON.stringify(responseHeaders)}`);
      
      if (!response.ok) {
        let errorDetail;
        try {
          const errorJson = await response.json();
          errorDetail = errorJson.error || `HTTP ${response.status}`;
          addDebugInfo(`Error response JSON: ${JSON.stringify(errorJson)}`);
        } catch {
          const text = await response.text();
          errorDetail = text || `HTTP ${response.status}`;
          addDebugInfo(`Error response text: ${text}`);
        }
        
        throw new Error(`Server error: ${errorDetail}`);
      }
      
      const data = await response.json();
      addDebugInfo(`Success response: ${JSON.stringify(data, null, 2).substring(0, 200)}...`);
      
      if (data.success) {
        displayChapters(data.chapters);
        addDebugInfo(`Chapters generated successfully. Video duration: ${data.video_duration}, used proxy: ${data.used_proxy}`);
      } else {
        throw new Error(data.error || 'Unknown error');
      }
    } catch (fetchError) {
      // Check if this is a CORS error
      if (fetchError.message.includes('CORS') || 
          fetchError.name === 'TypeError' && fetchError.message.includes('Failed to fetch')) {
        
        addDebugInfo(`CORS error detected: ${fetchError.message}`);
        
        // Try direct API ping to diagnose connectivity
        try {
          await fetch(PING_ENDPOINT, { 
            method: 'GET',
            mode: 'no-cors' // This will succeed if the server is accessible
          });
          
          addDebugInfo('API server is reachable with no-cors mode');
          throw new Error(`CORS issue detected. The server is running but cannot accept cross-origin requests from this extension.`);
        } catch (pingError) {
          // If this fails too, the server is likely down
          addDebugInfo(`API ping failed: ${pingError.message}`);
          throw new Error(`Cannot connect to API server. Please check if the server is running.`);
        }
      }
      
      // Not a CORS issue or couldn't diagnose further
      throw fetchError;
    }
  } catch (error) {
    console.error('Error generating chapters:', error);
    addDebugInfo(`Final error: ${error.message}`);
    
    if (error.message.includes('CORS')) {
      showError(`CORS error: The server is not properly configured to accept requests from this extension. Please check the server deployment.`);
    } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
      showError(`Network error: Cannot connect to the API server. Please check your internet connection and server status.`);
    } else if (error.message.includes('Transcript is not available') || error.message.includes('Could not find the transcript')) {
      showError(`No transcript available for this video. The video might not have captions, or YouTube might be blocking access.`);
    } else {
      showError(`Failed to generate chapters: ${error.message}`);
    }
  } finally {
    showLoading(false);
    isGenerating = false;
  }
}

// Display the generated chapters
function displayChapters(chapters) {
  chaptersContentElement.textContent = chapters;
  chaptersContainerElement.classList.remove('hidden');
}

// Copy chapters to clipboard
function copyToClipboard(text) {
  navigator.clipboard.writeText(text)
    .then(() => {
      // Show temporary "Copied!" feedback
      const originalText = copyButton.textContent;
      copyButton.innerHTML = '<span class="btn-icon">✓</span> Copied!';
      
      setTimeout(() => {
        copyButton.innerHTML = originalText;
      }, 2000);
    })
    .catch(err => {
      console.error('Failed to copy:', err);
      addDebugInfo(`Copy error: ${err.message}`);
      showError('Failed to copy to clipboard. Please try again.');
    });
}

// Add debug information
function addDebugInfo(info) {
  const timestamp = new Date().toLocaleTimeString();
  const logEntry = `[${timestamp}] ${info}`;
  
  console.log(logEntry);
  debugInfo.push(logEntry);
  
  // Limit debug info to prevent excessive memory usage
  if (debugInfo.length > 50) {
    debugInfo.shift();
  }
  
  // Update debug info element if it exists
  if (debugInfoElement) {
    debugInfoElement.textContent = debugInfo.join('\n');
  }
}

// Show/hide loading state
function showLoading(show) {
  if (show) {
    loadingElement.classList.remove('hidden');
    generateButton.disabled = true;
  } else {
    loadingElement.classList.add('hidden');
    generateButton.disabled = false;
  }
}

// Show error message
function showError(message) {
  errorMessageElement.textContent = message;
  errorMessageElement.classList.remove('hidden');
  statusElement.classList.add('hidden');
  addDebugInfo(`Error displayed: ${message}`);
}

// Hide error message
function hideError() {
  errorMessageElement.classList.add('hidden');
}

// Event Handlers
function handleGenerateClick() {
  chaptersContainerElement.classList.add('hidden');
  generateChapters();
}

function handleCopyClick() {
  copyToClipboard(chaptersContentElement.textContent);
}

function handleRegenerateClick() {
  chaptersContainerElement.classList.add('hidden');
  generateChapters();
} 