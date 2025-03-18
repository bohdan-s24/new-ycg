// YouTube Chapter Generator Popup Script

// API endpoints
const API_BASE_URL = 'https://new-ycg.vercel.app/api';
const GENERATE_CHAPTERS_ENDPOINT = `${API_BASE_URL}/generate-chapters`;

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

// State variables
let currentVideoId = null;
let currentVideoTitle = null;
let isGenerating = false;

// Initialize
document.addEventListener('DOMContentLoaded', init);

function init() {
  // Set up event listeners
  generateButton.addEventListener('click', handleGenerateClick);
  copyButton.addEventListener('click', handleCopyClick);
  regenerateButton.addEventListener('click', handleRegenerateClick);
  
  // Check if we're on a YouTube video page
  getCurrentTabInfo();
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
      chrome.tabs.sendMessage(currentTab.id, { action: 'getVideoInfo' }, (response) => {
        if (chrome.runtime.lastError) {
          console.error('Error sending message:', chrome.runtime.lastError.message);
          showError('Could not communicate with YouTube page. Please refresh the page and try again.');
          return;
        }
        
        if (response && response.success) {
          handleVideoInfo(response.videoId, response.videoTitle);
        } else {
          showError('Could not extract video information. Please make sure you are on a YouTube video page.');
        }
      });
    } catch (error) {
      console.error('Error in getCurrentTabInfo:', error);
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
    console.log(`Sending request to ${GENERATE_CHAPTERS_ENDPOINT} for video ID: ${currentVideoId}`);
    
    // Try first with standard fetch
    try {
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
      
      console.log('Received response:', response.status, response.statusText);
      console.log('Response headers:', 
        Array.from(response.headers.entries())
          .map(([key, value]) => `${key}: ${value}`)
          .join(', ')
      );
      
      if (!response.ok) {
        const text = await response.text();
        console.error('Error response:', text);
        throw new Error(`Server responded with status ${response.status}: ${text}`);
      }
      
      const data = await response.json();
      console.log('Parsed response data:', data);
      
      if (data.success) {
        displayChapters(data.chapters);
      } else {
        showError(`Failed to generate chapters: ${data.error || 'Unknown error'}`);
      }
    } catch (fetchError) {
      // If standard fetch fails (possibly due to CORS), try with mode: 'no-cors'
      // Note: This won't give us access to the response data, but it might help diagnose issues
      if (fetchError.message.includes('CORS') || fetchError.message.includes('Failed to fetch')) {
        console.warn('CORS error detected, retrying with no-cors mode for diagnostic purposes');
        
        try {
          // This is just a diagnostic attempt - we can't read the response with no-cors
          await fetch(GENERATE_CHAPTERS_ENDPOINT, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              video_id: currentVideoId
            }),
            mode: 'no-cors'
          });
          
          // If we reach here, the request went through but we can't access the response
          console.log('no-cors request was sent, but we cannot access the response');
          throw new Error("CORS issue detected. The server is running but cannot accept cross-origin requests from this extension. Please check the server configuration.");
        } catch (noCorsError) {
          console.error('Even no-cors mode failed:', noCorsError);
          throw fetchError; // Throw the original error
        }
      } else {
        // Not a CORS issue, rethrow
        throw fetchError;
      }
    }
  } catch (error) {
    console.error('Error generating chapters:', error);
    
    if (error.message.includes('CORS')) {
      showError(`CORS error: The server is not properly configured to accept requests from this extension. Please check the server deployment.`);
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
      showError('Failed to copy to clipboard. Please try again.');
    });
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