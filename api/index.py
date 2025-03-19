import os
import sys
import traceback
import json
import requests
from flask import Flask, request, jsonify, make_response
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, RequestBlocked, AgeRestricted, VideoUnplayable
from youtube_transcript_api.proxies import WebshareProxyConfig
from openai import OpenAI
from flask_cors import CORS
import time

# Simple in-memory cache
CHAPTERS_CACHE = {}

# Print debug info
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Files in current directory: {os.listdir()}")

# Create Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
print("Flask app created and CORS configured")

# Centralized configuration management
class Config:
    # Environment variables
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    WEBSHARE_USERNAME = os.environ.get("WEBSHARE_USERNAME", "")
    WEBSHARE_PASSWORD = os.environ.get("WEBSHARE_PASSWORD", "")
    
    # API configurations
    OPENAI_MODELS = ["gpt-3.5-turbo-16k", "gpt-3.5-turbo"]
    TRANSCRIPT_LANGUAGES = ["en", "en-US", "en-GB"]
    
    # Proxy configuration
    @classmethod
    def get_proxy_url(cls):
        if cls.WEBSHARE_USERNAME and cls.WEBSHARE_PASSWORD:
            return f"http://{cls.WEBSHARE_USERNAME}:{cls.WEBSHARE_PASSWORD}@p.webshare.io:80"
        return None
    
    @classmethod
    def get_proxy_dict(cls):
        proxy_url = cls.get_proxy_url()
        if proxy_url:
            return {
                'http': proxy_url,
                'https': proxy_url
            }
        return None
    
    @classmethod
    def get_webshare_proxy_config(cls):
        if cls.WEBSHARE_USERNAME and cls.WEBSHARE_PASSWORD:
            return WebshareProxyConfig(
                proxy_username=cls.WEBSHARE_USERNAME,
                proxy_password=cls.WEBSHARE_PASSWORD
            )
        return None

# Print config information
print(f"Environment variables loaded: OPENAI_API_KEY={'✓' if Config.OPENAI_API_KEY else '✗'}, "
      f"WEBSHARE_USERNAME={'✓' if Config.WEBSHARE_USERNAME else '✗'}, "
      f"WEBSHARE_PASSWORD={'✓' if Config.WEBSHARE_PASSWORD else '✗'}")

# Create OpenAI client if API key is available
openai_client = None
if Config.OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        print("OpenAI client configured")
    except Exception as e:
        print(f"ERROR configuring OpenAI client: {e}")
        traceback.print_exc()
else:
    print("Warning: OpenAI API key not found in environment variables")

# Standardized error response helper
def create_error_response(message, status_code=500, extra_data=None):
    response_data = {
        'success': False,
        'error': message
    }
    if extra_data:
        response_data.update(extra_data)
    
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Accept',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    response = jsonify(response_data)
    for key, value in response_headers.items():
        response.headers.add(key, value)
    
    return response, status_code

# Simple health check
@app.route('/', methods=['GET'])
def root():
    return "API is running. Try /api for more details.", 200

@app.route('/api', methods=['GET'])
def hello():
    """API status endpoint"""
    try:
        # Test direct connection to YouTube
        direct_connection_success = False
        try:
            # Create a fresh session for this test
            with requests.Session() as test_session:
                test_session.proxies.clear()
                response = test_session.get("https://www.youtube.com", timeout=5)
                direct_connection_success = response.status_code == 200
        except Exception as e:
            print(f"Direct connection test failed: {e}")
            direct_connection_success = False
        
        # Basic environment info for diagnostics
        env_info = {
            'python_version': sys.version,
            'openai_key_configured': bool(Config.OPENAI_API_KEY),
            'webshare_username_configured': bool(Config.WEBSHARE_USERNAME),
            'webshare_password_configured': bool(Config.WEBSHARE_PASSWORD)
        }
        
        return jsonify({
            'status': 'online',
            'message': 'YouTube Chapter Generator API is running',
            'proxy_configured': bool(Config.get_proxy_dict()),
            'direct_connection_available': direct_connection_success,
            'env_info': env_info
        })
    except Exception as e:
        print(f"Error in /api route: {e}")
        traceback.print_exc()
        return create_error_response(f"API error: {str(e)}", 500)

@app.route('/api/generate-chapters', methods=['POST', 'OPTIONS'])
def generate_chapters():
    """Generate chapters for a YouTube video"""
    
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        # Validate OpenAI API key
        if not openai_client:
            return create_error_response('OpenAI API key is not configured on the server.', 400)
        
        # Get data from request
        data = request.json
        if not data or 'video_id' not in data:
            return create_error_response('No video ID provided', 400)
        
        video_id = data['video_id']
        print(f"Processing request for video_id: {video_id}")
        
        # Check if we have cached results for this video
        force_refresh = data.get('force_refresh', False)
        if not force_refresh and video_id in CHAPTERS_CACHE:
            print(f"Returning cached chapters for {video_id}")
            cached_result = CHAPTERS_CACHE[video_id]
            
            # Create response from cache
            result = jsonify({
                "success": True,
                "chapters": cached_result["chapters"],
                "video_id": video_id,
                "video_duration_minutes": cached_result["video_duration_minutes"],
                "used_proxy": cached_result["used_proxy"],
                "from_cache": True
            })
            
            # Add CORS headers
            result.headers.add('Access-Control-Allow-Origin', '*')
            result.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept')
            result.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
            
            return result
        
        # Get transcript - using a timeout to avoid Vercel function timeouts
        start_time = time.time()
        timeout_limit = 20  # seconds - leave room for the rest of processing
        transcript_data = fetch_transcript(video_id, timeout_limit)
        
        if not transcript_data:
            return create_error_response('Failed to fetch transcript after multiple attempts', 500)
        
        elapsed_time = time.time() - start_time
        print(f"Successfully retrieved transcript for {video_id} with {len(transcript_data)} entries in {elapsed_time:.2f} seconds")
        
        # Calculate video duration
        last_entry = transcript_data[-1]
        video_duration_seconds = last_entry['start'] + last_entry['duration']
        video_duration_minutes = video_duration_seconds / 60
        
        # Format transcript for OpenAI - using the simplified format
        formatted_transcript, transcript_length = prepare_efficient_transcript(transcript_data)
        print(f"Prepared efficient transcript format with {transcript_length} lines")
        
        # Create prompt
        system_prompt = create_efficient_chapter_prompt(video_duration_minutes)
        
        # Generate chapters with OpenAI - quick version
        chapters = generate_chapters_efficiently(system_prompt, video_id, formatted_transcript)
        if not chapters:
            return create_error_response('Failed to generate chapters with OpenAI', 500)
        
        # Count chapters
        chapter_count = len(chapters.strip().split("\n"))
        print(f"Generated {chapter_count} chapters for {video_id}")
        
        # Cache the results
        CHAPTERS_CACHE[video_id] = {
            "chapters": chapters,
            "video_duration_minutes": f"{video_duration_minutes:.2f}",
            "used_proxy": bool(Config.get_webshare_proxy_config())
        }
        
        # Create successful response
        result = jsonify({
            "success": True,
            "chapters": chapters,
            "video_id": video_id,
            "video_duration_minutes": f"{video_duration_minutes:.2f}",
            "used_proxy": bool(Config.get_webshare_proxy_config()),
            "from_cache": False
        })
        
        # Add CORS headers
        result.headers.add('Access-Control-Allow-Origin', '*')
        result.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept')
        result.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        
        return result
        
    except Exception as e:
        print(f"Error in generate_chapters: {e}")
        traceback.print_exc()
        return create_error_response(str(e), 500)

def fetch_transcript(video_id, timeout_limit=30):
    """
    Fetch transcript using the YouTube Transcript API with proper error handling
    and fallbacks.
    
    Args:
        video_id: YouTube video ID
        timeout_limit: Maximum time in seconds to spend fetching the transcript
    """
    error_messages = []
    start_time = time.time()
    
    # Initialize YouTubeTranscriptApi with proxy configuration if available
    if Config.WEBSHARE_USERNAME and Config.WEBSHARE_PASSWORD:
        proxy_config = WebshareProxyConfig(
            proxy_username=Config.WEBSHARE_USERNAME,
            proxy_password=Config.WEBSHARE_PASSWORD
        )
        youtube_transcript_api = YouTubeTranscriptApi(proxy_config=proxy_config)
        print("Initialized YouTubeTranscriptApi with WebshareProxyConfig")
    else:
        youtube_transcript_api = YouTubeTranscriptApi()
        print("Initialized YouTubeTranscriptApi without proxy")
    
    def time_left():
        """Check if we still have time to continue operations"""
        elapsed = time.time() - start_time
        return timeout_limit - elapsed
    
    # First try: List transcripts
    try:
        if time_left() < 2:  # If less than 2 seconds left, skip this method
            raise TimeoutError("Time limit approaching, skipping transcript listing")
            
        print("Attempting to list available transcripts...")
        transcript_list = youtube_transcript_api.list(video_id)
        
        print("Available transcripts:")
        transcript_count = 0
        available_transcripts = []
        
        # Collect available transcripts
        for transcript in transcript_list:
            transcript_count += 1
            available_transcripts.append(transcript)
            print(f"  - {transcript.language_code} ({transcript.language}), Auto-generated: {transcript.is_generated}")
        
        print(f"Found {transcript_count} available transcripts")
        
        # Try to find transcript in preferred languages
        for lang in Config.TRANSCRIPT_LANGUAGES:
            if time_left() < 2:  # If less than 2 seconds left, skip to faster methods
                raise TimeoutError("Time limit approaching, skipping language search")
                
            try:
                print(f"Trying to find transcript in language: {lang}")
                transcript = transcript_list.find_transcript([lang])
                transcript_data = transcript.fetch()
                if transcript_data and len(transcript_data) > 0:
                    print(f"Successfully found transcript in {lang} with {len(transcript_data)} entries")
                    # Convert FetchedTranscriptSnippet objects to dictionaries if needed
                    if hasattr(transcript_data, 'to_raw_data'):
                        return transcript_data.to_raw_data()
                    # Try to process as FetchedTranscriptSnippet objects
                    if hasattr(transcript_data[0], 'to_dict'):
                        return [snippet.to_dict() for snippet in transcript_data]
                    return transcript_data
            except Exception as e:
                print(f"Could not find transcript in {lang}: {e}")
                continue
        
        # If no preferred language is found, try to get any transcript and translate it
        if time_left() < 5:  # Skip translation if we're running out of time
            raise TimeoutError("Time limit approaching, skipping translation")
            
        print("No preferred language found, trying to get any transcript and translate it")
        try:
            # Get the first available transcript
            if transcript_count > 0:
                first_transcript = available_transcripts[0]
                print(f"Found transcript in {first_transcript.language_code} ({first_transcript.language})")
                
                # Check if the transcript is not in English and translation is needed
                if first_transcript.language_code not in Config.TRANSCRIPT_LANGUAGES:
                    try:
                        print(f"Translating transcript from {first_transcript.language_code} to en...")
                        english_transcript = first_transcript.translate('en')
                        transcript_data = english_transcript.fetch()
                        print(f"Successfully translated transcript to English with {len(transcript_data)} entries")
                        # Convert FetchedTranscriptSnippet objects to dictionaries if needed
                        if hasattr(transcript_data, 'to_raw_data'):
                            return transcript_data.to_raw_data()
                        # Try to process as FetchedTranscriptSnippet objects
                        if hasattr(transcript_data[0], 'to_dict'):
                            return [snippet.to_dict() for snippet in transcript_data]
                        return transcript_data
                    except Exception as e:
                        print(f"Translation failed: {e}")
                        # Continue with the original language if translation fails
                
                # Use the original language if it's in our preferred list or translation failed
                transcript_data = first_transcript.fetch()
                if transcript_data and len(transcript_data) > 0:
                    print(f"Using original language transcript with {len(transcript_data)} entries")
                    # Convert FetchedTranscriptSnippet objects to dictionaries if needed
                    if hasattr(transcript_data, 'to_raw_data'):
                        return transcript_data.to_raw_data()
                    # Try to process as FetchedTranscriptSnippet objects
                    if hasattr(transcript_data[0], 'to_dict'):
                        return [snippet.to_dict() for snippet in transcript_data]
                    return transcript_data
            else:
                print("No transcripts found for this video")
        except Exception as e:
            error_message = str(e)
            error_messages.append(f"Processing first available transcript failed: {error_message}")
            print(f"Processing first available transcript failed: {error_message}")
    except TimeoutError as te:
        print(f"Timeout warning: {str(te)}")
    except (RequestBlocked, AgeRestricted, VideoUnplayable) as e:
        error_message = str(e)
        error_messages.append(f"Listing transcripts failed (blocked/restricted): {error_message}")
        print(f"Listing transcripts failed (blocked/restricted): {error_message}")
    except Exception as e:
        error_message = str(e)
        error_messages.append(f"Listing transcripts failed (unexpected error): {error_message}")
        print(f"Listing transcripts failed (unexpected error): {error_message}")
    
    # Second try: Direct transcript fetching
    try:
        if time_left() < 2:  # If less than 2 seconds left, skip this method
            raise TimeoutError("Time limit approaching, skipping direct fetch")
            
        print("Attempting direct transcript fetching...")
        transcript_data = youtube_transcript_api.fetch(
            video_id, 
            languages=Config.TRANSCRIPT_LANGUAGES
        )
        if transcript_data and len(transcript_data) > 0:
            print(f"Successfully fetched transcript directly: {len(transcript_data)} entries")
            # Convert to raw data if needed
            if hasattr(transcript_data, 'to_raw_data'):
                return transcript_data.to_raw_data()
            return transcript_data
    except TimeoutError as te:
        print(f"Timeout warning: {str(te)}")
    except Exception as e:
        error_message = str(e)
        error_messages.append(f"Direct transcript fetch failed: {error_message}")
        print(f"Direct transcript fetch failed: {error_message}")
    
    # Third try: Try without proxy
    try:
        if time_left() < 2:  # If less than 2 seconds left, skip this method
            raise TimeoutError("Time limit approaching, skipping no-proxy fetch")
            
        print("Attempting direct transcript fetching without proxy...")
        no_proxy_api = YouTubeTranscriptApi()
        transcript_data = no_proxy_api.fetch(
            video_id, 
            languages=Config.TRANSCRIPT_LANGUAGES
        )
        if transcript_data and len(transcript_data) > 0:
            print(f"Successfully fetched transcript directly without proxy: {len(transcript_data)} entries")
            # Convert to raw data if needed
            if hasattr(transcript_data, 'to_raw_data'):
                return transcript_data.to_raw_data()
            return transcript_data
    except TimeoutError as te:
        print(f"Timeout warning: {str(te)}")
    except Exception as e:
        error_message = str(e)
        error_messages.append(f"Direct transcript fetch without proxy failed: {error_message}")
        print(f"Direct transcript fetch without proxy failed: {error_message}")
    
    # Final fallback: Use custom requests implementation
    try:
        if time_left() < 5:  # If less than 5 seconds left, skip this method
            raise TimeoutError("Time limit approaching, skipping custom requests method")
            
        print("Attempting fallback method with direct requests...")
        proxy_dict = Config.get_proxy_dict()
        transcript_list = fetch_transcript_with_requests(video_id, proxy_dict, timeout=min(5, time_left()))
        if transcript_list and len(transcript_list) > 0:
            print(f"Successfully fetched transcript with requests: {len(transcript_list)} entries")
            return transcript_list
    except TimeoutError as te:
        print(f"Timeout warning: {str(te)}")
    except Exception as e:
        error_message = str(e)
        error_messages.append(f"Direct requests method failed: {error_message}")
        print(f"Direct requests method failed: {error_message}")
    
    # All methods failed
    combined_errors = " | ".join(error_messages)
    print(f"All transcript fetch methods failed: {combined_errors}")
    return None

def prepare_efficient_transcript(transcript_list):
    """Format transcript in a minimalist way optimized for OpenAI processing"""
    # Use a more compact format with just timestamps and text
    formatted_entries = []
    
    # Sample the transcript: beginning, middle parts, and end
    # This uses a strategic sampling to capture key moments throughout the video
    total_entries = len(transcript_list)
    
    if total_entries <= 300:
        # For shorter transcripts, use everything
        entries_to_use = transcript_list
    else:
        # For longer transcripts, take samples from throughout the video
        # Take more from the beginning and end, which tend to have more context
        beginning = transcript_list[:100]
        
        # Take samples from the middle at regular intervals
        middle_length = total_entries - 200  # 100 from beginning, 100 from end
        num_samples = 100  # Take 100 samples from the middle
        
        # Calculate step size to evenly distribute samples
        step = max(1, middle_length // num_samples)
        
        # Take samples at regular intervals from the middle
        middle_samples = []
        for i in range(100, total_entries - 100, step):
            if len(middle_samples) < num_samples:
                middle_samples.append(transcript_list[i])
                
        end = transcript_list[-100:]
        
        # Combine the parts
        entries_to_use = beginning + middle_samples + end
    
    # Format the selected entries
    for item in entries_to_use:
        # Convert seconds to MM:SS format
        minutes, seconds = divmod(int(item['start']), 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            timestamp = f"{minutes:02d}:{seconds:02d}"
            
        formatted_entries.append(f"{timestamp}: {item['text']}")
    
    return "\n".join(formatted_entries), len(formatted_entries)

def create_efficient_chapter_prompt(video_duration_minutes):
    """Create a streamlined prompt for OpenAI based on video duration"""
    system_prompt = (
        "You are a YouTube chapter creator. Extract the main topics from this transcript and create time-based chapters. "
        "Be efficient and focus on significant topic changes. The first chapter must start at 00:00."
        "\n\n"
        "Format your response as a list of timestamps and titles only, like:\n"
        "00:00 Introduction\n"
        "02:30 First Topic\n"
        "05:45 Second Topic"
        "\n\n"
    )
    
    # Adjust chapters based on video length
    if video_duration_minutes <= 10:
        system_prompt += "Provide 3-5 chapters."
    elif video_duration_minutes <= 20:
        system_prompt += "Provide 5-7 chapters."
    elif video_duration_minutes <= 40:
        system_prompt += "Provide 7-10 chapters."
    else:
        system_prompt += "Provide 10-15 chapters."
    
    return system_prompt

def generate_chapters_efficiently(system_prompt, video_id, formatted_transcript):
    """Generate chapters using OpenAI with optimization for speed and reliability"""
    if not openai_client:
        print("OpenAI client not configured")
        return None
    
    for model in Config.OPENAI_MODELS:
        try:
            print(f"Attempting to generate chapters with {model}...")
            
            # Prepare a concise message for the API
            user_content = f"Generate chapters for this video transcript:\n\n{formatted_transcript}"
            
            # Send request to OpenAI
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.7,  # Slightly creative but mostly focused
                max_tokens=300    # Limit token usage to speed up response
            )
            
            chapters = response.choices[0].message.content
            return chapters
        except Exception as e:
            print(f"Error generating chapters with {model}: {e}")
            continue
    
    # All models failed
    print("All OpenAI models failed to generate chapters")
    return None

# Backup function to fetch transcript using requests directly
def fetch_transcript_with_requests(video_id, proxy_dict=None, timeout=10):
    """Fetch YouTube transcript using requests library with proxy support"""
    print(f"Attempting to fetch transcript for {video_id} using requests with proxies: {bool(proxy_dict)}")
    
    # Create a session for this request
    session = requests.Session()
    if proxy_dict:
        session.proxies.update(proxy_dict)
    
    # First get the video page to extract available captions
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        print(f"Fetching video page with proxies: {bool(proxy_dict)}")
        response = session.get(video_url, timeout=timeout)
        response.raise_for_status()
        
        # Find the captions URL in the page
        html = response.text
        
        # Extract ytInitialPlayerResponse JSON
        start_marker = 'ytInitialPlayerResponse = '
        end_marker = '};'
        
        start_idx = html.find(start_marker)
        if start_idx == -1:
            raise Exception("Could not find player response in page")
        
        start_idx += len(start_marker)
        end_idx = html.find(end_marker, start_idx) + 1
        
        player_response_json = html[start_idx:end_idx]
        player_response = json.loads(player_response_json)
        
        # Find caption tracks
        captions_data = player_response.get('captions', {}).get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
        
        if not captions_data:
            raise Exception("No captions found for this video")
        
        # Try to find English captions
        caption_url = None
        for track in captions_data:
            if track.get('languageCode') in Config.TRANSCRIPT_LANGUAGES:
                caption_url = track.get('baseUrl')
                break
        
        # If no English captions, use the first available
        if not caption_url and captions_data:
            caption_url = captions_data[0].get('baseUrl')
        
        if not caption_url:
            raise Exception("No valid caption URL found")
        
        # Add format parameter for JSON
        caption_url += "&fmt=json3"
        
        # Fetch the captions
        print(f"Fetching captions from {caption_url}")
        captions_response = session.get(caption_url, timeout=timeout)
        captions_response.raise_for_status()
        
        captions_data = captions_response.json()
        
        # Process the transcript
        transcript = []
        for event in captions_data.get('events', []):
            if 'segs' not in event or 'tStartMs' not in event:
                continue
                
            text = ''.join(seg.get('utf8', '') for seg in event.get('segs', []))
            if not text.strip():
                continue
                
            transcript.append({
                'text': text.strip(),
                'start': event.get('tStartMs') / 1000,
                'duration': event.get('dDurationMs', 0) / 1000
            })
        
        print(f"Successfully fetched transcript with {len(transcript)} entries using requests")
        return transcript
        
    except Exception as e:
        print(f"Error fetching transcript with requests: {e}")
        traceback.print_exc()
        raise Exception(f"Failed to fetch transcript with requests: {str(e)}")

# For local development
if __name__ == '__main__':
    app.run(debug=True)
