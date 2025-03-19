from flask import Flask, request, jsonify, make_response
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from flask_cors import CORS
import os
import sys
import traceback
import json
import requests
from xml.etree import ElementTree

# Debug imports
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Files in current directory: {os.listdir()}")

# Import dependencies with error handling
try:
    from flask import Flask, request, jsonify, make_response
    print("Flask imported successfully")
except ImportError as e:
    print(f"ERROR importing Flask: {e}")
    traceback.print_exc()

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    print("YouTubeTranscriptApi imported successfully")
except ImportError as e:
    print(f"ERROR importing YouTubeTranscriptApi: {e}")
    traceback.print_exc()

try:
    from openai import OpenAI
    print("OpenAI imported successfully")
except ImportError as e:
    print(f"ERROR importing OpenAI: {e}")
    traceback.print_exc()
    
try:
    from flask_cors import CORS
    print("CORS imported successfully")
except ImportError as e:
    print(f"ERROR importing CORS: {e}")
    traceback.print_exc()

# Create Flask app
try:
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    print("Flask app created and CORS configured")
except Exception as e:
    print(f"ERROR creating Flask app: {e}")
    traceback.print_exc()

# Get environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
WEBSHARE_USERNAME = os.environ.get("WEBSHARE_USERNAME", "")
WEBSHARE_PASSWORD = os.environ.get("WEBSHARE_PASSWORD", "")

print(f"Environment variables loaded: OPENAI_API_KEY={'✓' if OPENAI_API_KEY else '✗'}, WEBSHARE_USERNAME={'✓' if WEBSHARE_USERNAME else '✗'}, WEBSHARE_PASSWORD={'✓' if WEBSHARE_PASSWORD else '✗'}")

# Configure proxies if credentials available
proxies = None
if WEBSHARE_USERNAME and WEBSHARE_PASSWORD:
    try:
        proxy_url = f"http://{WEBSHARE_USERNAME}:{WEBSHARE_PASSWORD}@p.webshare.io:80"
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # Set proxies in environment variables for libraries that use them
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
        
        # Set up proxy support for urllib and requests libraries
        import urllib.request
        proxy_handler = urllib.request.ProxyHandler(proxies)
        opener = urllib.request.build_opener(proxy_handler)
        urllib.request.install_opener(opener)
        
        # Configure requests library if it's being used
        try:
            import requests
            from requests.auth import HTTPProxyAuth
            
            # Set default proxies for requests
            requests.Session().proxies.update(proxies)
            print("Configured proxies for requests library")
        except ImportError:
            print("Requests library not installed, skipping requests proxy setup")
            
        print("Webshare proxy configured via environment variables and urllib")
    except Exception as e:
        print(f"ERROR configuring proxies: {e}")
        traceback.print_exc()
else:
    print("No Webshare proxy configured")

# Create OpenAI client if API key is available
openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("OpenAI client configured")
    except Exception as e:
        print(f"ERROR configuring OpenAI client: {e}")
        traceback.print_exc()
else:
    print("Warning: OpenAI API key not found in environment variables")

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
            # Temporarily clear proxy settings
            old_http_proxy = os.environ.pop('HTTP_PROXY', None)
            old_https_proxy = os.environ.pop('HTTPS_PROXY', None)
            
            # Try a quick direct connection
            with requests.Session() as test_session:
                test_session.proxies.clear()
                response = test_session.get("https://www.youtube.com", timeout=5)
                direct_connection_success = response.status_code == 200
                
            # Restore environment
            if old_http_proxy:
                os.environ['HTTP_PROXY'] = old_http_proxy
            if old_https_proxy:
                os.environ['HTTPS_PROXY'] = old_https_proxy
        except:
            direct_connection_success = False
        
        # Basic environment info for diagnostics
        env_info = {
            'python_version': sys.version,
            'openai_key_configured': bool(OPENAI_API_KEY),
            'webshare_username_configured': bool(WEBSHARE_USERNAME),
            'webshare_password_configured': bool(WEBSHARE_PASSWORD)
        }
        
        return jsonify({
            'status': 'online',
            'message': 'YouTube Chapter Generator API is running',
            'proxy_configured': bool(proxies),
            'direct_connection_available': direct_connection_success,
            'env_info': env_info
        })
    except Exception as e:
        print(f"Error in /api route: {e}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': 'API error',
            'error': str(e)
        }), 200  # Return 200 even on error for diagnostic purposes

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
    
    # Response headers
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Accept',
        'Access-Control-Allow-Methods': 'POST,OPTIONS'
    }
    
    try:
        # Validate OpenAI API key
        if not openai_client:
            return jsonify({
                'success': False,
                'error': 'OpenAI API key is not configured on the server.'
            }), 400, response_headers
        
        # Get data from request
        data = request.json
        if not data or 'video_id' not in data:
            return jsonify({
                'success': False,
                'error': 'No video ID provided'
            }), 400, response_headers
        
        video_id = data['video_id']
        print(f"Processing request for video_id: {video_id}")
        
        # Get transcript
        try:
            transcript_list = None
            error_messages = []
            
            # Setup proxies according to youtube-transcript-api documentation
            if WEBSHARE_USERNAME and WEBSHARE_PASSWORD:
                # Format proxies for youtube-transcript-api
                proxies_dict = {
                    'http': f'http://{WEBSHARE_USERNAME}:{WEBSHARE_PASSWORD}@p.webshare.io:80',
                    'https': f'http://{WEBSHARE_USERNAME}:{WEBSHARE_PASSWORD}@p.webshare.io:80'
                }
                print(f"Configured proxies for youtube-transcript-api: {proxies_dict}")
            else:
                proxies_dict = None
                print("No proxy credentials found, will attempt without proxy")
            
            # Try with Webshare proxies first
            try:
                print("Attempting to fetch transcript with proxies directly in YouTubeTranscriptApi...")
                # Pass proxies directly to the API call as documented
                transcript_list = YouTubeTranscriptApi.get_transcript(
                    video_id, 
                    languages=['en'],
                    proxies=proxies_dict
                )
                print(f"Successfully fetched transcript with {len(transcript_list)} entries")
            except Exception as e1:
                error_message = str(e1)
                error_messages.append(f"Proxy method failed: {error_message}")
                print(f"Proxy method failed: {error_message}")
                
                # Try without proxy as fallback
                try:
                    print("Attempting to fetch transcript without proxy...")
                    transcript_list = YouTubeTranscriptApi.get_transcript(
                        video_id, 
                        languages=['en'],
                        proxies=None
                    )
                    print(f"Successfully fetched transcript without proxy: {len(transcript_list)} entries")
                except Exception as e2:
                    error_messages.append(f"Direct method failed: {str(e2)}")
                    print(f"Direct method failed: {str(e2)}")
            
            # If all methods failed
            if not transcript_list:
                combined_errors = " | ".join(error_messages)
                return jsonify({
                    'success': False,
                    'error': f'Failed to fetch transcript: {combined_errors}'
                }), 500, response_headers
                
            print(f"Successfully retrieved transcript for {video_id} with {len(transcript_list)} entries")
        except Exception as transcript_error:
            return jsonify({
                'success': False,
                'error': f'Error fetching transcript: {str(transcript_error)}'
            }), 500, response_headers
        
        # Calculate video duration
        last_entry = transcript_list[-1]
        video_duration_seconds = last_entry['start'] + last_entry['duration']
        video_duration_minutes = video_duration_seconds / 60
        
        # Format transcript for OpenAI
        formatted_transcript = ""
        for item in transcript_list:
            minutes, seconds = divmod(int(item['start']), 60)
            hours, minutes = divmod(minutes, 60)
            
            if hours > 0:
                timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                timestamp = f"{minutes:02d}:{seconds:02d}"
                
            formatted_transcript += f"{timestamp} - {item['text']}\n"
        
        # Create prompt
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
        
        # Adjust chapters based on video length
        if video_duration_minutes <= 10:
            system_prompt += "Provide 3-5 chapters."
        elif video_duration_minutes <= 20:
            system_prompt += "Provide 5-7 chapters."
        elif video_duration_minutes <= 40:
            system_prompt += "Provide 7-10 chapters."
        else:
            system_prompt += "Provide 10-15 chapters."
        
        # Generate chapters with OpenAI
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Here is the transcript for YouTube video ID {video_id}:\n\n{formatted_transcript}"}
                ]
            )
            
            chapters = response.choices[0].message.content
            chapter_count = len(chapters.split("\n"))
            print(f"Generated {chapter_count} chapters for {video_id}")
        except Exception as openai_error:
            print(f"OpenAI API error: {openai_error}")
            traceback.print_exc()
            return jsonify({
                "success": False,
                "error": f"Error generating chapters: {str(openai_error)}"
            }), 500, response_headers
        
        # Create successful response
        result = jsonify({
            "success": True,
            "chapters": chapters,
            "video_id": video_id,
            "video_duration_minutes": f"{video_duration_minutes:.2f}",
            "used_proxy": bool(proxies)
        })
        
        # Add CORS headers
        for key, value in response_headers.items():
            result.headers.add(key, value)
        
        return result
        
    except Exception as e:
        print(f"Error in generate_chapters: {e}")
        traceback.print_exc()
        
        error_response = jsonify({
            "success": False,
            "error": str(e)
        })
        
        # Add CORS headers
        for key, value in response_headers.items():
            error_response.headers.add(key, value)
        
        return error_response, 500

# For local development
if __name__ == '__main__':
    app.run(debug=True) 

# Backup function to fetch transcript using requests directly
def fetch_transcript_with_requests(video_id, proxies=None, session=None):
    """Fetch YouTube transcript using requests library with proxy support"""
    print(f"Attempting to fetch transcript for {video_id} using requests with proxies: {bool(proxies)}")
    
    # Use provided session or create a new one
    req_session = session if session else requests
    
    # First get the video page to extract available captions
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        print(f"Fetching video page with proxies: {bool(proxies)}")
        response = req_session.get(video_url, proxies=proxies)
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
            if track.get('languageCode') == 'en':
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
        captions_response = req_session.get(caption_url, proxies=proxies)
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
        raise Exception(f"Failed to fetch transcript with requests: {str(e)}") # Enforcing a manual deployment trigger
