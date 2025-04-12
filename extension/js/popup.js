/**
 * YouTube Chapter Generator Popup Script
 * 
 * This is the main entry point for the popup UI.
 */

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  // Wait for the store, API, and video service to be initialized
  setTimeout(() => {
    if (window.YCG_STORE && window.YCG_API && window.YCG_VIDEO) {
      init();
    } else {
      console.error("[Popup] Failed to initialize: YCG_STORE, YCG_API, or YCG_VIDEO not available");
    }
  }, 100); // Small delay to ensure all services are initialized
});

/**
 * Initialize the popup
 */
async function init() {
  console.log("[Popup] Initializing popup...");
  
  // Get references to the store, API, and video service
  const store = window.YCG_STORE;
  const api = window.YCG_API;
  const video = window.YCG_VIDEO;
  
  // Initialize video service
  video.init();
  
  // Check API availability
  try {
    const isApiAvailable = await api.ping();
    if (!isApiAvailable) {
      console.error("[Popup] API is not available");
      if (window.YCG_UI) {
        window.YCG_UI.showNotification("API is not available. Please try again later.", "error");
      }
    }
  } catch (error) {
    console.error("[Popup] Error checking API availability:", error);
  }
  
  // Set up event listeners for popup-specific functionality
  setupPopupEventListeners();
  
  console.log("[Popup] Initialization complete");
}

/**
 * Set up popup-specific event listeners
 */
function setupPopupEventListeners() {
  // Terms and privacy links
  const termsLink = document.getElementById('terms-link');
  const privacyLink = document.getElementById('privacy-link');
  const myAccountLink = document.getElementById('my-account-link');
  const feedbackLink = document.getElementById('feedback-link');
  
  if (termsLink) {
    termsLink.addEventListener('click', (event) => {
      event.preventDefault();
      chrome.tabs.create({ url: 'https://new-ycg.vercel.app/terms' });
    });
  }
  
  if (privacyLink) {
    privacyLink.addEventListener('click', (event) => {
      event.preventDefault();
      chrome.tabs.create({ url: 'https://new-ycg.vercel.app/privacy' });
    });
  }
  
  if (myAccountLink) {
    myAccountLink.addEventListener('click', (event) => {
      event.preventDefault();
      chrome.tabs.create({ url: 'https://new-ycg.vercel.app/account' });
    });
  }
  
  if (feedbackLink) {
    feedbackLink.addEventListener('click', (event) => {
      event.preventDefault();
      chrome.tabs.create({ url: 'https://forms.gle/XYZ123' }); // Replace with actual feedback form URL
    });
  }
}
