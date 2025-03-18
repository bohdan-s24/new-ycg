# YouTube Chapter Generator

A Chrome extension that automatically generates YouTube video chapters using AI.

## Features

- Extracts transcripts directly from YouTube videos
- Uses OpenAI GPT-4 to generate meaningful chapters based on content
- Creates properly formatted YouTube chapters ready to copy
- Simple, user-friendly interface
- Works with any YouTube video that has captions/subtitles
- Supports Webshare proxies to avoid IP blocks

## How It Works

1. The extension extracts the video ID from the current YouTube page
2. It sends the video ID to our server
3. The server fetches the transcript using the YouTube Transcript API
4. The transcript is sent to OpenAI's API to analyze content and generate chapters
5. The generated chapters are returned to the extension and displayed to the user

## Technology Stack

- **Frontend**: Chrome Extension with vanilla JavaScript
- **Backend**: Python Flask API deployed on Vercel
- **Libraries**:
  - YouTube Transcript API (for transcript extraction)
  - OpenAI API (for intelligent chapter generation)
  - Flask for API endpoints (with CORS support)

## Development

### Setup Backend

1. Install requirements:
```
pip install -r requirements.txt
```

2. Set up environment variables:
```
OPENAI_API_KEY=your_api_key_here
WEBSHARE_USERNAME=your_webshare_username
WEBSHARE_PASSWORD=your_webshare_password
```

3. Run locally:
```
cd api
python index.py
```

### Setup Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" in the top right
3. Click "Load unpacked" and select the `extension` folder

## Deployment

The backend is automatically deployed to Vercel when changes are pushed to the main branch.

### Vercel Environment Variables

To ensure proper functionality, set these environment variables in your Vercel project:

1. `OPENAI_API_KEY` - Your OpenAI API key
2. `WEBSHARE_USERNAME` - Your Webshare proxy username (if using Webshare)
3. `WEBSHARE_PASSWORD` - Your Webshare proxy password (if using Webshare)

## Using Webshare Proxies

To avoid YouTube IP blocks, this project supports Webshare proxies:

1. **Purchase a Webshare Package**: 
   - Sign up for [Webshare](https://www.webshare.io/)
   - Purchase a "Residential" proxy package (NOT "Proxy Server" or "Static Residential")

2. **Configure Proxies**:
   - Find your proxy credentials in Webshare dashboard
   - Add them to your environment variables (see above)

3. **Vercel Configuration**:
   - Add the variables to your Vercel project settings
   - Redeploy the application

The API will automatically use the proxies if they are configured, falling back to direct access if not.

## Troubleshooting

### CORS Issues
If you see CORS errors in the console:
- Ensure the Vercel deployment has completed
- Check that the API is accessible
- Verify that the headers in vercel.json are correct
- Check browser console for specific error messages

### Proxy Issues
If the proxy is not working:
- Check the Webshare account status
- Verify the credentials are correct
- Ensure you're using Residential proxies (not other types)
- Check the server logs for connection errors

## License

This project is licensed under the MIT License.

## Latest Update
Updated on June 3, 2024 with improved CORS handling and better proxy integration.
