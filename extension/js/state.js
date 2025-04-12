/**
 * YouTube Chapter Generator State Management Module
 *
 * This module provides a centralized state management system for the extension.
 * It uses a simple pub/sub pattern to notify components of state changes.
 */

// Define the initial state
const initialState = {
  // Auth state
  auth: {
    isAuthenticated: false,
    user: null,
    token: null,
    isLoading: false,
    error: null,
  },

  // Video state
  video: {
    id: null,
    title: null,
    isOnVideoPage: false,
    error: null,
  },

  // Chapters state
  chapters: {
    versions: [],
    currentVersionIndex: 0,
    isGenerating: false,
    error: null,
  },

  // Credits state
  credits: {
    count: 0,
    isLoading: false,
    error: null,
  },

  // UI state
  ui: {
    activeView: "welcome", // 'welcome', 'auth', 'main'
    isMenuOpen: false,
    notifications: [],
  },
}

// Create the state store
class Store {
  constructor(initialState) {
    this.state = { ...initialState }
    this.listeners = []
    this.reducers = {}
  }

  /**
   * Get the current state
   * @returns {Object} The current state
   */
  getState() {
    return { ...this.state }
  }

  /**
   * Register a reducer function for a specific state slice
   * @param {string} sliceName - The name of the state slice
   * @param {Function} reducer - The reducer function
   */
  registerReducer(sliceName, reducer) {
    this.reducers[sliceName] = reducer
  }

  /**
   * Dispatch an action to update the state
   * @param {string} sliceName - The name of the state slice to update
   * @param {Object} action - The action object with type and payload
   */
  dispatch(sliceName, action) {
    console.log(`[STORE-DEBUG] Dispatching action to ${sliceName}:`, action)

    if (!this.reducers[sliceName]) {
      console.error(`[Store] No reducer registered for slice: ${sliceName}`)
      return
    }

    const currentSliceState = this.state[sliceName]
    console.log(`[STORE-DEBUG] Current state for ${sliceName}:`, currentSliceState)
    
    const newSliceState = this.reducers[sliceName](currentSliceState, action)
    console.log(`[STORE-DEBUG] New state for ${sliceName}:`, newSliceState)

    // Update the state
    this.state = {
      ...this.state,
      [sliceName]: newSliceState,
    }

    console.log(`[STORE-DEBUG] Full state after update:`, this.state)

    // Notify listeners
    console.log(`[STORE-DEBUG] Notifying ${this.listeners.length} listeners`)
    this.notifyListeners()
  }

  /**
   * Subscribe to state changes
   * @param {Function} listener - The listener function
   * @returns {Function} A function to unsubscribe
   */
  subscribe(listener) {
    this.listeners.push(listener)

    // Return unsubscribe function
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener)
    }
  }

  /**
   * Notify all listeners of state changes
   */
  notifyListeners() {
    this.listeners.forEach((listener) => listener(this.state))
  }

  /**
   * Reset the state to initial values
   */
  reset() {
    this.state = { ...initialState }
    this.notifyListeners()
  }

  /**
   * Save the state to chrome.storage.local
   */
  async saveToStorage() {
    try {
      // Check if chrome is defined (running in extension context)
      if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
        // Only save persistent parts of the state
        const persistentState = {
          auth: {
            isAuthenticated: this.state.auth.isAuthenticated,
            user: this.state.auth.user,
            token: this.state.auth.token,
          },
          credits: {
            count: this.state.credits.count,
          },
        }

        await chrome.storage.local.set({ ycg_state: persistentState })
        console.log("[Store] State saved to storage")
      } else {
        console.warn("[Store] chrome.storage.local is not available. State not saved.")
      }
    } catch (error) {
      console.error("[Store] Error saving state to storage:", error)
    }
  }

  /**
   * Load the state from chrome.storage.local
   */
  async loadFromStorage() {
    try {
      // Check if chrome is defined (running in extension context)
      if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
        const result = await chrome.storage.local.get("ycg_state")
        const savedState = result.ycg_state

        if (savedState) {
          // Merge saved state with initial state
          this.state = {
            ...this.state,
            auth: {
              ...this.state.auth,
              ...savedState.auth,
            },
            credits: {
              ...this.state.credits,
              ...savedState.credits,
            },
          }

          console.log("[Store] State loaded from storage")
          this.notifyListeners()
        }
      } else {
        console.warn("[Store] chrome.storage.local is not available. State not loaded.")
      }
    } catch (error) {
      console.error("[Store] Error loading state from storage:", error)
    }
  }
}

// Create reducers for each state slice
const authReducer = (state, action) => {
  console.log("[STORE-DEBUG] Auth reducer called with action:", action.type)
  console.log("[STORE-DEBUG] Current auth state:", state)
  
  switch (action.type) {
    case "LOGIN_START":
      const loginStartState = {
        ...state,
        isLoading: true,
        error: null,
      }
      console.log("[STORE-DEBUG] New auth state after LOGIN_START:", loginStartState)
      return loginStartState
      
    case "LOGIN_SUCCESS":
      const loginSuccessState = {
        ...state,
        isAuthenticated: true,
        user: action.payload.user,
        token: action.payload.token,
        isLoading: false,
        error: null,
      }
      console.log("[STORE-DEBUG] New auth state after LOGIN_SUCCESS:", loginSuccessState)
      return loginSuccessState
      
    case "LOGIN_FAILURE":
      const loginFailureState = {
        ...state,
        isAuthenticated: false,
        user: null,
        token: null,
        isLoading: false,
        error: action.payload.error,
      }
      console.log("[STORE-DEBUG] New auth state after LOGIN_FAILURE:", loginFailureState)
      console.log("[STORE-DEBUG] Error:", action.payload.error)
      return loginFailureState
      
    case "LOGOUT":
      const logoutState = {
        ...state,
        isAuthenticated: false,
        user: null,
        token: null,
        isLoading: false,
        error: null,
      }
      console.log("[STORE-DEBUG] New auth state after LOGOUT:", logoutState)
      return logoutState
      
    case "UPDATE_USER":
      const updateUserState = {
        ...state,
        user: {
          ...state.user,
          ...action.payload,
        },
      }
      console.log("[STORE-DEBUG] New auth state after UPDATE_USER:", updateUserState)
      return updateUserState
      
    default:
      return state
  }
}

const videoReducer = (state, action) => {
  switch (action.type) {
    case "SET_VIDEO_INFO":
      return {
        ...state,
        id: action.payload.id,
        title: action.payload.title,
        isOnVideoPage: true,
        error: null,
      }
    case "CLEAR_VIDEO_INFO":
      return {
        ...state,
        id: null,
        title: null,
        isOnVideoPage: false,
        error: null,
      }
    case "SET_VIDEO_ERROR":
      return {
        ...state,
        error: action.payload.error,
        isOnVideoPage: false,
      }
    default:
      return state
  }
}

const chaptersReducer = (state, action) => {
  switch (action.type) {
    case "GENERATE_START":
      return {
        ...state,
        isGenerating: true,
        error: null,
      }
    case "GENERATE_SUCCESS":
      // Add new version to versions array
      const newVersions = [...state.versions, action.payload.chapters]
      return {
        ...state,
        versions: newVersions,
        currentVersionIndex: newVersions.length - 1,
        isGenerating: false,
        error: null,
      }
    case "GENERATE_FAILURE":
      return {
        ...state,
        isGenerating: false,
        error: action.payload.error,
      }
    case "SET_VERSION_INDEX":
      return {
        ...state,
        currentVersionIndex: action.payload.index,
      }
    case "CLEAR_CHAPTERS":
      return {
        ...state,
        versions: [],
        currentVersionIndex: 0,
        isGenerating: false,
        error: null,
      }
    default:
      return state
  }
}

const creditsReducer = (state, action) => {
  switch (action.type) {
    case "SET_CREDITS":
      return {
        ...state,
        count: action.payload.count,
        isLoading: false,
        error: null,
      }
    case "LOADING_CREDITS":
      return {
        ...state,
        isLoading: true,
        error: null,
      }
    case "CREDITS_ERROR":
      return {
        ...state,
        isLoading: false,
        error: action.payload.error,
      }
    case "DECREMENT_CREDITS":
      return {
        ...state,
        count: Math.max(0, state.count - 1),
      }
    default:
      return state
  }
}

const uiReducer = (state, action) => {
  console.log("[STORE-DEBUG] UI reducer called with action:", action.type)
  console.log("[STORE-DEBUG] Current UI state:", state)
  
  switch (action.type) {
    case "SET_ACTIVE_VIEW":
      const setActiveViewState = {
        ...state,
        activeView: action.payload.view,
      }
      console.log("[STORE-DEBUG] New UI state after SET_ACTIVE_VIEW:", setActiveViewState)
      console.log("[STORE-DEBUG] Active view changed to:", action.payload.view)
      return setActiveViewState
      
    case "TOGGLE_MENU":
      return {
        ...state,
        isMenuOpen: !state.isMenuOpen,
      }
    case "CLOSE_MENU":
      return {
        ...state,
        isMenuOpen: false,
      }
    case "ADD_NOTIFICATION":
      return {
        ...state,
        notifications: [...state.notifications, action.payload.notification],
      }
    case "REMOVE_NOTIFICATION":
      return {
        ...state,
        notifications: state.notifications.filter((n) => n.id !== action.payload.id),
      }
    case "CLEAR_NOTIFICATIONS":
      return {
        ...state,
        notifications: [],
      }
    default:
      return state
  }
}

// Create and initialize the store
const store = new Store(initialState)

// Register reducers
store.registerReducer("auth", authReducer)
store.registerReducer("video", videoReducer)
store.registerReducer("chapters", chaptersReducer)
store.registerReducer("credits", creditsReducer)
store.registerReducer("ui", uiReducer)

// Export the store
window.YCG_STORE = store
