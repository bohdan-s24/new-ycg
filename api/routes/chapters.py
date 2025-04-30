import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, constr
from ..utils.responses import success_response
from ..utils.cache import get_from_cache, add_to_cache
from ..services.youtube import fetch_transcript
from ..services.openai_service import create_chapter_prompt, generate_chapters_with_openai
from ..utils.transcript import format_transcript_for_model
from ..services import credits_service
from ..utils.decorators import token_required_fastapi
from ..utils.db import redis_operation
from ..models.user import User

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
    force: bool = False

# --- Add parse_chapters_text helper ---
def parse_chapters_text(chapters_text: str):
    parsed_chapters = []
    formatted_text = chapters_text
    for line in chapters_text.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split(' ', 1)
        if len(parts) == 2:
            time, title = parts
            parsed_chapters.append({'time': time.strip(), 'title': title.strip()})
    return parsed_chapters, formatted_text

@router.post("/chapters/generate")
async def generate_chapters(body: GenerateChaptersRequest, user: User = Depends(token_required_fastapi)):
    """
    Generate chapters for a YouTube video, requiring authentication and credits.
    Implements distributed locking to prevent simultaneous generation.
    """
    video_id = body.video_id
    lock_key = f"{LOCK_PREFIX}{video_id}:{user.id}"
    logging.info(f"[CHAPTERS-DEBUG] generate_chapters called for video_id={video_id}, user_id={user.id}, force={body.force}")

    cache_obj = get_from_cache(video_id)
    # If force regenerate and cached transcript exists, skip lock and transcript fetching
    if body.force and cache_obj and cache_obj.get('transcript'):
        # Check generation count and calculate credits needed
        credits_needed = await credits_service.calculate_credits_needed(user.id, video_id)

        # If max generations reached
        if credits_needed == -1:
            logging.warning(f"User {user.id} reached maximum regenerations for video {video_id}")
            raise HTTPException(status_code=403, detail="Maximum regenerations reached for this video (5 regenerations maximum)")

        # Check if user has enough credits
        has_credits = await credits_service.has_sufficient_credits(user.id, credits_needed)
        if not has_credits:
            logging.warning(f"User {user.id} attempted regeneration with insufficient credits for video {video_id}")
            raise HTTPException(status_code=402, detail="Insufficient credits to regenerate chapters")

        transcript_data = cache_obj['transcript']
        logging.info(f"[CHAPTERS-DEBUG] Using cached transcript for {video_id} (User: {user.id})")
        # Rebuild prompt as in initial generation
        formatted_transcript, _ = format_transcript_for_model(transcript_data)
        # Estimate duration
        last_entry = transcript_data[-1]
        video_duration_seconds = last_entry['start'] + last_entry['duration']
        video_duration_minutes = video_duration_seconds / 60
        system_prompt = create_chapter_prompt(video_duration_minutes)
        chapters = await generate_chapters_with_openai(system_prompt, video_id, formatted_transcript)
        if not chapters:
            logging.error(f"Failed to generate chapters with OpenAI for {video_id} (User: {user.id}) [prompt replay]")
            raise HTTPException(status_code=500, detail="Failed to generate chapters with OpenAI")

        # Increment generation count first
        new_count = await credits_service.increment_video_generation_count(user.id, video_id)
        logging.info(f"Incremented generation count for video {video_id} (User: {user.id}). New count: {new_count}")

        # Deduct credits based on the calculated amount
        try:
            deduction_successful = await credits_service.deduct_credits(user.id, credits_needed, f"Chapter regeneration ({new_count})")
            logging.info(f"Deduction successful: {deduction_successful}, credits used: {credits_needed}")
        except Exception as e:
            logging.error(f"Exception during credit deduction for user {user.id} video {video_id}: {e}")

        add_to_cache(video_id, chapters, transcript_data)
        parsed_chapters, formatted_text = parse_chapters_text(chapters)

        # Get remaining generations
        remaining_generations = await credits_service.get_remaining_generations(user.id, video_id)

        return JSONResponse(content={
            'videoId': video_id,
            'chapters': parsed_chapters,
            'formatted_text': formatted_text,
            'fromCache': False,
            'generationCount': new_count,
            'remainingGenerations': remaining_generations
        })

    # Otherwise, use lock for initial generation or if transcript is not cached
    lock_acquired = await redis_operation("acquire_chapter_lock", acquire_chapter_lock, lock_key, LOCK_TTL_SECONDS)
    if not lock_acquired:
        logging.warning(f"Lock not acquired for {lock_key}: another generation in progress.")
        raise HTTPException(status_code=429, detail="Chapter generation already in progress. Please try again shortly.")
    try:
        # Check generation count and calculate credits needed
        credits_needed = await credits_service.calculate_credits_needed(user.id, video_id)

        # If max generations reached
        if credits_needed == -1:
            logging.warning(f"User {user.id} reached maximum regenerations for video {video_id}")
            raise HTTPException(status_code=403, detail="Maximum regenerations reached for this video (5 regenerations maximum)")

        # Check if user has enough credits
        has_credits = await credits_service.has_sufficient_credits(user.id, credits_needed)
        logging.info(f"[CHAPTERS-DEBUG] User {user.id} has credits: {has_credits}, needs: {credits_needed}")

        if not has_credits:
            logging.warning(f"User {user.id} attempted generation with insufficient credits for video {video_id}.")
            raise HTTPException(status_code=402, detail="Insufficient credits to generate chapters.")

        # Return cached chapters if available and not forcing regeneration
        if not body.force:
            if cache_obj and cache_obj.get('chapters'):
                logging.info(f"Returning cached chapters for {video_id} (User: {user.id})")
                parsed_chapters, formatted_text = parse_chapters_text(cache_obj['chapters'])
                # Get current generation count and remaining generations
                current_count = await credits_service.get_video_generation_count(user.id, video_id)
                remaining_generations = await credits_service.get_remaining_generations(user.id, video_id)

                return JSONResponse(content={
                    'videoId': video_id,
                    'chapters': parsed_chapters,
                    'formatted_text': formatted_text,
                    'fromCache': True,
                    'generationCount': current_count,
                    'remainingGenerations': remaining_generations
                })

        # Get transcript and format it
        timeout_limit = 45
        logging.info(f"Attempting to fetch transcript for {video_id} with timeout {timeout_limit}s (User: {user.id})")
        transcript_data = fetch_transcript(video_id, timeout_limit)
        if not transcript_data:
            logging.error(f"Failed to fetch transcript for {video_id} (User: {user.id})")
            raise HTTPException(status_code=500, detail="Failed to fetch transcript after multiple attempts")

        formatted_transcript, _ = format_transcript_for_model(transcript_data)
        last_entry = transcript_data[-1]
        video_duration_seconds = last_entry['start'] + last_entry['duration']
        video_duration_minutes = video_duration_seconds / 60
        system_prompt = create_chapter_prompt(video_duration_minutes)
        chapters = await generate_chapters_with_openai(system_prompt, video_id, formatted_transcript)

        if not chapters:
            logging.error(f"Failed to generate chapters with OpenAI for {video_id} (User: {user.id})")
            raise HTTPException(status_code=500, detail="Failed to generate chapters with OpenAI")

        # Increment generation count first
        new_count = await credits_service.increment_video_generation_count(user.id, video_id)
        logging.info(f"Incremented generation count for video {video_id} (User: {user.id}). New count: {new_count}")

        # Deduct credits based on the calculated amount
        try:
            generation_type = "Initial chapter generation" if new_count == 1 else f"Chapter regeneration ({new_count})"
            deduction_successful = await credits_service.deduct_credits(user.id, credits_needed, generation_type)
            logging.info(f"Deduction successful: {deduction_successful}, credits used: {credits_needed}")
        except Exception as e:
            logging.error(f"Exception during credit deduction for user {user.id} video {video_id}: {e}")

        add_to_cache(video_id, chapters, transcript_data)
        parsed_chapters, formatted_text = parse_chapters_text(chapters)

        # Get remaining generations
        remaining_generations = await credits_service.get_remaining_generations(user.id, video_id)

        return JSONResponse(content={
            'videoId': video_id,
            'chapters': parsed_chapters,
            'formatted_text': formatted_text,
            'fromCache': False,
            'generationCount': new_count,
            'remainingGenerations': remaining_generations
        })
    finally:
        await redis_operation("release_chapter_lock", release_chapter_lock, lock_key)

@router.get("/chapters")
def get_chapters():
    return JSONResponse(content={"message": "Chapters endpoint migrated to FastAPI!"})
