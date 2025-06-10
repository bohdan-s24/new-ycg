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

def fetch_transcript(video_id: str, timeout_limit: int = 30) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch transcript using pytubefix with proper error handling and language preferences.

    Args:
        video_id: YouTube video ID
        timeout_limit: Maximum time in seconds to spend fetching the transcript

    Returns:
        List of transcript entries or None if failed
    """
    start_time = time.time()

    def time_left() -> bool:
        """Check if we still have time to continue operations"""
        elapsed = time.time() - start_time
        return elapsed < timeout_limit

    print(f"Fetching transcript for {video_id} using pytubefix, timeout limit: {timeout_limit}s")

    try:
        # Create YouTube object
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        yt = YouTube(video_url)

        if not time_left():
            print(f"Time limit reached while creating YouTube object")
            return None

        # Check if captions are available
        if not yt.captions:
            print(f"No captions available for video {video_id}")
            return None

        print(f"Available captions for {video_id}: {list(yt.captions.keys())}")

        # Try to find the best caption track based on language preferences
        caption = None
        selected_lang = None

        # First, try to find manual captions in preferred languages
        for lang_code in Config.TRANSCRIPT_LANGUAGES:
            # Try exact match
            if lang_code in yt.captions:
                caption = yt.captions[lang_code]
                selected_lang = lang_code
                print(f"Found manual caption in preferred language: {lang_code}")
                break
            # Try auto-generated format (a.lang)
            auto_lang = f"a.{lang_code}"
            if auto_lang in yt.captions:
                caption = yt.captions[auto_lang]
                selected_lang = auto_lang
                print(f"Found auto-generated caption in preferred language: {auto_lang}")
                break

        # If no preferred language found, use the first available caption
        if not caption:
            first_caption_key = next(iter(yt.captions))
            caption = yt.captions[first_caption_key]
            selected_lang = first_caption_key
            print(f"Using first available caption: {first_caption_key}")

        if not time_left():
            print(f"Time limit reached while selecting caption")
            return None

        # Generate SRT captions and parse them
        print(f"Generating captions for language: {selected_lang}")
        srt_captions = caption.generate_srt_captions()

        if not time_left():
            print(f"Time limit reached while generating captions")
            return None

        # Parse SRT format to our expected format
        transcript_entries = _parse_srt_to_transcript(srt_captions)

        if transcript_entries:
            print(f"Successfully fetched transcript for {video_id} with {len(transcript_entries)} entries")
            return transcript_entries
        else:
            print(f"Failed to parse transcript entries for {video_id}")
            return None

    except (VideoUnavailable, VideoPrivate, VideoRegionBlocked) as e:
        print(f"Video not accessible for {video_id}: {type(e).__name__}: {e}")
        return None

    except (AgeRestrictedError, MembersOnly, RecordingUnavailable) as e:
        print(f"Access restricted for {video_id}: {type(e).__name__}: {e}")
        return None

    except LiveStreamError as e:
        print(f"Live stream error for {video_id}: {type(e).__name__}: {e}")
        return None

    except PytubeFixError as e:
        print(f"PytubeFixError for {video_id}: {type(e).__name__}: {e}")
        return None

    except Exception as e:
        print(f"Unexpected error fetching transcript for {video_id}: {type(e).__name__}: {e}")
        traceback.print_exc()
        return None


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
