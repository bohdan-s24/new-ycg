// Configuration for the YouTube Chapter Generator extension
const CONFIG = {
  // API endpoints
  API_BASE_URL: "https://new-ycg.vercel.app/api",
  AUTH_BASE_URL: "https://new-ycg.vercel.app/auth", // Remove /api prefix

  // Google OAuth
  GOOGLE_CLIENT_ID: "373897257675-i561f2gcpv310b61bptj0ge2bmvdm03m.apps.googleusercontent.com"
};

// Export the configuration
window.YCG_CONFIG = CONFIG;
