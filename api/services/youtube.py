"""
YouTube transcript fetching services using pytubefix
"""
import time
import traceback
from typing import List, Dict, Any, Optional
import re

from pytubefix import YouTube
from pytubefix.exceptions import (
    VideoUnavailable,
    VideoPrivate,
    VideoRegionBlocked,
    AgeRestrictedError,
    LiveStreamError,
    MembersOnly,
    RecordingUnavailable,
    PytubeFixError
)

from api.config import Config
# Decodo proxy config does not require SSL CA patching or special logic

def fetch_transcript(video_id: str, timeout_limit: int = 30) -> Optional[str]:
    """
    Fetch transcript using pytubefix with proper error handling and language preferences.

    Args:
        video_id: YouTube video ID
        timeout_limit: Maximum time in seconds to spend fetching the transcript

    Returns:
        Transcript text or None if failed
    """
    import time
    import os
    import platform
    import socket
    import traceback
    start_time = time.time()

    def time_left() -> bool:
        elapsed = time.time() - start_time
        return elapsed < timeout_limit

    print(f"Fetching transcript for {video_id} using pytubefix, timeout limit: {timeout_limit}s")

    # Environment info logging
    print(f"Environment info: platform={platform.platform()}, hostname={socket.gethostname()}, pid={os.getpid()}")

    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        from pytubefix import YouTube

        yt = YouTube(video_url)

        if not time_left():
            print(f"Time limit reached while creating YouTube object")
            return None

        print(f"DEBUG: Captions detected for video {video_id}: {list(yt.captions.keys())}")

        if not yt.captions:
            print(f"No captions available for video {video_id}")
            return None

        caption = None

        for lang in Config.TRANSCRIPT_LANGUAGES:
            if lang in yt.captions:
                caption = yt.captions[lang]
                print(f"Found manual caption in preferred language: {lang}")
                break
            elif f"a.{lang}" in yt.captions:
                caption = yt.captions[f"a.{lang}"]
                print(f"Found auto-generated caption in preferred language: a.{lang}")
                break

        if not caption:
            caption_key = next(iter(yt.captions))
            caption = yt.captions[caption_key]
            print(f"Using first available caption: {caption_key}")

        srt_captions = caption.generate_srt_captions()
        txt_captions = caption.generate_txt_captions()

        return txt_captions

    except Exception as e:
        print(f"Error fetching transcript for {video_id}: {e}")
        traceback.print_exc()
        return None


async def extract_youtube_transcript(state):
    """
    Extract YouTube transcript and generate chapters using OpenAI.

    Args:
        state: Object containing URL and other info

    Returns:
        Dictionary with content, title, and metadata including video_id and transcript
    """
    from api.services.openai_service import generate_chapters_with_openai
    from api.utils.transcript import format_transcript_for_model
    import logging

    assert state.url, "No URL provided"
    logging.warning(f"Extracting transcript from URL: {state.url}")
    languages = Config.TRANSCRIPT_LANGUAGES

    video_id = await _extract_youtube_id(state.url)

    try:
        title = await get_video_title(video_id)
    except Exception as e:
        logging.critical(f"Failed to get video title for video_id: {video_id}")
        logging.exception(e)
        title = ""

    transcript_text = fetch_transcript(video_id)
    if not transcript_text:
        logging.error(f"Failed to fetch transcript for video_id: {video_id}")
        return None

    # Optionally parse SRT to structured transcript for formatting
    # But since fetch_transcript returns txt captions, we can use directly
    formatted_transcript = transcript_text

    # Estimate video duration from transcript or set default
    # Here we set default 60 minutes, can be improved by parsing timestamps
    video_duration_minutes = 60

    system_prompt = create_chapter_prompt(video_duration_minutes)

    chapters = await generate_chapters_with_openai(
        system_prompt=system_prompt,
        video_id=video_id,
        formatted_transcript=formatted_transcript,
        video_duration_minutes=video_duration_minutes,
    )

    return {
        "content": chapters,
        "title": title,
        "metadata": {"video_id": video_id, "transcript": transcript_text},
    }


def _parse_srt_to_transcript(srt_content: str) -> List[Dict[str, Any]]:
    """
    Parse SRT format captions to our expected transcript format.

    Args:
        srt_content: SRT formatted caption content

    Returns:
        List of transcript entries with text, start, and duration
    """
    transcript_entries = []

    # Split SRT content into blocks
    blocks = srt_content.strip().split('\n\n')

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        try:
            # Parse timestamp line (format: 00:00:01,000 --> 00:00:04,000)
            timestamp_line = lines[1]
            start_time_str, end_time_str = timestamp_line.split(' --> ')

            # Convert timestamp to seconds
            start_seconds = _timestamp_to_seconds(start_time_str)
            end_seconds = _timestamp_to_seconds(end_time_str)
            duration = end_seconds - start_seconds

            # Get text content (everything after the timestamp line)
            text = ' '.join(lines[2:]).strip()

            # Clean up text (remove HTML tags if any)
            text = re.sub(r'<[^>]+>', '', text)

            if text:  # Only add if there's actual text
                transcript_entries.append({
                    'text': text,
                    'start': start_seconds,
                    'duration': duration
                })

        except (ValueError, IndexError) as e:
            print(f"Error parsing SRT block: {e}")
            continue

    return transcript_entries


def _timestamp_to_seconds(timestamp: str) -> float:
    """
    Convert SRT timestamp format (HH:MM:SS,mmm) to seconds.

    Args:
        timestamp: Timestamp in format HH:MM:SS,mmm

    Returns:
        Time in seconds as float
    """
    # Replace comma with dot for milliseconds
    timestamp = timestamp.replace(',', '.')

    # Split into time parts
    time_parts = timestamp.split(':')
    hours = int(time_parts[0])
    minutes = int(time_parts[1])
    seconds_and_ms = float(time_parts[2])

    total_seconds = hours * 3600 + minutes * 60 + seconds_and_ms
    return total_seconds


# Legacy function removed - now using pytubefix for all transcript fetching
