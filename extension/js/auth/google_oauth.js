// Handles Google OAuth logic
export async function launchGoogleSignIn() {
  return new Promise((resolve, reject) => {
    try {
      const timeoutId = setTimeout(() => {
        reject(new Error("Google authentication timed out"));
      }, 15000);
      chrome.identity.clearAllCachedAuthTokens(() => {
        chrome.identity.getAuthToken({ interactive: true }, (token) => {
          clearTimeout(timeoutId);
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
            return;
          }
          if (!token) {
            reject(new Error("Failed to get auth token"));
            return;
          }
          resolve(token);
        });
      });
    } catch (error) {
      reject(error);
    }
  });
}
