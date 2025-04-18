"use strict";
(function() {
/**
 * YouTube Chapter Generator UI Manager Module
 *
 * This module provides a centralized UI manager for handling DOM manipulation.
 * It uses the state store to update the UI based on state changes.
 */

/**
 * UI Manager class for handling DOM manipulation
 */
class UiManager {
  constructor() {
    this.store = window.YCG_STORE;
    this.api = window.YCG_API;
    this.elements = {};
    this.unsubscribe = null;
    this._boundGenerateHandler = null;
    this._boundCopyHandler = null;
    this._boundRegenerateHandler = null;
    this._boundPrevVersionHandler = null;
    this._boundNextVersionHandler = null;
  }

  /**
   * Initialize the UI manager
   */
  init() {
    console.log("[UI] Initializing UI manager");

    // Cache DOM elements
    this.cacheElements();

    // Subscribe to state changes
    if (this.store) {
      this.unsubscribe = this.store.subscribe((state) => {
        console.log("[UI-DEBUG] State changed, updating UI");
        this.updateUI(state);
      });
    } else {
      console.error("[UI] Store is not available");
    }

    // Set up event listeners
    this.setupEventListeners();

    // Initial UI update
    if (this.store) {
      const initialState = this.store.getState();
      console.log("[UI-DEBUG] Initial state:", JSON.stringify(initialState));
      this.updateUI(initialState);
    }

    console.log("[UI] UI manager initialized");
  }

  /**
   * Cache DOM elements for faster access
   */
  cacheElements() {
    // Header elements
    this.elements.header = {
      loginBtn: document.getElementById("login-btn"),
      settingsBtn: document.getElementById("settings-btn"),
      userProfile: document.getElementById("user-profile"),
      userMenu: document.getElementById("user-menu"),
      userAvatar: document.getElementById("user-avatar"),
      menuUserAvatar: document.getElementById("menu-user-avatar"),
      userName: document.getElementById("user-name"),
      userEmail: document.getElementById("user-email"),
      creditsCount: document.getElementById("credits-count"),
      creditsBadge: document.getElementById("credits-badge"),
    };

    // Container elements
    this.elements.containers = {
      welcomeContainer: document.getElementById("welcome-container"),
      authContainer: document.getElementById("auth-container"),
      mainContent: document.getElementById("main-content"),
      mainContentArea: document.getElementById("main-content-area"),
    };

    // Auth elements
    this.elements.auth = {
      googleSignInButton1: document.getElementById("google-signin-button"),
      googleSignInButton2: document.getElementById("google-signin-button-auth"),
      errorMessage: document.getElementById("error-message"),
      logoutLink: document.getElementById("logout-link"),
    };

    // Main content elements will be created dynamically
    this.elements.main = {};

    console.log("[UI] DOM elements cached");
    console.log("[UI-DEBUG] Cached DOM elements:", this.elements);
  }

  /**
   * Set up event listeners
   */
  setupEventListeners() {
    // Header event listeners
    if (this.elements.header.settingsBtn) {
      this.elements.header.settingsBtn.addEventListener("click", () => {
        if (this.store) {
          this.store.dispatch("ui", { type: "TOGGLE_MENU" });
        }
      });
    }

    // Close menu when clicking outside
    document.addEventListener("click", (event) => {
      const userMenu = this.elements.header.userMenu;
      const settingsBtn = this.elements.header.settingsBtn;

      if (
        userMenu &&
        settingsBtn &&
        !userMenu.contains(event.target) &&
        !settingsBtn.contains(event.target) &&
        this.store &&
        this.store.getState().ui.isMenuOpen
      ) {
        this.store.dispatch("ui", { type: "CLOSE_MENU" });
      }
    });

    // Auth event listeners
    if (this.elements.auth.logoutLink) {
      this.elements.auth.logoutLink.addEventListener("click", (event) => {
        event.preventDefault();
        this.handleLogout();
      });
    }

    console.log("[UI] Event listeners set up");
  }

  /**
   * Update the UI based on state changes
   * @param {Object} state - The current state
   */
  updateUI(state) {
    console.log("[UI] Updating UI with state:", state);

    // Update auth UI
    this.updateAuthUI(state);

    // Update credits UI
    this.updateCreditsUI(state);

    // Update active view
    this.updateActiveView(state);

    // Update menu state
    this.updateMenuState(state);

    // Update main content if it's the active view
    if (state.ui.activeView === "main") {
      this.ensureMainContentCreated();
      this.updateMainContent(state);
    }
  }

  /**
   * Update the authentication UI
   * @param {Object} state - The current state
   */
  updateAuthUI(state) {
    const { auth } = state;
    const { userProfile, userAvatar, menuUserAvatar, userName, userEmail } = this.elements.header;

    console.log("[UI-DEBUG] Updating auth UI with state:", JSON.stringify(auth));
    console.log("[UI-DEBUG] Header elements:", this.elements.header);

    // Hide userProfile and menuUserAvatar always (no user picture in header or menu)
    if (userProfile) {
      userProfile.classList.add("hidden");
    }
    if (menuUserAvatar) {
      menuUserAvatar.classList.add("hidden");
    }

    if (auth.isAuthenticated && auth.user) {
      if (userName) {
        userName.textContent = auth.user.name || "User";
      }
      if (userEmail) {
        userEmail.textContent = auth.user.email || "";
      }
    }

    // Update error message if any
    if (auth.error && this.elements.auth.errorMessage) {
      console.log("[UI-DEBUG] Error message shown:", auth.error);
      this.elements.auth.errorMessage.textContent = auth.error;
      this.elements.auth.errorMessage.classList.remove("hidden");
    } else if (this.elements.auth.errorMessage) {
      console.log("[UI-DEBUG] Error message hidden");
      this.elements.auth.errorMessage.classList.add("hidden");
    }

    console.log("[UI-DEBUG] Auth UI update complete");
  }

  /**
   * Update the credits UI
   * @param {Object} state - The current state
   */
  updateCreditsUI(state) {
    const { credits } = state;
    const { creditsCount, creditsBadge } = this.elements.header;

    if (creditsCount) {
      creditsCount.textContent = credits.isLoading ? "..." : credits.count;
    }

    if (creditsBadge) {
      if (credits.isLoading) {
        creditsBadge.innerHTML = "<span class=\"spinner\" aria-label=\"Loading credits\"></span>";
      } else {
        creditsBadge.textContent = credits.count;
      }
      if (credits.count > 0 || credits.isLoading) {
        creditsBadge.classList.remove("hidden");
      } else {
        creditsBadge.classList.add("hidden");
      }
    }
  }

  /**
   * Update the active view
   * @param {Object} state - The current state
   */
  updateActiveView(state) {
    const { ui, auth } = state;
    const { welcomeContainer, authContainer, mainContent } = this.elements.containers;

    console.log("[UI-DEBUG] Updating active view with state:", {
      "ui.activeView": ui.activeView,
      "auth.isAuthenticated": auth.isAuthenticated,
      "auth.user": auth.user
    });

    console.log("[UI-DEBUG] Container elements:", this.elements.containers);

    // Determine which view should be active
    let activeView = ui.activeView;

    // Override based on auth state
    if (!auth.isAuthenticated) {
      console.log("[UI-DEBUG] User not authenticated, should show welcome view");
      activeView = "welcome";
    } else if (activeView === "welcome") {
      activeView = "main";
    }

    // Update the store if needed
    if (activeView !== ui.activeView) {
      activeView = "main";
    }

    // Update the store if needed
    if (activeView !== ui.activeView) {
      this.store.dispatch("ui", {
        type: "SET_ACTIVE_VIEW",
        payload: { view: activeView },
      });
      return; // The UI will be updated again after the state change
    }

    console.log("[UI-DEBUG] Current view:", activeView);

    // Update the visible container
    if (welcomeContainer) {
      console.log("[UI-DEBUG] Welcome container shown");
      welcomeContainer.classList.toggle("hidden", activeView !== "welcome");
    }

    if (authContainer) {
      console.log("[UI-DEBUG] Auth container hidden");
      authContainer.classList.toggle("hidden", activeView !== "auth");
    }

    if (mainContent) {
      console.log("[UI-DEBUG] Main content hidden");
      mainContent.classList.toggle("hidden", activeView !== "main");
    }

    console.log("[UI-DEBUG] Active view update complete");
  }

  /**
   * Update the menu state
   * @param {Object} state - The current state
   */
  updateMenuState(state) {
    const { ui } = state;
    const { userMenu } = this.elements.header;

    if (userMenu) {
      userMenu.classList.toggle("hidden", !ui.isMenuOpen);
    }
  }

  /**
   * Ensure the main content is created
   */
  ensureMainContentCreated() {
    console.log("[DEBUG] ensureMainContentCreated called");
    const { mainContentArea } = this.elements.containers;

    if (!mainContentArea) return;

    // Check if main content is empty
    if (mainContentArea.children.length === 0) {
      console.log("[UI] Creating main content structure");

      // Unified card for video info, generate/regenerate, and chapters
      mainContentArea.innerHTML = `
      <div class="main-content-card">
        <div id="status" class="status-message">
          <p>Checking if you're on a YouTube video page...</p>
        </div>
        <div id="error-message" class="error-message hidden"></div>
        <div id="video-info" class="video-info hidden">
          <h3>Current Video</h3>
          <p id="video-title" class="video-title">Video Title</p>
        </div>
        <div class="actions">
          <button id="generate-btn" class="btn btn-primary btn-full">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 8px;">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path>
            </svg>
            Generate Chapters
          </button>
        </div>
        <div id="loading" class="loading hidden">
          <div class="spinner"></div>
          <p>Generating chapters...</p>
          <p class="text-sm text-muted-foreground mt-2">This may take a few moments</p>
        </div>
        <div id="chapters-container" class="chapters-block hidden">
          <div class="chapters-header">
            <h3>Generated Chapters</h3>
            <div class="version-controls">
              <button id="prev-version-btn" class="btn btn-secondary" disabled>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="15 18 9 12 15 6"></polyline>
                </svg>
              </button>
              <span id="version-indicator">1/1</span>
              <button id="next-version-btn" class="btn btn-secondary" disabled>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
              </button>
            </div>
          </div>
          <div id="chapters-content" class="chapters-content"></div>
          <div class="chapters-actions">
            <button id="copy-btn" class="btn btn-primary">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 8px;">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              Copy
            </button>
            <button id="regenerate-btn" class="btn btn-secondary">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 8px;">
                <path d="M23 4v6h-6"></path>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
              </svg>
              Regenerate
            </button>
          </div>
        </div>
      </div>
      `;

      // Cache the new elements
      this.elements.main = {
        status: document.getElementById("status"),
        videoInfo: document.getElementById("video-info"),
        videoTitle: document.getElementById("video-title"),
        generateButton: document.getElementById("generate-btn"),
        loading: document.getElementById("loading"),
        chaptersContainer: document.getElementById("chapters-container"),
        chaptersContent: document.getElementById("chapters-content"),
        copyButton: document.getElementById("copy-btn"),
        regenerateButton: document.getElementById("regenerate-btn"),
        prevVersionButton: document.getElementById("prev-version-btn"),
        nextVersionButton: document.getElementById("next-version-btn"),
        versionIndicator: document.getElementById("version-indicator"),
        errorMessage: document.getElementById("error-message"),
      };

      // Set up event listeners for main content
      this.setupMainContentEventListeners();
    }
  }

  /**
   * Set up event listeners for main content
   */
  setupMainContentEventListeners() {
    console.log("[DEBUG] setupMainContentEventListeners called");
    const { generateButton, copyButton, regenerateButton, prevVersionButton, nextVersionButton } = this.elements.main;

    // --- Generate Button ---
    if (generateButton) {
        if (this._boundGenerateHandler) {
            generateButton.removeEventListener("click", this._boundGenerateHandler);
        }
        // Only pass event if needed
        this._boundGenerateHandler = (event) => this.handleGenerateChapters();
        generateButton.addEventListener("click", this._boundGenerateHandler);
        console.log("[DEBUG] Generate button event listener attached");
    }

    // --- Copy Button ---
    if (copyButton) {
        if (this._boundCopyHandler) {
            copyButton.removeEventListener("click", this._boundCopyHandler);
        }
        this._boundCopyHandler = () => this.handleCopyChapters();
        copyButton.addEventListener("click", this._boundCopyHandler);
        console.log("[DEBUG] Copy button event listener attached");
    }

    // --- Regenerate Button ---
    if (regenerateButton) {
        if (this._boundRegenerateHandler) {
            regenerateButton.removeEventListener("click", this._boundRegenerateHandler);
        }
        // Prevent event object from being passed
        this._boundRegenerateHandler = () => this.handleRegenerateChapters();
        regenerateButton.addEventListener("click", this._boundRegenerateHandler);
        console.log("[DEBUG] Regenerate button event listener attached");
    }

    // --- Prev Version Button ---
    if (prevVersionButton) {
        if (this._boundPrevVersionHandler) {
            prevVersionButton.removeEventListener("click", this._boundPrevVersionHandler);
        }
        this._boundPrevVersionHandler = () => this.handlePrevVersion();
        prevVersionButton.addEventListener("click", this._boundPrevVersionHandler);
        console.log("[DEBUG] PrevVersion button event listener attached");
    }

    // --- Next Version Button ---
    if (nextVersionButton) {
        if (this._boundNextVersionHandler) {
            nextVersionButton.removeEventListener("click", this._boundNextVersionHandler);
        }
        this._boundNextVersionHandler = () => this.handleNextVersion();
        nextVersionButton.addEventListener("click", this._boundNextVersionHandler);
        console.log("[DEBUG] NextVersion button event listener attached");
    }

    console.log("[UI] Main content event listeners set up");
  }

  /**
   * Update the main content
   * @param {Object} state - The current state
   */
  updateMainContent(state) {
    const { video, chapters } = state;
    const {
      status,
      videoInfo,
      videoTitle,
      loading,
      chaptersContainer,
      chaptersContent,
      prevVersionButton,
      nextVersionButton,
      versionIndicator,
      errorMessage,
      generateButton,
      regenerateButton,
      copyButton
    } = this.elements.main;

    // Hide all main blocks by default
    if (status) status.classList.add("hidden");
    if (videoInfo) videoInfo.classList.add("hidden");
    if (generateButton) generateButton.classList.add("hidden");
    if (loading) loading.classList.add("hidden");
    if (chaptersContainer) chaptersContainer.classList.add("hidden");

    // Show video info and generate button if on video page and no chapters generated yet
    if (video.isOnVideoPage && video.id && video.title && chapters.versions.length === 0 && !chapters.isGenerating) {
      if (videoInfo) videoInfo.classList.remove("hidden");
      if (generateButton) generateButton.classList.remove("hidden");
      if (status) status.classList.add("hidden");
    }
    // Show only loading indicator when generating
    else if (chapters.isGenerating) {
      if (loading) loading.classList.remove("hidden");
    }
    // Show chapters, copy, regenerate, version controls when chapters exist and not generating
    else if (chapters.versions.length > 0 && !chapters.isGenerating) {
      if (videoInfo) videoInfo.classList.remove("hidden");
      if (chaptersContainer) chaptersContainer.classList.remove("hidden");
      // Update chapters content
      if (chaptersContent) {
        const currentVersion = chapters.versions[chapters.currentVersionIndex];
        chaptersContent.innerHTML = this.formatChaptersHtml(currentVersion);
      }
      // Update version controls
      if (versionIndicator) {
        versionIndicator.textContent = `${chapters.currentVersionIndex + 1}/${chapters.versions.length}`;
      }
      if (prevVersionButton) {
        prevVersionButton.disabled = chapters.currentVersionIndex === 0;
      }
      if (nextVersionButton) {
        nextVersionButton.disabled = chapters.currentVersionIndex === chapters.versions.length - 1;
      }
      if (copyButton) copyButton.disabled = false;
      if (regenerateButton) regenerateButton.disabled = false;
    }
    // Show status if not on video page
    else {
      if (status) status.classList.remove("hidden");
    }

    // Update video title
    if (videoInfo && video.title) {
      videoInfo.querySelector("#video-title").textContent = video.title;
    }

    // Error handling
    if (errorMessage) {
      if (video.error || chapters.error) {
        errorMessage.textContent = video.error || chapters.error;
        errorMessage.classList.remove("hidden");
      } else {
        errorMessage.classList.add("hidden");
      }
    }
  }

  /**
   * Format chapters as HTML
   * @param {Object} chapters - The chapters object
   * @returns {string} The formatted HTML
   */
  formatChaptersHtml(chapters) {
    if (!chapters || !chapters.formatted_text || chapters.formatted_text.trim().length === 0) {
      return "<p>No chapters generated.</p>";
    }
    // Only render the full chapter text, not the list
    return `
      <div class="chapters-text">
        <pre>${chapters.formatted_text}</pre>
      </div>
    `;
  }

  /**
   * Handle generate chapters button click
   * @param {boolean} [force] - Whether to force regeneration (bypass cache)
   */
  async handleGenerateChapters(force = false) {
    console.log("[DEBUG] handleGenerateChapters called, force:", force);
    if (!this.store || !this.api) {
      this.showNotification("API service not available", "error");
      return;
    }

    const state = this.store.getState();
    const { video, credits } = state;

    // Check if user has enough credits
    if (credits.count <= 0) {
      this.showNotification("You need credits to generate chapters. Please purchase more credits.", "error");
      return;
    }

    // Check if we have video info
    if (!video.id || !video.title) {
      this.showNotification("No video information available.", "error");
      return;
    }

    // Dispatch generate start action
    this.store.dispatch("chapters", { type: "GENERATE_START" });

    try {
      // Call the API with force param if needed
      const chapterObj = await this.api.generateChapters(video.id, video.title, force);
      this.store.dispatch("chapters", {
        type: "GENERATE_SUCCESS",
        payload: { chapters: chapterObj },
      });

      // Decrement credits
      this.store.dispatch("credits", { type: "DECREMENT_CREDITS" });

      // Save state to storage
      await this.store.saveToStorage();

      this.showNotification("Chapters generated successfully!", "success");
    } catch (error) {
      console.error("[UI] Error generating chapters:", error);

      // Dispatch generate failure action
      this.store.dispatch("chapters", {
        type: "GENERATE_FAILURE",
        payload: { error: error.message },
      });

      this.showNotification(`Error generating chapters: ${error.message}`, "error");
    }
  }

  /**
   * Handle copy chapters button click
   */
  handleCopyChapters() {
    if (!this.store) {
      this.showNotification("Store not available", "error");
      return;
    }

    const state = this.store.getState();
    const { chapters } = state;

    // Get current version
    const currentVersion = chapters.versions[chapters.currentVersionIndex];

    if (!currentVersion || !currentVersion.formatted_text) {
      this.showNotification("No chapters to copy.", "error");
      return;
    }

    // Copy to clipboard
    navigator.clipboard
      .writeText(currentVersion.formatted_text)
      .then(() => {
        this.showNotification("Chapters copied to clipboard!", "success");
      })
      .catch((error) => {
        console.error("[UI] Error copying to clipboard:", error);
        this.showNotification("Error copying to clipboard. Please try again.", "error");
      });
  }

  /**
   * Handle regenerate chapters button click
   */
  handleRegenerateChapters() {
    console.log("[DEBUG] handleRegenerateChapters called");
    // Pass force=true to handleGenerateChapters
    this.handleGenerateChapters(true);
  }

  /**
   * Handle previous version button click
   */
  handlePrevVersion() {
    if (!this.store) return;

    const state = this.store.getState();
    const { chapters } = state;

    if (chapters.currentVersionIndex > 0) {
      this.store.dispatch("chapters", {
        type: "SET_VERSION_INDEX",
        payload: { index: chapters.currentVersionIndex - 1 },
      });
    }
  }

  /**
   * Handle next version button click
   */
  handleNextVersion() {
    if (!this.store) return;

    const state = this.store.getState();
    const { chapters } = state;

    if (chapters.currentVersionIndex < chapters.versions.length - 1) {
      this.store.dispatch("chapters", {
        type: "SET_VERSION_INDEX",
        payload: { index: chapters.currentVersionIndex + 1 },
      });
    }
  }

  /**
   * Handle logout button click
   */
  async handleLogout() {
    if (!this.store) {
      console.error("[UI] Store not available for logout");
      return;
    }

    console.log("[UI] Handling logout");

    // Dispatch logout action
    this.store.dispatch("auth", { type: "LOGOUT" });

    // Clear chapters
    this.store.dispatch("chapters", { type: "CLEAR_CHAPTERS" });

    // Set active view to welcome
    this.store.dispatch("ui", {
      type: "SET_ACTIVE_VIEW",
      payload: { view: "welcome" },
    });

    // Close menu
    this.store.dispatch("ui", { type: "CLOSE_MENU" });

    // Save state to storage
    await this.store.saveToStorage();

    // Force UI update
    this.updateUI(this.store.getState());

    // Clear Google auth token
    try {
      // Check if chrome is defined
      if (typeof chrome !== "undefined" && chrome.identity && chrome.identity.clearAllCachedAuthTokens) {
        await new Promise((resolve) => {
          chrome.identity.clearAllCachedAuthTokens(resolve);
        });
        console.log("[UI] Cleared Google auth tokens");
      } else {
        console.warn("[UI] chrome.identity.clearAllCachedAuthTokens is not available.");
      }
    } catch (error) {
      console.error("[UI] Error clearing Google auth tokens:", error);
    }

    this.showNotification("You have been logged out.", "info");

    // Force refresh the popup after a short delay
    setTimeout(() => {
      console.log("[UI] Refreshing popup after logout");
      window.location.reload();
    }, 1000);
  }

  /**
   * Fetch chapters for a video (add logging)
   * @param {string} videoId - The YouTube video ID
   */
  async fetchChapters(videoId) {
    console.log(`[UI-DEBUG] fetchChapters called for videoId: ${videoId}`);
    try {
      const result = await this.api.generateChapters(videoId);
      console.log("[UI-DEBUG] fetchChapters result:", result);
      if (result && result.data && result.data.formatted_text) {
        this.store.dispatch("chapters", {
          type: "GENERATE_SUCCESS",
          payload: { chapters: result.data },
        });
      } else {
        this.showNotification("No chapters found for this video.", "info");
      }
    } catch (error) {
      console.error("[UI-DEBUG] fetchChapters error:", error);
      this.showNotification("Failed to fetch chapters.", "error");
    }
  }

  /**
   * Show a notification
   * @param {string} message - The notification message
   * @param {string} type - The notification type (success, error, info)
   */
  showNotification(message, type = "info") {
    // Create notification element
    const notification = document.createElement("div");
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Add close button
    const closeButton = document.createElement("button");
    closeButton.className = "notification-close";
    closeButton.innerHTML = "&times;";
    closeButton.addEventListener("click", () => {
      notification.remove();
    });

    notification.appendChild(closeButton);

    // Add to document
    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      notification.classList.add("notification-hide");
      setTimeout(() => {
        notification.remove();
      }, 300);
    }, 5000);
  }

  /**
   * Clean up the UI manager
   */
  cleanup() {
    if (this.unsubscribe) {
      this.unsubscribe();
    }
  }
}

// Create and export the UI manager
document.addEventListener("DOMContentLoaded", () => {
  // Wait for the DOM to be loaded before creating the UI manager
  // This ensures that YCG_STORE is available
  if (window.YCG_STORE) {
    window.YCG_UI = new UiManager();
    window.YCG_UI.init();
  } else {
    console.error("[UI] Failed to create UI manager: YCG_STORE not available");
  }
});

})();
