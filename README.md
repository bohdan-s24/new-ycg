# YouTube Chapter Generator

A Chrome extension that automatically generates YouTube video chapters using AI.

## Features

- Extracts transcripts directly from YouTube videos
- Uses OpenAI GPT-4 to generate meaningful chapters based on content
- Creates properly formatted YouTube chapters ready to copy
- Simple, user-friendly interface
- Works with any YouTube video that has captions/subtitles

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
  - YouTube Transcript API
  - OpenAI API
  - Flask for API endpoints

## Development

### Setup Backend

1. Install requirements:
```
pip install -r requirements.txt
```

2. Set up environment variables:
```
OPENAI_API_KEY=your_api_key_here
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

## License

This project is licensed under the MIT License.
