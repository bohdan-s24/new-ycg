// YouTube Chapter Generator Popup Script

// API endpoints
const API_BASE_URL = "https://new-ycg.vercel.app/api"
const GENERATE_CHAPTERS_ENDPOINT = `${API_BASE_URL}/generate-chapters`
const PING_ENDPOINT = `${API_BASE_URL}`

// Elements
const statusElement = document.getElementById("status")
const videoInfoElement = document.getElementById("video-info")
const videoTitleElement = document.getElementById("video-title")
const errorMessageElement = document.getElementById("error-message")
const generateButton = document.getElementById("generate-btn")
const loadingElement = document.getElementById("loading")
const chaptersContainerElement = document.getElementById("chapters-container")
const chaptersContentElement = document.getElementById("chapters-content")
const copyButton = document.getElementById("copy-btn")
const regenerateButton = document.getElementById("regenerate-btn")
const settingsButton = document.getElementById("settings-btn")
const prevVersionButton = document.getElementById("prev-version-btn")
const nextVersionButton = document.getElementById("next-version-btn")
const versionIndicatorElement = document.getElementById("version-indicator")
const creditsCountElement = document.getElementById("credits-count")

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
  // Set up event listeners
  generateButton.addEventListener("click", handleGenerateClick)
  copyButton.addEventListener("click", handleCopyClick)
  regenerateButton.addEventListener("click", handleRegenerateClick)
  settingsButton.addEventListener("click", handleSettingsClick)
  prevVersionButton.addEventListener("click", handlePrevVersionClick)
  nextVersionButton.addEventListener("click", handleNextVersionClick)

  // Load user credits
  loadUserCredits()

  // Check API server status first
  checkApiStatus()
    .then(() => {
      // Check if we're on a YouTube video page
      getCurrentTabInfo()
    })
    .catch((error) => {
      console.error(`API status check failed with error: ${error.message}`)
      // Continue anyway to allow diagnostics
      getCurrentTabInfo()
      showError(`API server may have issues: ${error.message}. You can still try to generate chapters.`)
    })
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

