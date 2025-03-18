// YouTube Chapter Generator Popup Script

// API endpoints
const API_BASE_URL = 'https://old-ycg.vercel.app/api';
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
    chrome.tabs.sendMessage(currentTab.id, { action: 'getVideoInfo' }, (response) => {
      if (chrome.runtime.lastError) {
        console.error('Error sending message:', chrome.runtime.lastError);
        showError('Could not communicate with YouTube page. Please refresh the page and try again.');
        return;
      }
      
      if (response && response.success) {
        handleVideoInfo(response.videoId, response.videoTitle);
      } else {
        showError('Could not extract video information. Please make sure you are on a YouTube video page.');
      }
    });
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
    const response = await fetch(GENERATE_CHAPTERS_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        video_id: currentVideoId
      }),
    });
    
    const data = await response.json();
    
    if (response.ok && data.success) {
      displayChapters(data.chapters);
    } else {
      showError(`Failed to generate chapters: ${data.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error generating chapters:', error);
    showError(`Failed to generate chapters: ${error.message}`);
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