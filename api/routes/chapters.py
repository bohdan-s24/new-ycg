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
    # Start timing the entire operation
    total_start_time = time.time()

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

    logging.info(f"[CHAPTERS] Generate request received for video {video_id} from user {user_id}")

    # --- Credit Check ---
    try:
        has_credits = await credits_service.has_sufficient_credits(user_id)
        if not has_credits:
            logging.warning(f"[CHAPTERS] User {user_id} attempted generation with insufficient credits for video {video_id}.")
            # 402 Payment Required is appropriate here
            return error_response('Insufficient credits to generate chapters.', 402)
    except Exception as e:
        logging.error(f"[CHAPTERS] Error checking credits for user {user_id}: {e}")
        return error_response("Failed to verify credit balance.", 500)
    # --- End Credit Check ---

    # Check cache first (still useful to avoid re-generation even if credits are checked)
    cached_chapters = get_from_cache(video_id)
    if cached_chapters:
        logging.info(f"[CHAPTERS] Returning cached chapters for {video_id} (User: {user_id})")
        # Note: We don't deduct credits if serving from cache
        return success_response({
            'videoId': video_id,
            'chapters': cached_chapters,
            'fromCache': True
        })

    # Get transcript - using a reduced timeout to avoid Vercel function timeouts
    start_time_transcript = time.time()
    # Reduced timeout limit to ensure we have time for OpenAI call
    timeout_limit = 25 # Reduced from 45 to leave more time for OpenAI
    logging.info(f"[CHAPTERS] Fetching transcript for {video_id} with timeout {timeout_limit}s (User: {user_id})")
    transcript_data = fetch_transcript(video_id, timeout_limit)

    if not transcript_data:
        logging.error(f"[CHAPTERS] Failed to fetch transcript for {video_id} after {time.time() - start_time_transcript:.2f} seconds (User: {user_id})")
        return error_response('Failed to fetch transcript after multiple attempts', 500)

    elapsed_time_transcript = time.time() - start_time_transcript
    logging.info(f"[CHAPTERS] Retrieved transcript for {video_id} with {len(transcript_data)} entries in {elapsed_time_transcript:.2f}s (User: {user_id})")

    # Check if we're approaching Vercel's timeout limit
    elapsed_so_far = time.time() - total_start_time
    if elapsed_so_far > 40:  # If we've already used 40 seconds of our 60 second limit
        logging.warning(f"[CHAPTERS] Approaching timeout limit ({elapsed_so_far:.2f}s elapsed). Returning error to avoid Vercel timeout.")
        return error_response('Processing taking too long. Please try again.', 503)

    # Format transcript for OpenAI - streamlined
    formatted_transcript, transcript_length = format_transcript_for_model(transcript_data)
    logging.info(f"[CHAPTERS] Formatted transcript ({transcript_length} lines) for {video_id}")

    # Calculate video duration from the last transcript entry
    last_entry = transcript_data[-1]
    video_duration_seconds = last_entry['start'] + last_entry['duration']
    video_duration_minutes = video_duration_seconds / 60

    # Generate chapters with OpenAI - create a prompt based on the video duration
    start_time_openai = time.time()
    logging.info(f"[CHAPTERS] Calling OpenAI to generate chapters for {video_id} (User: {user_id})")

    # Create a system prompt based on the video duration
    system_prompt = create_chapter_prompt(video_duration_minutes)

    # Pass both the system prompt and formatted transcript to OpenAI
    chapters = generate_chapters_with_openai(system_prompt, video_id, formatted_transcript)

    openai_duration = time.time() - start_time_openai
    logging.info(f"[CHAPTERS] OpenAI call completed in {openai_duration:.2f}s (User: {user_id})")

    if not chapters:
        logging.error(f"[CHAPTERS] Failed to generate chapters with OpenAI for {video_id} (User: {user_id})")
        return error_response('Failed to generate chapters with OpenAI', 500)

    # Count chapters
    chapter_count = len(chapters.strip().split("\n"))
    logging.info(f"[CHAPTERS] Generated {chapter_count} chapters for {video_id} (User: {user_id})")

    # --- Credit Deduction ---
    try:
        deduction_successful = await credits_service.deduct_credits(user_id)
        if not deduction_successful:
            logging.error(f"[CHAPTERS] Failed to deduct credits for user {user_id} after successful generation")
        else:
             logging.info(f"[CHAPTERS] Successfully deducted 1 credit from user {user_id} for video {video_id}")
    except Exception as e:
        logging.error(f"[CHAPTERS] Exception during credit deduction for user {user_id}: {e}")
    # --- End Credit Deduction ---

    # Add to cache
    add_to_cache(video_id, chapters)

    # Log total time
    total_time = time.time() - total_start_time
    logging.info(f"[CHAPTERS] Total processing time for {video_id}: {total_time:.2f}s (User: {user_id})")

    # Prepare response using helper
    return success_response({
        'videoId': video_id,
        'chapters': chapters,
        'fromCache': False
    })

# Ensure the old registration function is removed or commented out if present elsewhere
