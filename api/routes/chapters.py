import time
import logging
from flask import request, g

# Import necessary services, utils, and decorators
from ..utils.responses import success_response, error_response
from ..utils.cache import get_from_cache, add_to_cache
from ..services.youtube import fetch_transcript
from ..services.openai_service import create_chapter_prompt, generate_chapters_with_openai
from ..utils.transcript import format_transcript_for_model
from ..utils.decorators import token_required
from ..services import credits_service
from ..utils.versioning import VersionedBlueprint

# Create a versioned blueprint
chapters_bp = VersionedBlueprint('chapters', __name__, url_prefix='/chapters')

# Define the route under the blueprint
@chapters_bp.route('/generate', methods=['POST'])
@token_required # Apply the authentication decorator
async def generate_chapters():
    """
    Generate chapters for a YouTube video, requiring authentication and credits.
    """
    # Get user_id from the decorator via Flask's g context
    user_id = getattr(g, 'current_user_id', None)
    if not user_id:
        logging.error("User ID not found in g context within generate_chapters route.")
        return error_response("Authentication context error.", 500)

    # Extract video ID from request
    data = request.get_json()
    if not data:
        return error_response('Request must be JSON', 400)

    video_id = data.get('video_id')
    if not video_id:
        return error_response('Missing video_id parameter', 400)

    # --- Credit Check ---
    try:
        has_credits = await credits_service.has_sufficient_credits(user_id)
        if not has_credits:
            logging.warning(f"User {user_id} attempted generation with insufficient credits for video {video_id}.")
            # 402 Payment Required is appropriate here
            return error_response('Insufficient credits to generate chapters.', 402)
    except Exception as e:
        logging.error(f"Error checking credits for user {user_id}: {e}")
        return error_response("Failed to verify credit balance.", 500)
    # --- End Credit Check ---

    # Check cache first (still useful to avoid re-generation even if credits are checked)
    cached_chapters = get_from_cache(video_id)
    if cached_chapters:
        logging.info(f"Returning cached chapters for {video_id} (User: {user_id})")
        # Note: We don't deduct credits if serving from cache
        return success_response({
            'videoId': video_id,
            'chapters': cached_chapters,
            'fromCache': True
        })

    # Get transcript - using a timeout to avoid Vercel function timeouts
    start_time_transcript = time.time()
    # Increased timeout limit for fetching transcript
    timeout_limit = 45 # Increased from 20
    logging.info(f"Attempting to fetch transcript for {video_id} with timeout {timeout_limit}s (User: {user_id})")
    transcript_data = fetch_transcript(video_id, timeout_limit)

    if not transcript_data:
        logging.error(f"Failed to fetch transcript for {video_id} after {time.time() - start_time_transcript:.2f} seconds (User: {user_id})")
        return error_response('Failed to fetch transcript after multiple attempts', 500)

    elapsed_time_transcript = time.time() - start_time_transcript
    logging.info(f"Successfully retrieved transcript for {video_id} with {len(transcript_data)} entries in {elapsed_time_transcript:.2f} seconds (User: {user_id})")

    # Calculate video duration
    if not transcript_data: # Should not happen due to check above, but defensive coding
         return error_response('Transcript data is empty after successful fetch.', 500)
    last_entry = transcript_data[-1]
    video_duration_seconds = last_entry['start'] + last_entry['duration']
    video_duration_minutes = video_duration_seconds / 60

    # Format transcript for OpenAI
    start_time_format = time.time()
    formatted_transcript, transcript_length = format_transcript_for_model(transcript_data)
    logging.info(f"Formatted transcript ({transcript_length} lines) for {video_id} in {time.time() - start_time_format:.2f}s (User: {user_id})")

    # Create prompt
    system_prompt = create_chapter_prompt(video_duration_minutes)

    # Generate chapters with OpenAI
    start_time_openai = time.time()
    logging.info(f"Calling OpenAI to generate chapters for {video_id} (User: {user_id})")
    chapters = generate_chapters_with_openai(system_prompt, video_id, formatted_transcript)
    openai_duration = time.time() - start_time_openai
    logging.info(f"OpenAI call for {video_id} completed in {openai_duration:.2f}s (User: {user_id})")

    if not chapters:
        logging.error(f"Failed to generate chapters with OpenAI for {video_id} (User: {user_id})")
        return error_response('Failed to generate chapters with OpenAI', 500)

    # Count chapters
    chapter_count = len(chapters.strip().split("
"))
    logging.info(f"Generated {chapter_count} chapters for {video_id} (User: {user_id})")

    # --- Credit Deduction ---
    try:
        start_time_deduct = time.time()
        deduction_successful = await credits_service.deduct_credits(user_id)
        if not deduction_successful:
            logging.error(f"Failed to deduct credits for user {user_id} after successful generation for video {video_id}. Took {time.time() - start_time_deduct:.2f}s")
        else:
             logging.info(f"Successfully deducted 1 credit from user {user_id} for video {video_id}. Took {time.time() - start_time_deduct:.2f}s")
    except Exception as e:
        logging.error(f"Exception during credit deduction for user {user_id} video {video_id}: {e}")
    # --- End Credit Deduction ---

    # Add to cache
    start_time_cache = time.time()
    add_to_cache(video_id, chapters)
    logging.info(f"Added chapters for {video_id} to cache in {time.time() - start_time_cache:.2f}s (User: {user_id})")

    # Prepare response using helper
    return success_response({
        'videoId': video_id,
        'chapters': chapters,
        'fromCache': False
    })

# Ensure the old registration function is removed or commented out if present elsewhere
