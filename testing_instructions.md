# Testing Instructions for Google Login

## Setup

1. Start the local test server:
   ```bash
   python test_server.py
   ```

2. Load the extension in Chrome:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode" in the top right
   - Click "Load unpacked" and select the `dist` folder
   - Make sure the extension is enabled

## Testing

1. Click on the extension icon to open the popup
2. You should see the welcome screen with a "Sign in with Google" button
3. Click the "Sign in with Google" button
4. Chrome will prompt you to select an account and grant permissions
5. After selecting an account, the extension should authenticate with the local test server
6. If successful, you should see the main content screen with your credit balance

## Debugging

If you encounter any issues:

1. Right-click on the extension popup and select "Inspect" to open the DevTools
2. Check the Console tab for any error messages
3. Look for logs starting with "[Auth]" which provide detailed information about the authentication process
4. Check the Network tab to see the requests being made to the server
5. Check the server logs in the terminal where you started the test server

## Common Issues and Solutions

### "Cannot read properties of null" error
- This usually means a DOM element is missing or not found
- Check the HTML structure in popup.html
- Make sure all element IDs match what's being referenced in auth.js

### "Login failed: 500" error
- This indicates a server-side error
- Check the server logs for more details
- Make sure the server is running and accessible

### "chrome.identity API is not available" error
- Make sure the extension has the "identity" permission in manifest.json
- Check that the OAuth2 configuration is correct in manifest.json

### "Invalid response from server" error
- Check the response format from the server
- Make sure it matches what the extension is expecting

## Next Steps After Fixing Google Login

Once the Google login is working properly:

1. Switch back to using the production server:
   - In `extension/js/auth.js`, change `USE_LOCAL_SERVER` to `false`
   - Rebuild the extension

2. Fix any server-side issues:
   - Check the Vercel logs for errors
   - Update the server code as needed

3. Proceed with implementing the monetization features as outlined in the implementation plan
