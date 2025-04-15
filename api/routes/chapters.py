import time
import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from ..utils.responses import success_response, error_response
from ..utils.cache import get_from_cache, add_to_cache
from ..services.youtube import fetch_transcript
from ..services.openai_service import create_chapter_prompt, generate_chapters_with_openai
from ..utils.transcript import format_transcript_for_model
from ..services import credits_service
from ..utils.decorators import token_required_fastapi

router = APIRouter()

@router.post("/chapters/generate")
async def generate_chapters(request: Request, user_id: str = Depends(token_required_fastapi)):
    """
    Generate chapters for a YouTube video, requiring authentication and credits.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request must be JSON")

    video_id = data.get('video_id')
    if not video_id:
        raise HTTPException(status_code=400, detail="Missing video_id parameter")

    # --- Credit Check ---
    try:
        has_credits = await credits_service.has_sufficient_credits(user_id)
        if not has_credits:
            logging.warning(f"User {user_id} attempted generation with insufficient credits for video {video_id}.")
            raise HTTPException(status_code=402, detail="Insufficient credits to generate chapters.")
    except Exception as e:
        logging.error(f"Error checking credits for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify credit balance.")
    # --- End Credit Check ---

    # Check cache first
    cached_chapters = get_from_cache(video_id)
    if cached_chapters:
        logging.info(f"Returning cached chapters for {video_id} (User: {user_id})")
        return JSONResponse(content={
            'videoId': video_id,
            'chapters': cached_chapters,
            'fromCache': True
        })

    # Get transcript
    start_time_transcript = time.time()
    timeout_limit = 45
    logging.info(f"Attempting to fetch transcript for {video_id} with timeout {timeout_limit}s (User: {user_id})")
    transcript_data = fetch_transcript(video_id, timeout_limit)

    if not transcript_data:
        logging.error(f"Failed to fetch transcript for {video_id} after {time.time() - start_time_transcript:.2f} seconds (User: {user_id})")
        raise HTTPException(status_code=500, detail="Failed to fetch transcript after multiple attempts")

    elapsed_time_transcript = time.time() - start_time_transcript
    logging.info(f"Successfully retrieved transcript for {video_id} with {len(transcript_data)} entries in {elapsed_time_transcript:.2f} seconds (User: {user_id})")

    last_entry = transcript_data[-1]
    video_duration_seconds = last_entry['start'] + last_entry['duration']
    video_duration_minutes = video_duration_seconds / 60

    start_time_format = time.time()
    formatted_transcript, transcript_length = format_transcript_for_model(transcript_data)
    logging.info(f"Formatted transcript ({transcript_length} lines) for {video_id} in {time.time() - start_time_format:.2f}s (User: {user_id})")

    system_prompt = create_chapter_prompt(video_duration_minutes)

    start_time_openai = time.time()
    logging.info(f"Calling OpenAI to generate chapters for {video_id} (User: {user_id})")
    chapters = generate_chapters_with_openai(system_prompt, video_id, formatted_transcript)
    openai_duration = time.time() - start_time_openai
    logging.info(f"OpenAI call for {video_id} completed in {openai_duration:.2f}s (User: {user_id})")

    if not chapters:
        logging.error(f"Failed to generate chapters with OpenAI for {video_id} (User: {user_id})")
        raise HTTPException(status_code=500, detail="Failed to generate chapters with OpenAI")

    chapter_count = len(chapters.strip().split("\n"))
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

    start_time_cache = time.time()
    add_to_cache(video_id, chapters)
    logging.info(f"Added chapters for {video_id} to cache in {time.time() - start_time_cache:.2f}s (User: {user_id})")

    return JSONResponse(content={
        'videoId': video_id,
        'chapters': chapters,
        'fromCache': False
    })

@router.get("/chapters")
def get_chapters():
    return JSONResponse(content={"message": "Chapters endpoint migrated to FastAPI!"})
