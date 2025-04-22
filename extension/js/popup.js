/**
 * YouTube Chapter Generator Popup Script
 *
 * This is the main entry point for the popup UI.
 */

"use strict";

(function() {
  // Initialize when DOM is loaded
  document.addEventListener("DOMContentLoaded", () => {
    console.log("[POPUP-DEBUG] DOM content loaded, waiting for services to initialize");

    // Log available services
    const checkServices = () => {
      console.log("[POPUP-DEBUG] Available services:", {
        store: !!window.YCG_STORE,
        api: !!window.YCG_API,
        video: !!window.YCG_VIDEO,
        ui: !!window.YCG_UI,
      });

      // We only require the store and UI to be available
      // API and video services are optional and can be handled gracefully if missing
      return window.YCG_STORE && window.YCG_UI;
    };

    // Try to initialize with increasing delays
    const tryInit = (attempt = 1, maxAttempts = 5) => {
      console.log(`[POPUP-DEBUG] Initialization attempt ${attempt}/${maxAttempts}`);

      if (checkServices()) {
        console.log("[POPUP-DEBUG] All services available, initializing popup");
        init();
        return;
      }

      if (attempt < maxAttempts) {
        const delay = 100 * Math.pow(2, attempt - 1); // Exponential backoff
        console.log(`[POPUP-DEBUG] Services not ready, retrying in ${delay}ms`);
        setTimeout(() => tryInit(attempt + 1, maxAttempts), delay);
      } else {
        console.error("[POPUP-DEBUG] Failed to initialize after multiple attempts");
        // Try to initialize with whatever services are available
        if (window.YCG_STORE) {
          console.log("[POPUP-DEBUG] Attempting initialization with partial services");
          init();
        }
      }
    };

    // Start initialization attempts
    tryInit();
  });

  /**
   * Initialize the popup
   */
  async function init() {
    console.log("[POPUP-DEBUG] Initializing popup...");

    // Get references to the store, API, and video service
    const store = window.YCG_STORE;
    const api = window.YCG_API;
    const video = window.YCG_VIDEO;
    const ui = window.YCG_UI;

    console.log("[POPUP-DEBUG] Services for initialization:", {
      store: !!store,
      api: !!api,
      video: !!video,
      ui: !!ui
    });

    // Check if user is logged in (for logging purposes)
    const isUserLoggedIn = store && store.getState().auth && store.getState().auth.isAuthenticated;
    console.log("[POPUP-DEBUG] User login status:", isUserLoggedIn ? "logged in" : "not logged in");

    // Always initialize video service if available
    // The video service will internally decide whether to check for videos based on login state
    if (video) {
      console.log("[POPUP-DEBUG] Initializing video service");
      video.init();
    } else {
      console.warn("[POPUP-DEBUG] Video service not available");
    }

    // Check API availability only if API service is available
    if (api) {
      try {
        console.log("[POPUP-DEBUG] Checking API availability");
        const isApiAvailable = await api.ping().catch(error => {
          console.warn("[POPUP-DEBUG] API ping failed:", error);
          return false;
        });

        console.log("[POPUP-DEBUG] API availability check result:", isApiAvailable);

        if (!isApiAvailable) {
          console.warn("[POPUP-DEBUG] API is not available");
          if (ui) {
            // Only show notification if user is logged in, as API is not needed for login screen
            if (isUserLoggedIn) {
              ui.showNotification("Server is not available. Some features may be limited.", "warning");
            }
          }
        }
      } catch (error) {
        console.warn("[POPUP-DEBUG] Error checking API availability:", error);
      }
    } else {
      console.warn("[POPUP-DEBUG] API service not available, continuing with limited functionality");
    }

    // Set up event listeners for popup-specific functionality
    console.log("[POPUP-DEBUG] Setting up popup event listeners");
    setupPopupEventListeners();

    // Force UI update if UI service is available
    if (ui && store) {
      console.log("[POPUP-DEBUG] Forcing UI update");
      ui.updateUI(store.getState());
    }

    console.log("[POPUP-DEBUG] Initialization complete");
  }

  /**
   * Set up popup-specific event listeners
   */
  function setupPopupEventListeners() {
    // Terms and privacy links
    const termsLink = document.getElementById("terms-link");
    const privacyLink = document.getElementById("privacy-link");
    const myAccountLink = document.getElementById("my-account-link");
    const feedbackLink = document.getElementById("feedback-link");
    const purchaseOptions = document.getElementById("purchase-options");
    const purchaseBtns = document.querySelectorAll(".purchase-btn");

    if (termsLink) {
      termsLink.addEventListener("click", (event) => {
        event.preventDefault();
        chrome.tabs.create({ url: "https://new-ycg.vercel.app/terms" });
      });
    }

    if (privacyLink) {
      privacyLink.addEventListener("click", (event) => {
        event.preventDefault();
        chrome.tabs.create({ url: "https://new-ycg.vercel.app/privacy" });
      });
    }

    if (myAccountLink) {
      myAccountLink.addEventListener("click", (event) => {
        event.preventDefault();
        // Toggle purchase options
        if (purchaseOptions) {
          purchaseOptions.classList.toggle("hidden");
          console.log("[BUY-CREDITS] Toggled purchase options. Hidden:", purchaseOptions.classList.contains("hidden"));
        }
      });
    }

    if (feedbackLink) {
      feedbackLink.addEventListener("click", async (event) => {
        event.preventDefault();
        // Lazy load feedback module only when feedback is clicked
        const feedbackModule = await import("./popup_feedback.js");
        feedbackModule.openFeedbackForm();
      });
    }

    // Purchase button logic
    if (purchaseBtns && window.YCG_API) {
      purchaseBtns.forEach(btn => {
        btn.addEventListener("click", async (event) => {
          event.preventDefault();
          const priceId = btn.getAttribute("data-price-id");
          const mode = btn.getAttribute("data-mode");
          console.log(`[BUY-CREDITS] Purchase button clicked. priceId=${priceId}, mode=${mode}`);
          if (!priceId || !mode) {
            console.warn("[BUY-CREDITS] Missing priceId or mode.", { priceId, mode });
            return;
          }
          btn.disabled = true;
          btn.textContent = "Redirecting...";
          try {
            const result = await window.YCG_API.createCheckoutSession(priceId, mode);
            console.log("[BUY-CREDITS] createCheckoutSession result:", result);
            if (result && result.success && result.data && result.data.url) {
              window.open(result.data.url, "_blank");
            } else {
              alert("Failed to create Stripe checkout session. Please try again.");
            }
          } catch (e) {
            console.error("[BUY-CREDITS] Error during checkout:", e);
            alert("Error: " + (e.message || e));
          } finally {
            btn.disabled = false;
            btn.textContent = btn.getAttribute("data-mode") === "payment" ?
              (btn.getAttribute("data-price-id") === "price_1RGefhF7Kryr2ZRb4GUtKKvj" ? "10 Credits – $9 (One-Time)" : "50 Credits – $29 (One-Time)") :
              (btn.getAttribute("data-price-id") === "price_1RGef7F7Kryr2ZRb9FWp5g7v" ? "10 Credits – $9/mo (Subscription)" : "50 Credits – $29/mo (Subscription)");
          }
        });
      });
    }
  }
})();
