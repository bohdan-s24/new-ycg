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
    
    // Initialize when DOM is loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.init());
    } else {
      this.init();
    }
  }
  
  /**
   * Initialize the UI manager
   */
  init() {
    console.log('[UI] Initializing UI manager');
    
    // Cache DOM elements
    this.cacheElements();
    
    // Subscribe to state changes
    this.unsubscribe = this.store.subscribe(state => this.updateUI(state));
    
    // Set up event listeners
    this.setupEventListeners();
    
    // Initial UI update
    this.updateUI(this.store.getState());
    
    console.log('[UI] UI manager initialized');
  }
  
  /**
   * Cache DOM elements for faster access
   */
  cacheElements() {
    // Header elements
    this.elements.header = {
      loginBtn: document.getElementById('login-btn'),
      settingsBtn: document.getElementById('settings-btn'),
      userProfile: document.getElementById('user-profile'),
      userMenu: document.getElementById('user-menu'),
      userAvatar: document.getElementById('user-avatar'),
      menuUserAvatar: document.getElementById('menu-user-avatar'),
      userName: document.getElementById('user-name'),
      userEmail: document.getElementById('user-email'),
      creditsCount: document.getElementById('credits-count'),
      creditsBadge: document.getElementById('credits-badge')
    };
    
    // Container elements
    this.elements.containers = {
      welcomeContainer: document.getElementById('welcome-container'),
      authContainer: document.getElementById('auth-container'),
      mainContent: document.getElementById('main-content')
    };
    
    // Auth elements
    this.elements.auth = {
      googleSignInButton1: document.getElementById('google-signin-button'),
      googleSignInButton2: document.getElementById('google-signin-button-auth'),
      errorMessage: document.getElementById('error-message'),
      logoutLink: document.getElementById('logout-link')
    };
    
    // Main content elements (will be created dynamically if needed)
    this.elements.main = {
      status: null,
      videoInfo: null,
      videoTitle: null,
      generateButton: null,
      loading: null,
      chaptersContainer: null,
      chaptersContent: null,
      copyButton: null,
      regenerateButton: null,
      prevVersionButton: null,
      nextVersionButton: null,
      versionIndicator: null
    };
    
    console.log('[UI] DOM elements cached');
  }
  
  /**
   * Set up event listeners
   */
  setupEventListeners() {
    // Header event listeners
    if (this.elements.header.settingsBtn) {
      this.elements.header.settingsBtn.addEventListener('click', () => {
        this.store.dispatch('ui', { type: 'TOGGLE_MENU' });
      });
    }
    
    // Close menu when clicking outside
    document.addEventListener('click', (event) => {
      const userMenu = this.elements.header.userMenu;
      const settingsBtn = this.elements.header.settingsBtn;
      
      if (userMenu && settingsBtn && 
          !userMenu.contains(event.target) && 
          !settingsBtn.contains(event.target) &&
          this.store.getState().ui.isMenuOpen) {
        this.store.dispatch('ui', { type: 'CLOSE_MENU' });
      }
    });
    
    // Auth event listeners
    if (this.elements.auth.logoutLink) {
      this.elements.auth.logoutLink.addEventListener('click', (event) => {
        event.preventDefault();
        this.handleLogout();
      });
    }
    
    console.log('[UI] Event listeners set up');
  }
  
  /**
   * Update the UI based on state changes
   * @param {Object} state - The current state
   */
  updateUI(state) {
    console.log('[UI] Updating UI with state:', state);
    
    // Update auth UI
    this.updateAuthUI(state);
    
    // Update credits UI
    this.updateCreditsUI(state);
    
    // Update active view
    this.updateActiveView(state);
    
    // Update menu state
    this.updateMenuState(state);
    
    // Update main content if it's the active view
    if (state.ui.activeView === 'main') {
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
    const { loginBtn, userProfile, userAvatar, menuUserAvatar, userName, userEmail } = this.elements.header;
    
    if (auth.isAuthenticated && auth.user) {
      // User is authenticated
      if (loginBtn) loginBtn.classList.add('hidden');
      if (userProfile) userProfile.classList.remove('hidden');
      
      // Update user profile
      if (userAvatar && auth.user.picture) {
        userAvatar.src = auth.user.picture;
        userAvatar.alt = auth.user.name || 'User';
      }
      
      if (menuUserAvatar && auth.user.picture) {
        menuUserAvatar.src = auth.user.picture;
        menuUserAvatar.alt = auth.user.name || 'User';
      }
      
      if (userName) userName.textContent = auth.user.name || 'User';
      if (userEmail) userEmail.textContent = auth.user.email || '';
    } else {
      // User is not authenticated
      if (loginBtn) loginBtn.classList.remove('hidden');
      if (userProfile) userProfile.classList.add('hidden');
    }
    
    // Update error message if any
    if (auth.error && this.elements.auth.errorMessage) {
      this.elements.auth.errorMessage.textContent = auth.error;
      this.elements.auth.errorMessage.classList.remove('hidden');
    } else if (this.elements.auth.errorMessage) {
      this.elements.auth.errorMessage.classList.add('hidden');
    }
  }
  
  /**
   * Update the credits UI
   * @param {Object} state - The current state
   */
  updateCreditsUI(state) {
    const { credits } = state;
    const { creditsCount, creditsBadge } = this.elements.header;
    
    if (creditsCount) {
      creditsCount.textContent = credits.isLoading ? '...' : credits.count;
    }
    
    if (creditsBadge) {
      if (credits.count > 0 || credits.isLoading) {
        creditsBadge.classList.remove('hidden');
      } else {
        creditsBadge.classList.add('hidden');
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
    
    // Determine which view should be active
    let activeView = ui.activeView;
    
    // Override based on auth state
    if (!auth.isAuthenticated) {
      activeView = 'welcome';
    } else if (activeView === 'welcome') {
      activeView = 'main';
    }
    
    // Update the store if needed
    if (activeView !== ui.activeView) {
      this.store.dispatch('ui', { 
        type: 'SET_ACTIVE_VIEW', 
        payload: { view: activeView } 
      });
      return; // The UI will be updated again after the state change
    }
    
    // Update the visible container
    if (welcomeContainer) {
      welcomeContainer.classList.toggle('hidden', activeView !== 'welcome');
    }
    
    if (authContainer) {
      authContainer.classList.toggle('hidden', activeView !== 'auth');
    }
    
    if (mainContent) {
      mainContent.classList.toggle('hidden', activeView !== 'main');
    }
  }
  
  /**
   * Update the menu state
   * @param {Object} state - The current state
   */
  updateMenuState(state) {
    const { ui } = state;
    const { userMenu } = this.elements.header;
    
    if (userMenu) {
      userMenu.classList.toggle('hidden', !ui.isMenuOpen);
    }
  }
  
  /**
   * Ensure the main content is created
   */
  ensureMainContentCreated() {
    const { mainContent } = this.elements.containers;
    
    if (!mainContent) return;
    
    // Check if main content is empty
    if (mainContent.children.length === 0) {
      console.log('[UI] Creating main content structure');
      
      // Create the main content structure
      mainContent.innerHTML = `
        <div id="status" class="status-message">
          <p>Checking if you're on a YouTube video page...</p>
        </div>
        <div id="error-message" class="error-message hidden"></div>
        <div id="video-info" class="video-info hidden">
          <h2>Video Information</h2>
          <p id="video-title" class="video-title">Video Title</p>
          <button id="generate-btn" class="btn btn-primary">Generate Chapters</button>
        </div>
        <div id="loading" class="loading hidden">
          <div class="spinner"></div>
          <p>Generating chapters...</p>
        </div>
        <div id="chapters-container" class="chapters-container hidden">
          <div class="chapters-header">
            <h2>Generated Chapters</h2>
            <div class="version-controls">
              <button id="prev-version-btn" class="btn btn-sm" disabled>Previous</button>
              <span id="version-indicator">Version 1/1</span>
              <button id="next-version-btn" class="btn btn-sm" disabled>Next</button>
            </div>
          </div>
          <div id="chapters-content" class="chapters-content"></div>
          <div class="chapters-actions">
            <button id="copy-btn" class="btn">Copy to Clipboard</button>
            <button id="regenerate-btn" class="btn btn-secondary">Regenerate</button>
          </div>
        </div>
      `;
      
      // Cache the new elements
      this.elements.main = {
        status: document.getElementById('status'),
        videoInfo: document.getElementById('video-info'),
        videoTitle: document.getElementById('video-title'),
        generateButton: document.getElementById('generate-btn'),
        loading: document.getElementById('loading'),
        chaptersContainer: document.getElementById('chapters-container'),
        chaptersContent: document.getElementById('chapters-content'),
        copyButton: document.getElementById('copy-btn'),
        regenerateButton: document.getElementById('regenerate-btn'),
        prevVersionButton: document.getElementById('prev-version-btn'),
        nextVersionButton: document.getElementById('next-version-btn'),
        versionIndicator: document.getElementById('version-indicator'),
        errorMessage: document.getElementById('error-message')
      };
      
      // Set up event listeners for main content
      this.setupMainContentEventListeners();
    }
  }
  
  /**
   * Set up event listeners for main content
   */
  setupMainContentEventListeners() {
    const { generateButton, copyButton, regenerateButton, prevVersionButton, nextVersionButton } = this.elements.main;
    
    if (generateButton) {
      generateButton.addEventListener('click', () => this.handleGenerateChapters());
    }
    
    if (copyButton) {
      copyButton.addEventListener('click', () => this.handleCopyChapters());
    }
    
    if (regenerateButton) {
      regenerateButton.addEventListener('click', () => this.handleRegenerateChapters());
    }
    
    if (prevVersionButton) {
      prevVersionButton.addEventListener('click', () => this.handlePrevVersion());
    }
    
    if (nextVersionButton) {
      nextVersionButton.addEventListener('click', () => this.handleNextVersion());
    }
    
    console.log('[UI] Main content event listeners set up');
  }
  
  /**
   * Update the main content
   * @param {Object} state - The current state
   */
  updateMainContent(state) {
    const { video, chapters } = state;
    const { status, videoInfo, videoTitle, loading, chaptersContainer, chaptersContent, 
            prevVersionButton, nextVersionButton, versionIndicator, errorMessage } = this.elements.main;
    
    // Update video info
    if (video.isOnVideoPage && video.id && video.title) {
      if (status) status.classList.add('hidden');
      if (videoInfo) videoInfo.classList.remove('hidden');
      if (videoTitle) videoTitle.textContent = video.title;
    } else {
      if (status) status.classList.remove('hidden');
      if (videoInfo) videoInfo.classList.add('hidden');
    }
    
    // Update loading state
    if (loading) {
      loading.classList.toggle('hidden', !chapters.isGenerating);
    }
    
    // Update chapters
    if (chaptersContainer && chapters.versions.length > 0) {
      chaptersContainer.classList.remove('hidden');
      
      // Get current version
      const currentVersion = chapters.versions[chapters.currentVersionIndex];
      
      // Update chapters content
      if (chaptersContent && currentVersion) {
        chaptersContent.innerHTML = this.formatChaptersHtml(currentVersion);
      }
      
      // Update version controls
      if (versionIndicator) {
        versionIndicator.textContent = `Version ${chapters.currentVersionIndex + 1}/${chapters.versions.length}`;
      }
      
      if (prevVersionButton) {
        prevVersionButton.disabled = chapters.currentVersionIndex === 0;
      }
      
      if (nextVersionButton) {
        nextVersionButton.disabled = chapters.currentVersionIndex === chapters.versions.length - 1;
      }
    } else if (chaptersContainer) {
      chaptersContainer.classList.add('hidden');
    }
    
    // Update error message
    if (errorMessage) {
      if (video.error || chapters.error) {
        errorMessage.textContent = video.error || chapters.error;
        errorMessage.classList.remove('hidden');
      } else {
        errorMessage.classList.add('hidden');
      }
    }
  }
  
  /**
   * Format chapters as HTML
   * @param {Object} chapters - The chapters object
   * @returns {string} The formatted HTML
   */
  formatChaptersHtml(chapters) {
    if (!chapters || !chapters.chapters || chapters.chapters.length === 0) {
      return '<p>No chapters generated.</p>';
    }
    
    const formattedChapters = chapters.chapters.map(chapter => {
      return `<div class="chapter-item">
        <span class="chapter-time">${chapter.time}</span>
        <span class="chapter-title">${chapter.title}</span>
      </div>`;
    }).join('');
    
    return `
      <div class="chapters-text">
        <pre>${chapters.formatted_text}</pre>
      </div>
      <div class="chapters-list">
        ${formattedChapters}
      </div>
    `;
  }
  
  /**
   * Handle generate chapters button click
   */
  async handleGenerateChapters() {
    const state = this.store.getState();
    const { video, credits } = state;
    
    // Check if user has enough credits
    if (credits.count <= 0) {
      this.showNotification('You need credits to generate chapters. Please purchase more credits.', 'error');
      return;
    }
    
    // Check if we have video info
    if (!video.id || !video.title) {
      this.showNotification('No video detected. Please make sure you are on a YouTube video page.', 'error');
      return;
    }
    
    // Dispatch generate start action
    this.store.dispatch('chapters', { type: 'GENERATE_START' });
    
    try {
      // Generate chapters
      const result = await this.api.generateChapters(video.id, video.title);
      
      // Dispatch generate success action
      this.store.dispatch('chapters', { 
        type: 'GENERATE_SUCCESS', 
        payload: { chapters: result.data }
      });
      
      // Decrement credits
      this.store.dispatch('credits', { type: 'DECREMENT_CREDITS' });
      
      // Save state to storage
      await this.store.saveToStorage();
      
      this.showNotification('Chapters generated successfully!', 'success');
    } catch (error) {
      console.error('[UI] Error generating chapters:', error);
      
      // Dispatch generate failure action
      this.store.dispatch('chapters', { 
        type: 'GENERATE_FAILURE', 
        payload: { error: error.message }
      });
      
      this.showNotification(`Error generating chapters: ${error.message}`, 'error');
    }
  }
  
  /**
   * Handle copy chapters button click
   */
  handleCopyChapters() {
    const state = this.store.getState();
    const { chapters } = state;
    
    // Get current version
    const currentVersion = chapters.versions[chapters.currentVersionIndex];
    
    if (!currentVersion || !currentVersion.formatted_text) {
      this.showNotification('No chapters to copy.', 'error');
      return;
    }
    
    // Copy to clipboard
    navigator.clipboard.writeText(currentVersion.formatted_text)
      .then(() => {
        this.showNotification('Chapters copied to clipboard!', 'success');
      })
      .catch(error => {
        console.error('[UI] Error copying to clipboard:', error);
        this.showNotification('Error copying to clipboard. Please try again.', 'error');
      });
  }
  
  /**
   * Handle regenerate chapters button click
   */
  handleRegenerateChapters() {
    // Just call handleGenerateChapters
    this.handleGenerateChapters();
  }
  
  /**
   * Handle previous version button click
   */
  handlePrevVersion() {
    const state = this.store.getState();
    const { chapters } = state;
    
    if (chapters.currentVersionIndex > 0) {
      this.store.dispatch('chapters', { 
        type: 'SET_VERSION_INDEX', 
        payload: { index: chapters.currentVersionIndex - 1 }
      });
    }
  }
  
  /**
   * Handle next version button click
   */
  handleNextVersion() {
    const state = this.store.getState();
    const { chapters } = state;
    
    if (chapters.currentVersionIndex < chapters.versions.length - 1) {
      this.store.dispatch('chapters', { 
        type: 'SET_VERSION_INDEX', 
        payload: { index: chapters.currentVersionIndex + 1 }
      });
    }
  }
  
  /**
   * Handle logout button click
   */
  async handleLogout() {
    // Dispatch logout action
    this.store.dispatch('auth', { type: 'LOGOUT' });
    
    // Clear chapters
    this.store.dispatch('chapters', { type: 'CLEAR_CHAPTERS' });
    
    // Set active view to welcome
    this.store.dispatch('ui', { 
      type: 'SET_ACTIVE_VIEW', 
      payload: { view: 'welcome' } 
    });
    
    // Close menu
    this.store.dispatch('ui', { type: 'CLOSE_MENU' });
    
    // Save state to storage
    await this.store.saveToStorage();
    
    this.showNotification('You have been logged out.', 'info');
  }
  
  /**
   * Show a notification
   * @param {string} message - The notification message
   * @param {string} type - The notification type (success, error, info)
   */
  showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Add close button
    const closeButton = document.createElement('button');
    closeButton.className = 'notification-close';
    closeButton.innerHTML = '&times;';
    closeButton.addEventListener('click', () => {
      notification.remove();
    });
    
    notification.appendChild(closeButton);
    
    // Add to document
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      notification.classList.add('notification-hide');
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
window.YCG_UI = new UiManager();
