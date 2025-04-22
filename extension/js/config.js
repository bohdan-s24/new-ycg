/**
 * Configuration for the YouTube Chapter Generator extension
 */
"use strict";
(function() {
  const CONFIG = {
    // API endpoints
    API_BASE_URL: "https://new-ycg.vercel.app",
    AUTH_BASE_URL: "https://new-ycg.vercel.app/v1/auth",

    // Google OAuth client ID
    GOOGLE_CLIENT_ID: "373897257675-i561f2gcpv310b61bptj0ge2bmvdm03m.apps.googleusercontent.com",
  };

  // Export the configuration
  window.YCG_CONFIG = CONFIG;

  // Stripe Price IDs for credit packs
  window.YCG_CONFIG.STRIPE_PRICE_IDS = {
    ONE_TIME_10: 'price_1RGefhF7Kryr2ZRb4GUtKKvj',
    ONE_TIME_50: 'price_1RGefRF7Kryr2ZRbmpxIKe7S',
    SUBSCRIPTION_10: 'price_1RGef7F7Kryr2ZRb9FWp5g7v',
    SUBSCRIPTION_50: 'price_1RGenMF7Kryr2ZRbrNPx4BVb',
  };

  // Stripe publishable key (for frontend Stripe.js)
  window.YCG_CONFIG.STRIPE_PUBLISHABLE_KEY = process.env.STRIPE_PUBLISHABLE_KEY || '<YOUR_PUBLISHABLE_KEY_HERE>';
})();
