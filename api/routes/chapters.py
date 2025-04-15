import time
import logging
import json
import uuid
import asyncio
from flask import request, g
from typing import List, Dict, Optional

# Import necessary services, utils, and decorators
from ..utils.responses import success_response, error_response
from ..utils.cache import get_from_cache, add_to_cache
from ..services.youtube import fetch_transcript
from ..services.openai_service import create_chapter_prompt, generate_chapters_with_openai
from ..utils.transcript import format_transcript_for_model
from ..utils.decorators import token_required
from ..services import credits_service
from ..utils.versioning import VersionedBlueprint
from ..config import Config


def parse_chapters_text(chapters_text: str) -> tuple[List[Dict[str, str]], str]:
    """
    Parse the raw chapters text into a structured format for the frontend.

    Args:
        chapters_text: Raw chapters text from OpenAI

    Returns:
        Tuple of (parsed_chapters, formatted_text)
    """
    parsed_chapters = []
    formatted_text = chapters_text

    # Parse each line of the chapters text
    for line in chapters_text.strip().split('\n'):
        if not line.strip():
            continue

        # Extract time and title
        parts = line.split(' ', 1)
        if len(parts) == 2:
            time = parts[0].strip()
            title = parts[1].strip()
            parsed_chapters.append({
                'time': time,
                'title': title
            })

    return parsed_chapters, formatted_text

# Create a versioned blueprint
chapters_bp = VersionedBlueprint('chapters', __name__, url_prefix='/chapters')

# In-memory job store for development (in production, this would be Redis)
# Structure: {job_id: {status, result, created_at, video_id, user_id}}
JOB_STORE = {}

# Helper function to create a new job
def create_job(video_id: str, user_id: str) -> str:
    job_id = str(uuid.uuid4())
    JOB_STORE[job_id] = {
        'status': 'pending',
        'result': None,
        'created_at': time.time(),
        'video_id': video_id,
        'user_id': user_id
    }
    return job_id

# Helper function to update a job
def update_job(job_id: str, status: str, result=None) -> None:
    if job_id in JOB_STORE:
        JOB_STORE[job_id]['status'] = status
        if result is not None:
            JOB_STORE[job_id]['result'] = result

# Helper function to get a job
def get_job(job_id: str) -> Optional[dict]:
    return JOB_STORE.get(job_id)

# Define the route for submitting a chapter generation job
@chapters_bp.route('/submit-job', methods=['POST'])
@token_required
async def submit_chapter_job():
    """
    Submit a job to generate chapters for a YouTube video.
    Returns a job ID that can be used to check the status of the job.
    """
    # Start timing the entire operation
    total_start_time = time.time()

    # Get user_id from the decorator via Flask's g context
    user_id = getattr(g, 'current_user_id', None)
    if not user_id:
        logging.error("User ID not found in g context within submit_chapter_job route.")
        return error_response("Authentication context error.", 500)

    # Extract video ID from request
    data = request.get_json()
    if not data:
        return error_response('Request must be JSON', 400)

    video_id = data.get('video_id')
    if not video_id:
        return error_response('Missing video_id parameter', 400)

    logging.info(f"[CHAPTERS] Job submission received for video {video_id} from user {user_id}")

    # --- Credit Check ---
    try:
        has_credits = await credits_service.has_sufficient_credits(user_id)
        if not has_credits:
            logging.warning(f"[CHAPTERS] User {user_id} attempted job submission with insufficient credits for video {video_id}.")
            return error_response('Insufficient credits to generate chapters.', 402)
    except Exception as e:
        logging.error(f"[CHAPTERS] Error checking credits for user {user_id}: {e}")
        return error_response("Failed to verify credit balance.", 500)
    # --- End Credit Check ---

    # Check cache first (still useful to avoid re-generation even if credits are checked)
    cached_chapters = get_from_cache(video_id)
    if cached_chapters:
        logging.info(f"[CHAPTERS] Returning cached chapters for {video_id} (User: {user_id})")

        # Parse the cached chapters text into the format expected by the frontend
        parsed_chapters, formatted_text = parse_chapters_text(cached_chapters)

        # Note: We don't deduct credits if serving from cache
        return success_response({
            'videoId': video_id,
            'chapters': parsed_chapters,
            'formatted_text': formatted_text,
            'fromCache': True
        })

    # Create a new job
    job_id = create_job(video_id, user_id)
    logging.info(f"[CHAPTERS] Created job {job_id} for video {video_id} (User: {user_id})")

    # Start the job in the background (in a real system, this would be a queue worker)
    # We're using asyncio.create_task to run this in the background without blocking
    asyncio.create_task(process_chapter_job(job_id, video_id, user_id))

    # Return the job ID to the client
    return success_response({
        'job_id': job_id,
        'status': 'pending',
        'message': 'Chapter generation job submitted successfully'
    })

# Define the route for checking the status of a job
@chapters_bp.route('/job-status/<job_id>', methods=['GET'])
@token_required
async def check_job_status(job_id):
    """
    Check the status of a chapter generation job.
    """
    # Get user_id from the decorator via Flask's g context
    user_id = getattr(g, 'current_user_id', None)
    if not user_id:
        logging.error("User ID not found in g context within check_job_status route.")
        return error_response("Authentication context error.", 500)

    # Get the job
    job = get_job(job_id)
    if not job:
        return error_response('Job not found', 404)

    # Check if the job belongs to the user
    if job['user_id'] != user_id:
        return error_response('Unauthorized', 403)

    # Return the job status
    response = {
        'job_id': job_id,
        'status': job['status'],
        'video_id': job['video_id']
    }

    # If the job is complete, include the result
    if job['status'] == 'completed' and job['result']:
        response['chapters'] = job['result']['chapters']
        response['formatted_text'] = job['result']['formatted_text']

    # If the job failed, include the error message
    if job['status'] == 'failed' and job['result']:
        response['error'] = job['result']['error']

    return success_response(response)

# Background task to process a chapter generation job
async def process_chapter_job(job_id: str, video_id: str, user_id: str):
    """
    Process a chapter generation job in the background.
    """
    try:
        # Update job status to processing
        update_job(job_id, 'processing')
        logging.info(f"[CHAPTERS] Processing job {job_id} for video {video_id} (User: {user_id})")

        # Get transcript with a shorter timeout
        timeout_limit = 20  # 20 seconds timeout for transcript fetching
        logging.info(f"[CHAPTERS] Fetching transcript for {video_id} with timeout {timeout_limit}s (User: {user_id})")
        transcript_data = fetch_transcript(video_id, timeout_limit)

        if not transcript_data:
            logging.error(f"[CHAPTERS] Failed to fetch transcript for {video_id} (User: {user_id})")
            update_job(job_id, 'failed', {'error': 'Failed to fetch transcript'})
            return

        logging.info(f"[CHAPTERS] Retrieved transcript for {video_id} with {len(transcript_data)} entries (User: {user_id})")

        # Format transcript for OpenAI
        formatted_transcript, transcript_length = format_transcript_for_model(transcript_data)
        logging.info(f"[CHAPTERS] Formatted transcript ({transcript_length} lines) for {video_id}")

        # Calculate video duration from the last transcript entry
        last_entry = transcript_data[-1]
        video_duration_seconds = last_entry['start'] + last_entry['duration']
        video_duration_minutes = video_duration_seconds / 60

        # Create a system prompt based on the video duration
        system_prompt = create_chapter_prompt(video_duration_minutes)

        # Generate chapters with OpenAI
        logging.info(f"[CHAPTERS] Calling OpenAI to generate chapters for {video_id} (User: {user_id})")
        chapters_text = generate_chapters_with_openai(system_prompt, video_id, formatted_transcript)

        if not chapters_text:
            logging.error(f"[CHAPTERS] Failed to generate chapters with OpenAI for {video_id} (User: {user_id})")
            update_job(job_id, 'failed', {'error': 'Failed to generate chapters with OpenAI'})
            return

        # Parse the chapters text
        parsed_chapters, formatted_text = parse_chapters_text(chapters_text)

        # Add to cache
        add_to_cache(video_id, chapters_text)

        # Deduct credits
        deduction_successful = await credits_service.deduct_credits(user_id)
        if not deduction_successful:
            logging.error(f"[CHAPTERS] Failed to deduct credits for user {user_id} after successful generation")
        else:
            logging.info(f"[CHAPTERS] Successfully deducted 1 credit from user {user_id} for video {video_id}")

        # Update job status to completed
        update_job(job_id, 'completed', {
            'chapters': parsed_chapters,
            'formatted_text': formatted_text
        })

        logging.info(f"[CHAPTERS] Completed job {job_id} for video {video_id} (User: {user_id})")
    except Exception as e:
        logging.error(f"[CHAPTERS] Error processing job {job_id} for video {video_id} (User: {user_id}): {str(e)}")
        update_job(job_id, 'failed', {'error': str(e)})

# Define the original route for backward compatibility
@chapters_bp.route('/generate', methods=['POST'])
@token_required # Apply the authentication decorator
async def generate_chapters():
    """
    Generate chapters for a YouTube video, requiring authentication and credits.
    This is the original endpoint, kept for backward compatibility.
    It now uses the job-based approach internally.
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

    logging.info(f"[CHAPTERS] Generate request received for video {video_id} from user {user_id}")

    # Check cache first (still useful to avoid re-generation even if credits are checked)
    cached_chapters_text = get_from_cache(video_id)
    if cached_chapters_text:
        logging.info(f"[CHAPTERS] Returning cached chapters for {video_id} (User: {user_id})")

        # Parse the cached chapters text into the format expected by the frontend
        parsed_chapters, formatted_text = parse_chapters_text(cached_chapters_text)

        # Note: We don't deduct credits if serving from cache
        return success_response({
            'videoId': video_id,
            'chapters': parsed_chapters,
            'formatted_text': formatted_text,
            'fromCache': True
        })

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

    # For the original endpoint, we'll use the job-based approach but wait for a short time
    # to see if the job completes quickly

    # Create a new job
    job_id = create_job(video_id, user_id)
    logging.info(f"[CHAPTERS] Created job {job_id} for video {video_id} (User: {user_id})")

    # Start the job in the background
    task = asyncio.create_task(process_chapter_job(job_id, video_id, user_id))

    # Wait for a short time to see if the job completes quickly
    try:
        # Wait for up to 10 seconds for the job to complete
        await asyncio.wait_for(task, timeout=10.0)

        # If we get here, the job completed within the timeout
        job = get_job(job_id)

        if job['status'] == 'completed' and job['result']:
            # Job completed successfully, return the result
            return success_response({
                'videoId': video_id,
                'chapters': job['result']['chapters'],
                'formatted_text': job['result']['formatted_text'],
                'fromCache': False
            })
        elif job['status'] == 'failed' and job['result']:
            # Job failed, return the error
            return error_response(job['result']['error'], 500)
        else:
            # Job is still processing, return the job ID
            return success_response({
                'job_id': job_id,
                'status': job['status'],
                'message': 'Chapter generation is taking longer than expected. Please check back in a few moments.'
            })
    except asyncio.TimeoutError:
        # Job didn't complete within the timeout, return the job ID
        logging.info(f"[CHAPTERS] Job {job_id} for video {video_id} is taking longer than expected (User: {user_id})")
        return success_response({
            'job_id': job_id,
            'status': 'processing',
            'message': 'Chapter generation is taking longer than expected. Please check back in a few moments.'
        })

# Ensure the old registration function is removed or commented out if present elsewhere
