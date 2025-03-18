from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import openai
import os
from flask_cors import CORS
import json
import time
import uuid

app = Flask(__name__)
CORS(app)  # Enable cross-origin requests

# Get API key from environment variable
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Generate a session ID for requests to ensure user requests don't get mixed up
def generate_session_id():
    return str(uuid.uuid4())

@app.route('/api', methods=['GET'])
def hello():
    return jsonify({
        'status': 'online',
        'message': 'YouTube Chapter Generator API is running'
    })

@app.route('/api/generate-chapters', methods=['POST'])
def generate_chapters():
    # Generate a unique session ID for this request
    session_id = generate_session_id()
    
    # Get data from request
    data = request.json
    video_id = data.get('video_id')
    
    if not video_id:
        return jsonify({
            'success': False,
            'error': 'No video ID provided',
            'session_id': session_id
        })
    
    try:
        # Get transcript using YouTube Transcript API
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Calculate video duration in minutes
        if transcript_list:
            last_entry = transcript_list[-1]
            video_duration_seconds = last_entry['start'] + last_entry['duration']
            video_duration_minutes = video_duration_seconds / 60
        else:
            video_duration_minutes = 0
        
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
        
        # Get chapter suggestions from OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Using the most capable model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the transcript with timestamps for YouTube video ID {video_id}:\n\n{formatted_transcript}"}
            ]
        )
        
        chapters = response.choices[0].message.content
        
        return jsonify({
            "success": True,
            "chapters": chapters,
            "session_id": session_id,
            "video_id": video_id,
            "video_duration": format_time(video_duration_seconds)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "session_id": session_id,
            "video_id": video_id
        })

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