// Configuration for the YouTube Chapter Generator extension
const CONFIG = {
  // API endpoints
  API_BASE_URL: "https://new-ycg.vercel.app",
  AUTH_BASE_URL: "https://new-ycg.vercel.app/v1/auth",

  // Google OAuth client ID
  GOOGLE_CLIENT_ID: "YOUR_GOOGLE_CLIENT_ID_HERE" // Replace with your actual Google Client ID
};

// Export the configuration
window.YCG_CONFIG = CONFIG;
