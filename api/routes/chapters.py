"""
Chapter generation endpoints
"""
import time
from flask import Flask, request, jsonify, make_response

from api.utils.responses import create_error_response
from api.utils.cache import get_from_cache, add_to_cache
from api.services.youtube import fetch_transcript
from api.services.openai_service import create_chapter_prompt, generate_chapters_with_openai
from api.utils.transcript import format_transcript_for_model


def register_chapter_routes(app: Flask) -> None:
    """
    Register chapter generation routes with the Flask app
    
    Args:
        app: Flask application instance
    """
    @app.route('/api/generate-chapters', methods=['POST', 'OPTIONS'])
    def generate_chapters():
        """Generate chapters for a YouTube video"""
        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            result = make_response()
            result.headers.add('Access-Control-Allow-Origin', '*')
            result.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept')
            result.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
            
            return result
        
        # Extract video ID from request
        data = request.get_json()
        video_id = data.get('videoId')
        if not video_id:
            return create_error_response('Missing videoId parameter', 400)
        
        # Check cache first
        cached_chapters = get_from_cache(video_id)
        if cached_chapters:
            print(f"Returning cached chapters for {video_id}")
            response_data = {
                'success': True,
                'videoId': video_id,
                'chapters': cached_chapters,
                'fromCache': True
            }
            
            response = jsonify(response_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept')
            response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
            
            return response
        
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
        
        # Format transcript for OpenAI with intelligent handling of long transcripts
        formatted_transcript, transcript_length = format_transcript_for_model(transcript_data)
        print(f"Prepared transcript format with {transcript_length} lines")
        
        # Create prompt
        system_prompt = create_chapter_prompt(video_duration_minutes)
        
        # Generate chapters with OpenAI
        chapters = generate_chapters_with_openai(system_prompt, video_id, formatted_transcript)
        if not chapters:
            return create_error_response('Failed to generate chapters with OpenAI', 500)
        
        # Count chapters
        chapter_count = len(chapters.strip().split("\n"))
        print(f"Generated {chapter_count} chapters for {video_id}")
        
        # Add to cache
        add_to_cache(video_id, chapters)
        
        # Prepare response
        response_data = {
            'success': True,
            'videoId': video_id,
            'chapters': chapters,
            'fromCache': False
        }
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        
        return response
