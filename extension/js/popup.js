// YouTube Chapter Generator Popup Script

// API endpoints
const API_BASE_URL = "https://new-ycg.vercel.app/api"
const GENERATE_CHAPTERS_ENDPOINT = `${API_BASE_URL}/generate-chapters`
const PING_ENDPOINT = `${API_BASE_URL}`

// Elements
let mainContentElement = document.getElementById("main-content")
let statusElement = document.getElementById("status")
let videoInfoElement = document.getElementById("video-info")
let videoTitleElement = document.getElementById("video-title")
let errorMessageElement = document.getElementById("error-message")
let generateButton = document.getElementById("generate-btn")
let loadingElement = document.getElementById("loading")
let chaptersContainerElement = document.getElementById("chapters-container")
let chaptersContentElement = document.getElementById("chapters-content")
let copyButton = document.getElementById("copy-btn")
let regenerateButton = document.getElementById("regenerate-btn")
let settingsButton = document.getElementById("settings-btn")
let prevVersionButton = document.getElementById("prev-version-btn")
let nextVersionButton = document.getElementById("next-version-btn")
let versionIndicatorElement = document.getElementById("version-indicator")
let creditsCountElement = document.getElementById("credits-count")

// State variables
let currentVideoId = null
let currentVideoTitle = null
let isGenerating = false
const chapterVersions = []
let currentVersionIndex = 0
let userCredits = 10 // Default value, should be fetched from server or storage

// Initialize
document.addEventListener("DOMContentLoaded", init)

function init() {
  console.log("Initializing popup.js...");

  // Initialize main content if not already done by auth.js
  if (mainContentElement) {
    // Create the main content structure if it's empty
    if (mainContentElement.children.length === 0) {
      console.log("Creating main content structure");
      mainContentElement.innerHTML = `
        <div id="status" class="status-message">
          <p>Checking if you're on a YouTube video page...</p>
        </div>
        <div id="error-message" class="error-message hidden"></div>
        <div id="video-info" class="video-info hidden">
          <h3>Video Title:</h3>
          <p id="video-title" class="video-title">Loading...</p>
          <div class="generate-button-container">
            <button id="generate-btn" class="btn btn-primary" disabled>
              <span class="btn-icon">✨</span> Generate Chapters
            </button>
          </div>
        </div>
        <div id="loading" class="loading hidden">
          <div class="spinner"></div>
          <p>Generating chapters...</p>
        </div>
        <div id="chapters-container" class="chapters-container hidden">
          <div class="chapters-header">
            <h3>Generated Chapters</h3>
            <div class="version-navigation">
              <button id="prev-version-btn" class="btn btn-sm" disabled>
                <span class="btn-icon">◀</span>
              </button>
              <span id="version-indicator">Version 1/1</span>
              <button id="next-version-btn" class="btn btn-sm" disabled>
                <span class="btn-icon">▶</span>
              </button>
            </div>
          </div>
          <pre id="chapters-content" class="chapters-content"></pre>
          <div class="chapters-actions">
            <button id="copy-btn" class="btn">
              <span class="btn-icon">📋</span> Copy to Clipboard
            </button>
            <button id="regenerate-btn" class="btn" disabled>
              <span class="btn-icon">🔄</span> Regenerate
            </button>
          </div>
        </div>
      `;

      // Re-initialize element references after creating the structure
      initElementReferences();
    }
  } else {
    console.error("Main content element not found!");
  }

  // Set up event listeners
  if (generateButton) generateButton.addEventListener("click", handleGenerateClick);
  if (copyButton) copyButton.addEventListener("click", handleCopyClick);
  if (regenerateButton) regenerateButton.addEventListener("click", handleRegenerateClick);
  if (settingsButton) settingsButton.addEventListener("click", handleSettingsClick);
  if (prevVersionButton) prevVersionButton.addEventListener("click", handlePrevVersionClick);
  if (nextVersionButton) nextVersionButton.addEventListener("click", handleNextVersionClick);

  // Load user credits
  loadUserCredits();

  // Check API server status first
  checkApiStatus()
    .then(() => {
      // Check if we're on a YouTube video page
      getCurrentTabInfo();
    })
    .catch((error) => {
      console.error(`API status check failed with error: ${error.message}`);
      // Continue anyway to allow diagnostics
      getCurrentTabInfo();
      showError(`API server may have issues: ${error.message}. You can still try to generate chapters.`);
    });
}

// Initialize element references after creating the structure
function initElementReferences() {
  console.log("Re-initializing element references");
  statusElement = document.getElementById("status");
  videoInfoElement = document.getElementById("video-info");
  videoTitleElement = document.getElementById("video-title");
  errorMessageElement = document.getElementById("error-message");
  generateButton = document.getElementById("generate-btn");
  loadingElement = document.getElementById("loading");
  chaptersContainerElement = document.getElementById("chapters-container");
  chaptersContentElement = document.getElementById("chapters-content");
  copyButton = document.getElementById("copy-btn");
  regenerateButton = document.getElementById("regenerate-btn");
  prevVersionButton = document.getElementById("prev-version-btn");
  nextVersionButton = document.getElementById("next-version-btn");
  versionIndicatorElement = document.getElementById("version-indicator");
}

// Load user credits from storage
function loadUserCredits() {
  chrome.storage.sync.get(["userCredits"], (result) => {
    if (result.userCredits !== undefined) {
      userCredits = result.userCredits
      updateCreditsDisplay()
    } else {
      // If not found in storage, fetch from server
      fetchUserCredits()
    }
  })
}

// Fetch user credits from server
function fetchUserCredits() {
  // This is a placeholder - implement actual API call to get user credits
  // For now, we'll use the default value set in state variables
  updateCreditsDisplay()
}

// Update credits display
function updateCreditsDisplay() {
  creditsCountElement.textContent = userCredits
}

// Check API server status
async function checkApiStatus() {
  try {
    console.log("Checking API status...")

    // Add cache buster to prevent caching
    const cacheBuster = Date.now()
    const response = await fetch(`${PING_ENDPOINT}?_=${cacheBuster}`, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    })

    let responseData
    try {
      responseData = await response.json()
    } catch (jsonError) {
      console.error(`Failed to parse API response as JSON: ${jsonError.message}`)
      throw new Error(`API returned invalid JSON. Response status: ${response.status}`)
    }

    // Even if status code is not OK, check if we got a valid response with error info
    if (responseData) {
      if (responseData.status === "error") {
        console.error(`API returned error status: ${JSON.stringify(responseData)}`)
        throw new Error(`API error: ${responseData.error || responseData.message || "Unknown error"}`)
      }

      if (!response.ok) {
        console.error(
          `API server returned status ${response.status} but with parseable data: ${JSON.stringify(responseData)}`,
        )
        throw new Error(`API server returned status ${response.status}: ${JSON.stringify(responseData.error || {})}`)
      }

      // Success case
      console.log(`API server is online. Status: ${responseData.status}`)
      return responseData
    } else {
      throw new Error(`API server returned status ${response.status} with no valid data`)
    }
  } catch (error) {
    console.error(`API status check failed: ${error.message}`)
    throw error
  }
}

// Get information about the current tab
function getCurrentTabInfo() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const currentTab = tabs[0]

    if (!currentTab || !currentTab.url || !currentTab.url.includes("youtube.com/watch")) {
      showError("Please open a YouTube video page to use this extension.")
      return
    }

    // Send message to content script to get video info
    try {
      console.log(`Requesting video info from tab ${currentTab.id}`)
      chrome.tabs.sendMessage(currentTab.id, { action: "getVideoInfo" }, (response) => {
        if (chrome.runtime.lastError) {
          console.error("Error sending message:", chrome.runtime.lastError.message)
          showError("Could not communicate with YouTube page. Please refresh the page and try again.")
          return
        }

        if (response && response.success) {
          console.log(
            `Received video info: ID=${response.videoId}, title="${response.videoTitle?.substring(0, 30)}..."`,
          )
          handleVideoInfo(response.videoId, response.videoTitle)
        } else {
          console.error(`Failed to get video info: ${response?.error || "Unknown error"}`)
          showError("Could not extract video information. Please make sure you are on a YouTube video page.")
        }
      })
    } catch (error) {
      console.error("Error in getCurrentTabInfo:", error)
      showError("An unexpected error occurred. Please refresh the page and try again.")
    }
  })
}

// Handle the video information received from content script
function handleVideoInfo(videoId, videoTitle) {
  if (!videoId) {
    showError("Could not determine the video ID. Please make sure you are on a YouTube video page.")
    return
  }

  currentVideoId = videoId
  currentVideoTitle = videoTitle || "Unknown Title"

  // Update UI
  statusElement.classList.add("hidden")
  videoInfoElement.classList.remove("hidden")
  videoTitleElement.textContent = currentVideoTitle
  generateButton.disabled = false
}

// Generate chapters
async function generateChapters(forceRefresh = false) {
  if (!currentVideoId) {
    showError("No YouTube video ID found.")
    return
  }

  if (isGenerating) {
    console.log("Already generating chapters, please wait...")
    return
  }

  // Check if user has enough credits
  if (userCredits <= 0) {
    showError("You have no credits left. Please purchase more credits to continue using this service.")
    return
  }

  hideError()
  showLoading(true)
  isGenerating = true

  try {
    console.log(`Sending request to generate chapters for video ID: ${currentVideoId}`)
    console.log(
      `Fetch request to ${GENERATE_CHAPTERS_ENDPOINT} with video_id=${currentVideoId}${forceRefresh ? " (force refresh)" : ""}`,
    )

    const response = await fetch(GENERATE_CHAPTERS_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        video_id: currentVideoId,
        force_refresh: forceRefresh,
      }),
    })

    // Log response status and headers for debugging
    console.log(`Response status: ${response.status} `)

    let jsonResponse
    try {
      const responseText = await response.text()
      console.log(`Got JSON response: ${responseText.substring(0, 150)}...`)
      jsonResponse = JSON.parse(responseText)
    } catch (jsonError) {
      console.error(`Failed to parse response as JSON: ${jsonError.message}`)
      throw new Error(`Failed to parse response as JSON: ${jsonError.message}`)
    }

    if (!response.ok) {
      if (jsonResponse && jsonResponse.error) {
        console.error(`Error response: ${JSON.stringify(jsonResponse)}`)
        throw new Error(`Server error: ${JSON.stringify(jsonResponse.error)}`)
      } else {
        throw new Error(`Server returned status ${response.status}`)
      }
    }

    if (!jsonResponse.success) {
      const errorMessage = jsonResponse.error || "Unknown error occurred"
      console.error(`API reported error: ${errorMessage}`)
      throw new Error(errorMessage)
    }

    // Success!
    const chapters = jsonResponse.chapters
    const fromCache = jsonResponse.from_cache || false

    console.log(
      `Chapters generated ${fromCache ? "from cache" : "successfully"}. Video duration: ${jsonResponse.video_duration_minutes}, used proxy: ${jsonResponse.used_proxy}`,
    )

    // If not from cache, deduct a credit
    if (!fromCache) {
      decrementCredits()
    }

    // Add to versions if it's a new generation
    if (forceRefresh || chapterVersions.length === 0) {
      chapterVersions.push(chapters)
      currentVersionIndex = chapterVersions.length - 1
    }

    displayChapters(chapters)
    updateVersionNavigation()
    regenerateButton.disabled = false
    return chapters
  } catch (error) {
    console.error(`Final error: ${error.message}`)
    showError(`Failed to generate chapters: ${error.message}`)
    throw error
  } finally {
    showLoading(false)
    isGenerating = false
  }
}

// Decrement user credits
function decrementCredits() {
  userCredits = Math.max(0, userCredits - 1)
  updateCreditsDisplay()

  // Save to storage
  chrome.storage.sync.set({ userCredits: userCredits })
}

// Display the generated chapters
function displayChapters(chapters) {
  chaptersContentElement.textContent = chapters
  chaptersContainerElement.classList.remove("hidden")
}

// Update version navigation
function updateVersionNavigation() {
  versionIndicatorElement.textContent = `Version ${currentVersionIndex + 1}/${chapterVersions.length}`

  prevVersionButton.disabled = currentVersionIndex <= 0
  nextVersionButton.disabled = currentVersionIndex >= chapterVersions.length - 1
}

// Copy chapters to clipboard
function copyToClipboard(text) {
  navigator.clipboard
    .writeText(text)
    .then(() => {
      // Show temporary "Copied!" feedback
      const originalText = copyButton.innerHTML
      copyButton.innerHTML = '<span class="btn-icon">✓</span> Copied!'

      setTimeout(() => {
        copyButton.innerHTML = originalText
      }, 2000)
    })
    .catch((err) => {
      console.error("Failed to copy:", err)
      showError("Failed to copy to clipboard. Please try again.")
    })
}

// Show/hide loading state
function showLoading(show) {
  if (show) {
    loadingElement.classList.remove("hidden")
    generateButton.disabled = true
  } else {
    loadingElement.classList.add("hidden")
    generateButton.disabled = false
  }
}

// Show error message
function showError(message) {
  errorMessageElement.textContent = message
  errorMessageElement.classList.remove("hidden")
  statusElement.classList.add("hidden")
  console.error(`Error displayed: ${message}`)
}

// Hide error message
function hideError() {
  errorMessageElement.classList.add("hidden")
}

// Event Handlers
function handleGenerateClick() {
  chaptersContainerElement.classList.add("hidden")
  generateChapters()
}

function handleCopyClick() {
  copyToClipboard(chaptersContentElement.textContent)
}

function handleRegenerateClick() {
  generateChapters(true) // Pass true to force a refresh from the server
}

function handleSettingsClick() {
  // Open settings page or show settings modal
  chrome.runtime.openOptionsPage()
}

function handlePrevVersionClick() {
  if (currentVersionIndex > 0) {
    currentVersionIndex--
    displayChapters(chapterVersions[currentVersionIndex])
    updateVersionNavigation()
  }
}

function handleNextVersionClick() {
  if (currentVersionIndex < chapterVersions.length - 1) {
    currentVersionIndex++
    displayChapters(chapterVersions[currentVersionIndex])
    updateVersionNavigation()
  }
}

