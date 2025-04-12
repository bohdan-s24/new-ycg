// Configuration for the YouTube Chapter Generator extension
const CONFIG = {
  // API endpoints
  API_BASE_URL: "https://new-ycg.vercel.app/api",
  AUTH_BASE_URL: "https://new-ycg.vercel.app/auth", // Remove /api prefix

  // Google OAuth - This will be replaced during build with the actual client ID
  GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID || "GOOGLE_CLIENT_ID_PLACEHOLDER"
};

// Export the configuration
window.YCG_CONFIG = CONFIG;
