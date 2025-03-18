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

# Load environment variables from .env file if present
load_dotenv()

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

# Get API keys from environment variables
openai.api_key = os.environ.get("OPENAI_API_KEY")
WEBSHARE_USERNAME = os.environ.get("WEBSHARE_USERNAME")
WEBSHARE_PASSWORD = os.environ.get("WEBSHARE_PASSWORD")

# Configure HTTP/HTTPS proxies if Webshare credentials are available
proxies = None
if WEBSHARE_USERNAME and WEBSHARE_PASSWORD:
    proxy_url = f"http://{WEBSHARE_USERNAME}:{WEBSHARE_PASSWORD}@p.webshare.io:80"
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    # Set environment variables for libraries that use them
    os.environ['HTTP_PROXY'] = proxy_url
    os.environ['HTTPS_PROXY'] = proxy_url
    print("Webshare proxy configured")
else:
    print("No Webshare proxy configured")

# Generate a session ID for requests to ensure user requests don't get mixed up
def generate_session_id():
    return str(uuid.uuid4())

@app.route('/api', methods=['GET'])
def hello():
    proxy_status = {
        'configured': bool(proxies),
        'username': bool(WEBSHARE_USERNAME),
        'password': bool(WEBSHARE_PASSWORD)
    }
    
    return jsonify({
        'status': 'online',
        'message': 'YouTube Chapter Generator API is running',
        'webshare_proxy_configured': bool(proxies),
        'proxy_status': proxy_status,
        'cors_headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Accept',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        }
    })

# Custom transcript fetcher that uses proxies
def get_transcript_with_proxy(video_id, language_code='en'):
    """
    Get transcript using multiple methods, with proxy support if configured
    """
    errors = []
    
    try:
        # Method 1: Direct approach with the library's built-in proxy support
        try:
            print(f"Getting transcript for {video_id} using method 1...")
            # This uses the proxies from environment variables
            return YouTubeTranscriptApi.get_transcript(video_id, languages=[language_code])
        except Exception as e:
            errors.append(f"Method 1 failed: {str(e)}")
            traceback.print_exc()
        
        # Method 2: Explicitly pass proxies using the library's proxy parameter
        if proxies:
            try:
                print(f"Getting transcript for {video_id} using method 2...")
                return YouTubeTranscriptApi.get_transcript(
                    video_id, 
                    languages=[language_code],
                    proxies=proxies
                )
            except Exception as e:
                errors.append(f"Method 2 failed: {str(e)}")
                traceback.print_exc()
        
        # Method 3: Use requests session with proxies
        if proxies:
            try:
                print(f"Getting transcript for {video_id} using method 3...")
                # Create a custom requests session with proxies
                session = requests.Session()
                session.proxies.update(proxies)
                
                # Override the YouTubeTranscriptApi's _make_http_request method temporarily
                original_request_method = YouTubeTranscriptApi._make_http_request
                
                def custom_request(url):
                    response = session.get(url)
                    return response.text
                
                # Monkey patch
                YouTubeTranscriptApi._make_http_request = custom_request
                
                try:
                    result = YouTubeTranscriptApi.get_transcript(video_id, languages=[language_code])
                    return result
                finally:
                    # Restore original method
                    YouTubeTranscriptApi._make_http_request = original_request_method
            except Exception as e:
                errors.append(f"Method 3 failed: {str(e)}")
                traceback.print_exc()
        
        # Method 4: Last resort - try without proxy
        try:
            # Clear environment variables temporarily
            temp_http_proxy = os.environ.pop('HTTP_PROXY', None)
            temp_https_proxy = os.environ.pop('HTTPS_PROXY', None)
            
            print(f"Getting transcript for {video_id} using method 4 (no proxy)...")
            result = YouTubeTranscriptApi.get_transcript(video_id, languages=[language_code])
            
            # Restore environment variables
            if temp_http_proxy:
                os.environ['HTTP_PROXY'] = temp_http_proxy
            if temp_https_proxy:
                os.environ['HTTPS_PROXY'] = temp_https_proxy
                
            return result
        except Exception as e:
            errors.append(f"Method 4 failed: {str(e)}")
            traceback.print_exc()
            
        # If we get here, all methods failed
        raise Exception(f"All transcript fetch methods failed. Errors: {errors}")
        
    except Exception as e:
        print(f"Final error getting transcript: {e}")
        # If all methods fail, raise the exception with all errors
        raise Exception(f"Failed to fetch transcript: {str(e)}. Detailed errors: {', '.join(errors)}")

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
        
        # Get transcript using YouTube Transcript API (with proxy if configured)
        transcript_list = get_transcript_with_proxy(video_id)
        
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
        
        # Create response with CORS headers
        result = jsonify({
            "success": True,
            "chapters": chapters,
            "session_id": session_id,
            "video_id": video_id,
            "video_duration": format_time(video_duration_seconds),
            "used_proxy": bool(proxies)
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