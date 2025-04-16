import time
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, constr
from ..utils.responses import success_response, error_response
from ..utils.cache import get_from_cache, add_to_cache
from ..services.youtube import fetch_transcript
from ..services.openai_service import create_chapter_prompt, generate_chapters_with_openai
from ..utils.transcript import format_transcript_for_model
from ..services import credits_service
from ..utils.decorators import token_required_fastapi
from ..utils.db import redis_operation
import asyncio

LOCK_TTL_SECONDS = 120
LOCK_PREFIX = "chaptergen-lock:"

async def acquire_chapter_lock(redis, key: str, ttl: int = LOCK_TTL_SECONDS):
    # SET key value NX EX ttl
    return await redis.set(key, "locked", ex=ttl, nx=True)

async def release_chapter_lock(redis, key: str):
    await redis.delete(key)

router = APIRouter()

class GenerateChaptersRequest(BaseModel):
    video_id: constr(min_length=8, max_length=16, pattern=r"^[\w-]{8,16}$")

@router.post("/chapters/generate")
async def generate_chapters(body: GenerateChaptersRequest, user: User = Depends(token_required_fastapi)):
    """
    Generate chapters for a YouTube video, requiring authentication and credits.
    Implements distributed locking to prevent simultaneous generation.
    """
    video_id = body.video_id
    lock_key = f"{LOCK_PREFIX}{video_id}:{user.id}"
    lock_acquired = await redis_operation("acquire_chapter_lock", acquire_chapter_lock, lock_key, LOCK_TTL_SECONDS)
    if not lock_acquired:
        logging.warning(f"Lock not acquired for {lock_key}: another generation in progress.")
        raise HTTPException(status_code=429, detail="Chapter generation already in progress. Please try again shortly.")
    try:
        # --- Credit Check ---
        has_credits = await credits_service.has_sufficient_credits(user.id)
        if not has_credits:
            logging.warning(f"User {user.id} attempted generation with insufficient credits for video {video_id}.")
            raise HTTPException(status_code=402, detail="Insufficient credits to generate chapters.")

        # Check cache first
        cached_chapters = get_from_cache(video_id)
        if cached_chapters:
            logging.info(f"Returning cached chapters for {video_id} (User: {user.id})")
            return JSONResponse(content={
                'videoId': video_id,
                'chapters': cached_chapters,
                'fromCache': True
            })

        # Get transcript
        start_time_transcript = time.time()
        timeout_limit = 45
        logging.info(f"Attempting to fetch transcript for {video_id} with timeout {timeout_limit}s (User: {user.id})")
        transcript_data = fetch_transcript(video_id, timeout_limit)

        if not transcript_data:
            logging.error(f"Failed to fetch transcript for {video_id} after {time.time() - start_time_transcript:.2f} seconds (User: {user.id})")
            raise HTTPException(status_code=500, detail="Failed to fetch transcript after multiple attempts")

        elapsed_time_transcript = time.time() - start_time_transcript
        logging.info(f"Successfully retrieved transcript for {video_id} with {len(transcript_data)} entries in {elapsed_time_transcript:.2f} seconds (User: {user.id})")

        last_entry = transcript_data[-1]
        video_duration_seconds = last_entry['start'] + last_entry['duration']
        video_duration_minutes = video_duration_seconds / 60

        start_time_format = time.time()
        formatted_transcript, transcript_length = format_transcript_for_model(transcript_data)
        logging.info(f"Formatted transcript ({transcript_length} lines) for {video_id} in {time.time() - start_time_format:.2f}s (User: {user.id})")

        system_prompt = create_chapter_prompt(video_duration_minutes)

        start_time_openai = time.time()
        logging.info(f"Calling OpenAI to generate chapters for {video_id} (User: {user.id})")
        chapters = await generate_chapters_with_openai(system_prompt, video_id, formatted_transcript)
        openai_duration = time.time() - start_time_openai
        logging.info(f"OpenAI call for {video_id} completed in {openai_duration:.2f}s (User: {user.id})")

        if not chapters:
            logging.error(f"Failed to generate chapters with OpenAI for {video_id} (User: {user.id})")
            raise HTTPException(status_code=500, detail="Failed to generate chapters with OpenAI")

        chapter_count = len(chapters.strip().split("\n"))
        logging.info(f"Generated {chapter_count} chapters for {video_id} (User: {user.id})")

        # --- Credit Deduction ---
        try:
            start_time_deduct = time.time()
            deduction_successful = await credits_service.deduct_credits(user.id)
            if not deduction_successful:
                logging.error(f"Failed to deduct credits for user {user.id} after successful generation for video {video_id}. Took {time.time() - start_time_deduct:.2f}s")
            else:
                logging.info(f"Successfully deducted 1 credit from user {user.id} for video {video_id}. Took {time.time() - start_time_deduct:.2f}s")
        except Exception as e:
            logging.error(f"Exception during credit deduction for user {user.id} video {video_id}: {e}")
        # --- End Credit Deduction ---

        start_time_cache = time.time()
        add_to_cache(video_id, chapters)
        logging.info(f"Added chapters for {video_id} to cache in {time.time() - start_time_cache:.2f}s (User: {user.id})")

        return JSONResponse(content={
            'videoId': video_id,
            'chapters': chapters,
            'fromCache': False
        })
    finally:
        await redis_operation("release_chapter_lock", release_chapter_lock, lock_key)

@router.get("/chapters")
def get_chapters():
    return JSONResponse(content={"message": "Chapters endpoint migrated to FastAPI!"})
