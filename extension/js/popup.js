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
  
  // Make debug panel visible by default to help diagnose issues
  if (debugContentElement) {
    debugContentElement.classList.add('visible');
  }
  
  // Check API server status first
  checkApiStatus()
    .then(() => {
      // Check if we're on a YouTube video page
      getCurrentTabInfo();
    })
    .catch(error => {
      addDebugInfo(`API status check failed with error: ${error.message}`);
      // Continue anyway to allow diagnostics
      getCurrentTabInfo();
      showError(`API server may have issues: ${error.message}. You can still try to generate chapters.`);
    });
}

// Check API server status
async function checkApiStatus() {
  try {
    addDebugInfo('Checking API status...');
    
    // Add cache buster to prevent caching
    const cacheBuster = Date.now();
    const response = await fetch(`${PING_ENDPOINT}?_=${cacheBuster}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    });
    
    let responseData;
    try {
      responseData = await response.json();
    } catch (jsonError) {
      addDebugInfo(`Failed to parse API response as JSON: ${jsonError.message}`);
      throw new Error(`API returned invalid JSON. Response status: ${response.status}`);
    }
    
    // Even if status code is not OK, check if we got a valid response with error info
    if (responseData) {
      if (responseData.status === 'error') {
        addDebugInfo(`API returned error status: ${JSON.stringify(responseData)}`);
        throw new Error(`API error: ${responseData.error || responseData.message || 'Unknown error'}`);
      }
      
      if (!response.ok) {
        addDebugInfo(`API server returned status ${response.status} but with parseable data: ${JSON.stringify(responseData)}`);
        throw new Error(`API server returned status ${response.status}: ${JSON.stringify(responseData.error || {})}`);
      }
      
      // Success case
      addDebugInfo(`API server is online. Status: ${responseData.status}`);
      if (responseData.cors_headers) {
        addDebugInfo(`CORS headers configured: ${JSON.stringify(responseData.cors_headers || {})}`);
      }
      if (responseData.proxy_status) {
        addDebugInfo(`Webshare proxy status: ${JSON.stringify(responseData.proxy_status || {})}`);
      }
      if (responseData.env_info) {
        addDebugInfo(`Environment info: ${JSON.stringify(responseData.env_info || {})}`);
      }
      
      return responseData;
    } else {
      throw new Error(`API server returned status ${response.status} with no valid data`);
    }
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
async function generateChapters(forceRefresh = false) {
  if (!currentVideoId) {
    showError('No YouTube video ID found.');
    return;
  }
  
  if (isGenerating) {
    addDebugInfo('Already generating chapters, please wait...');
    return;
  }
  
  hideError();
  showLoading(true);
  isGenerating = true;
  
  try {
    addDebugInfo(`Sending request to generate chapters for video ID: ${currentVideoId}`);
    addDebugInfo(`Fetch request to ${GENERATE_CHAPTERS_ENDPOINT} with video_id=${currentVideoId}${forceRefresh ? ' (force refresh)' : ''}`);
    
    const response = await fetch(GENERATE_CHAPTERS_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        video_id: currentVideoId,
        force_refresh: forceRefresh
      })
    });
    
    // Log response status and headers for debugging
    addDebugInfo(`Response status: ${response.status} `);
    addDebugInfo(`Response headers: ${JSON.stringify(Object.fromEntries([...response.headers]))}`);
    
    let jsonResponse;
    try {
      const responseText = await response.text();
      addDebugInfo(`Got JSON response: ${responseText.substring(0, 150)}...`);
      jsonResponse = JSON.parse(responseText);
    } catch (jsonError) {
      addDebugInfo(`Failed to parse response as JSON: ${jsonError.message}`);
      throw new Error(`Failed to parse response as JSON: ${jsonError.message}`);
    }
    
    if (!response.ok) {
      if (jsonResponse && jsonResponse.error) {
        addDebugInfo(`Error response: ${JSON.stringify(jsonResponse)}`);
        throw new Error(`Server error: ${JSON.stringify(jsonResponse.error)}`);
      } else {
        throw new Error(`Server returned status ${response.status}`);
      }
    }
    
    if (!jsonResponse.success) {
      const errorMessage = jsonResponse.error || 'Unknown error occurred';
      addDebugInfo(`API reported error: ${errorMessage}`);
      throw new Error(errorMessage);
    }
    
    // Success!
    const chapters = jsonResponse.chapters;
    const fromCache = jsonResponse.from_cache || false;
    
    addDebugInfo(`Chapters generated ${fromCache ? 'from cache' : 'successfully'}. Video duration: ${jsonResponse.video_duration_minutes}, used proxy: ${jsonResponse.used_proxy}`);
    
    displayChapters(chapters);
    regenerateButton.disabled = false;
    return chapters;
    
  } catch (error) {
    addDebugInfo(`Final error: ${error.message}`);
    showError(`Failed to generate chapters: ${error.message}`);
    throw error;
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
  generateChapters(true); // Pass true to force a refresh from the server
} 