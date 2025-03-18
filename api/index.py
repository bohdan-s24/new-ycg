from flask import Flask, request, jsonify, make_response
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._transcripts import Transcript
from youtube_transcript_api.formatters import TextFormatter
import openai
import os
from flask_cors import CORS
import json
import time
import uuid
import requests
from dotenv import load_dotenv
import http.client
import urllib.request
import ssl
import traceback
import sys

# Load environment variables from .env file if present
try:
    load_dotenv()
    print("Environment variables loaded from .env file")
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")

app = Flask(__name__)
# Enable CORS for all routes and all origins (including Chrome extensions)
CORS(app, resources={r"/*": {"origins": "*"}})

# For handling preflight requests explicitly
@app.route('/api/generate-chapters', methods=['OPTIONS'])
def handle_options():
    response = make_response()
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept')
    response.headers.add('Access-Control-Allow-Methods', 'POST')
    return response

# Get API keys from environment variables with fallbacks to prevent errors
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
WEBSHARE_USERNAME = os.environ.get("WEBSHARE_USERNAME", "")
WEBSHARE_PASSWORD = os.environ.get("WEBSHARE_PASSWORD", "")

# Set OpenAI API key if available
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
    print("OpenAI API key configured")
else:
    print("Warning: OpenAI API key not found in environment variables")

# Set up Webshare proxy if credentials are available
webshare_proxy = None
if WEBSHARE_USERNAME and WEBSHARE_PASSWORD:
    webshare_proxy = {
        'http': f'http://{WEBSHARE_USERNAME}:{WEBSHARE_PASSWORD}@p.webshare.io:80/',
        'https': f'http://{WEBSHARE_USERNAME}:{WEBSHARE_PASSWORD}@p.webshare.io:80/'
    }
    print("Webshare proxy configured")
else:
    print("No Webshare proxy configured")

# Generate a session ID for requests to ensure user requests don't get mixed up
def generate_session_id():
    return str(uuid.uuid4())

# Cache for API status checks to reduce load
api_status_cache = {
    'timestamp': 0,
    'data': None
}

@app.route('/api', methods=['GET'])
def hello():
    try:
        proxy_status = {
            'configured': bool(webshare_proxy),
            'username': bool(WEBSHARE_USERNAME),
            'password': bool(WEBSHARE_PASSWORD)
        }
        
        # Include Python version and environment info for diagnostics
        env_info = {
            'python_version': sys.version,
            'openai_key_configured': bool(OPENAI_API_KEY),
            'env_vars': list(os.environ.keys())[:5]  # Just show first 5 for security
        }
        
        return jsonify({
            'status': 'online',
            'message': 'YouTube Chapter Generator API is running',
            'webshare_proxy_configured': bool(webshare_proxy),
            'proxy_status': proxy_status,
            'env_info': env_info,
            'cors_headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Accept',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            }
        })
    except Exception as e:
        print(f"Error in /api route: {e}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': 'API is running but encountered an error',
            'error': str(e)
        }), 200  # Return 200 even on error for diagnostic purposes

def get_transcript(video_id, language_code='en'):
    """
    Get transcript for a YouTube video using youtube-transcript-api
    
    This function follows the recommended approach from the youtube-transcript-api 
    documentation for working around IP blocks using proxies.
    """
    try:
        # First attempt: Try without proxy
        try:
            print(f"Attempting to get transcript for {video_id} without proxy...")
            return YouTubeTranscriptApi.get_transcript(video_id, languages=[language_code])
        except Exception as e:
            print(f"Failed to get transcript without proxy: {e}")
            if not webshare_proxy:
                # If no proxy is configured, re-raise the exception
                raise
        
        # Second attempt: Try with Webshare proxy if configured
        if webshare_proxy:
            print(f"Attempting to get transcript for {video_id} with Webshare proxy...")
            try:
                return YouTubeTranscriptApi.get_transcript(
                    video_id, 
                    languages=[language_code],
                    proxies=webshare_proxy
                )
            except Exception as e:
                print(f"Failed to get transcript with Webshare proxy: {e}")
                raise
    except Exception as e:
        print(f"All transcript fetching methods failed: {e}")
        traceback.print_exc()
        raise Exception(f"Could not retrieve transcript: {str(e)}")

@app.route('/api/generate-chapters', methods=['POST'])
def generate_chapters():
    # Generate a unique session ID for this request
    session_id = generate_session_id()
    
    # Add CORS headers explicitly for this endpoint
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Accept',
        'Access-Control-Allow-Methods': 'POST,OPTIONS'
    }
    
    try:
        # Validate OpenAI API key first
        if not OPENAI_API_KEY:
            return jsonify({
                'success': False,
                'error': 'OpenAI API key is not configured on the server.',
                'session_id': session_id
            }), 400, response_headers
        
        # Get data from request
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided in the request',
                'session_id': session_id
            }), 400, response_headers
        
        video_id = data.get('video_id')
        
        if not video_id:
            return jsonify({
                'success': False,
                'error': 'No video ID provided',
                'session_id': session_id
            }), 400, response_headers
        
        print(f"Processing request for video_id: {video_id} with session_id: {session_id}")
        
        # Get transcript using YouTube Transcript API (with proxy if needed)
        transcript_list = get_transcript(video_id)
        
        if not transcript_list:
            return jsonify({
                'success': False,
                'error': 'No transcript found for this video',
                'session_id': session_id,
                'video_id': video_id
            }), 404, response_headers
        
        # Calculate video duration in minutes
        if transcript_list:
            last_entry = transcript_list[-1]
            video_duration_seconds = last_entry['start'] + last_entry['duration']
            video_duration_minutes = video_duration_seconds / 60
        else:
            video_duration_minutes = 0
            video_duration_seconds = 0
        
        print(f"Video duration for {video_id}: {video_duration_minutes:.2f} minutes")
        
        # Convert to plain text with timestamps for OpenAI
        formatted_transcript = ""
        for item in transcript_list:
            timestamp = format_time(item['start'])
            formatted_transcript += f"{timestamp} - {item['text']}\n"
        
        # Create system prompt with instructions based on video length
        system_prompt = (
            "You are a YouTube chapter creator. Create concise, descriptive chapters for this video "
            "based on topic changes. Each chapter should be 2-4 minutes long. The first chapter "
            "should always start at 00:00."
            "\n\n"
            "Format your response as a list of timestamps and titles only, like:\n"
            "00:00 Introduction\n"
            "02:30 First Topic\n"
            "05:45 Second Topic"
            "\n\n"
        )
        
        # Adjust number of chapters based on video length
        if video_duration_minutes <= 10:
            system_prompt += "Provide 3-5 chapters."
        elif video_duration_minutes <= 20:
            system_prompt += "Provide 5-7 chapters."
        elif video_duration_minutes <= 40:
            system_prompt += "Provide 7-10 chapters."
        else:
            system_prompt += "Provide 10-15 chapters."
        
        print(f"Calling OpenAI for video {video_id} with transcript length: {len(formatted_transcript)} chars")
        
        try:
            # Get chapter suggestions from OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Using the most capable model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Here is the transcript with timestamps for YouTube video ID {video_id}:\n\n{formatted_transcript}"}
                ]
            )
            
            chapters = response.choices[0].message.content
            
            print(f"Generated chapters for {video_id}: {len(chapters.split('\\n'))} chapters")
        except Exception as openai_error:
            print(f"OpenAI API error: {openai_error}")
            traceback.print_exc()
            return jsonify({
                "success": False,
                "error": f"OpenAI API error: {str(openai_error)}",
                "session_id": session_id,
                "video_id": video_id
            }), 500, response_headers
        
        # Create response with CORS headers
        result = jsonify({
            "success": True,
            "chapters": chapters,
            "session_id": session_id,
            "video_id": video_id,
            "video_duration": format_time(video_duration_seconds),
            "used_proxy": bool(webshare_proxy)
        })
        
        # Add CORS headers to response
        for key, value in response_headers.items():
            result.headers.add(key, value)
        
        return result
        
    except Exception as e:
        print(f"Error in generate_chapters: {e}")
        traceback.print_exc()
        
        error_response = jsonify({
            "success": False,
            "error": str(e),
            "session_id": session_id,
            "video_id": video_id if 'video_id' in locals() else None
        })
        
        # Add CORS headers to error response
        for key, value in response_headers.items():
            error_response.headers.add(key, value)
        
        return error_response, 500

def format_time(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

# For local development
if __name__ == '__main__':
    app.run(debug=True) 