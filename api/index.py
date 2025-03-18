import os
import sys
import traceback

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
        if not os.environ.get('HTTP_PROXY'):
            os.environ['HTTP_PROXY'] = proxy_url
        if not os.environ.get('HTTPS_PROXY'):
            os.environ['HTTPS_PROXY'] = proxy_url
            
        print("Webshare proxy configured via environment variables")
    except Exception as e:
        print(f"ERROR configuring proxies: {e}")
        traceback.print_exc()
else:
    print("No Webshare proxy configured")

# Create OpenAI client if API key is available
openai_client = None
if OPENAI_API_KEY:
    try:
        # Initialize the OpenAI client without passing proxies directly
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
            # Only use the language parameter, proxies should be picked up from env vars
            kwargs = {'languages': ['en']}
            
            # We don't pass proxies directly anymore
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, **kwargs)
            
            if not transcript_list:
                return jsonify({
                    'success': False,
                    'error': 'No transcript found for this video'
                }), 404, response_headers
                
            print(f"Transcript retrieved for {video_id} with {len(transcript_list)} entries")
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

# This should help Vercel understand we're returning a Flask application
def handler(event, context):
    return app

# For local development
if __name__ == '__main__':
    app.run(debug=True) 