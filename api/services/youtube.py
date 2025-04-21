"""
YouTube transcript fetching services
"""
import json
import time
import traceback
import asyncio
import httpx
import requests
import os
from typing import List, Dict, Any, Optional, Callable

from youtube_transcript_api import (
    YouTubeTranscriptApi, 
    TranscriptsDisabled, 
    NoTranscriptFound, 
    VideoUnavailable, 
    RequestBlocked, 
    AgeRestricted, 
    VideoUnplayable
)

from api.config import Config

# Evomi proxy config does not require SSL CA patching or special logic

def fetch_transcript(video_id: str, timeout_limit: int = 30) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch transcript using the YouTube Transcript API with proper error handling
    and fallbacks.
    
    Args:
        video_id: YouTube video ID
        timeout_limit: Maximum time in seconds to spend fetching the transcript
        
    Returns:
        List of transcript entries or None if failed
    """
    start_time = time.time()
    
    # Function to check if we still have time
    def time_left() -> bool:
        """Check if we still have time to continue operations"""
        elapsed = time.time() - start_time
        return elapsed < timeout_limit
    
    print(f"Fetching transcript for {video_id}, timeout limit: {timeout_limit}s")
    
    # Try with proxy first, then without
    attempts = [
        ("with proxy", True),
        ("without proxy", False)
    ]
    
    for attempt_name, use_proxy in attempts:
        if not time_left():
            print(f"Time limit reached during {attempt_name} attempt")
            break
            
        print(f"Attempting to fetch transcript {attempt_name}")
        try:
            transcript_list = None
            if use_proxy and Config.get_proxy_dict():
                proxy_config = Config.get_proxy_dict()
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "*/*",
                }
                proxies = proxy_config
                url = f"https://www.youtube.com/watch?v={video_id}"
                from requests.exceptions import ChunkedEncodingError
                for attempt in range(3):
                    try:
                        resp = requests.get(url, headers=headers, proxies=proxies, timeout=30, stream=False)
                        if resp.status_code == 200 and resp.content:
                            transcript_list = YouTubeTranscriptApi.get_transcript(
                                video_id,
                                proxies=proxy_config,
                                languages=Config.TRANSCRIPT_LANGUAGES
                            )
                            break
                        else:
                            print(f"Proxy request failed: status={resp.status_code}, len={len(resp.content)}")
                    except ChunkedEncodingError as e:
                        print(f"Attempt {attempt+1}: ChunkedEncodingError, retrying...")
                        time.sleep(2)
            else:
                transcript_list = YouTubeTranscriptApi.get_transcript(
                    video_id,
                    languages=Config.TRANSCRIPT_LANGUAGES
                )
            
            if transcript_list:
                print(f"Successfully fetched transcript {attempt_name} for {video_id}")
                return transcript_list
                
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
            print(f"Transcript not available for {video_id}: {type(e).__name__}: {e}")
            # These are permanent failures, no retry needed
            return None
            
        except (RequestBlocked, AgeRestricted, VideoUnplayable) as e:
            print(f"Access error for {video_id}: {type(e).__name__}: {e}")
            # Continue to the next attempt
            continue
            
        except Exception as e:
            print(f"Unexpected error {attempt_name}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            # Continue to the next attempt
            continue

    # If we get here, try the httpx-based approach as a last resort
    if time_left():
        try:
            print("Trying httpx-based transcript fetching as fallback")
            proxy_dict = Config.get_proxy_dict() if Config.get_proxy_dict() else None
            transcript_data = fetch_transcript_with_requests(video_id, proxy_dict=proxy_dict)
            return transcript_data
        except Exception as e:
            print(f"httpx-based fallback also failed: {e}")
    
    print(f"Failed to fetch transcript for {video_id} after all attempts")
    return None


def fetch_transcript_with_requests(video_id: str, proxy_dict: Optional[Dict[str, str]] = None, timeout: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch YouTube transcript using httpx.AsyncClient with proxy support (async replacement for requests)
    """
    async def _fetch():
        print(f"Attempting to fetch transcript for {video_id} using httpx with proxies: {bool(proxy_dict)}")
        proxies = proxy_dict if proxy_dict else None
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        async with httpx.AsyncClient(proxies=proxies, timeout=timeout) as client:
            print(f"Fetching video page with proxies: {bool(proxy_dict)}")
            response = await client.get(video_url)
            response.raise_for_status()
            html = response.text
            start_marker = 'ytInitialPlayerResponse = '
            end_marker = '};'
            start_idx = html.find(start_marker)
            if start_idx == -1:
                raise Exception("Could not find player response in page")
            start_idx += len(start_marker)
            end_idx = html.find(end_marker, start_idx) + 1
            player_response_json = html[start_idx:end_idx]
            player_response = json.loads(player_response_json)
            captions_data = player_response.get('captions', {}).get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
            if not captions_data:
                raise Exception("No captions found for this video")
            caption_url = None
            for track in captions_data:
                if track.get('languageCode') in Config.TRANSCRIPT_LANGUAGES:
                    caption_url = track.get('baseUrl')
                    break
            if not caption_url and captions_data:
                caption_url = captions_data[0].get('baseUrl')
            if not caption_url:
                raise Exception("No valid caption URL found")
            caption_url += "&fmt=json3"
            print(f"Fetching captions from {caption_url}")
            captions_response = await client.get(caption_url)
            captions_response.raise_for_status()
            captions_data = captions_response.json()
            transcript = []
            for event in captions_data.get('events', []):
                if 'segs' not in event or 'tStartMs' not in event:
                    continue
                text = ''.join(seg.get('utf8', '') for seg in event.get('segs', []))
                if not text.strip():
                    continue
                transcript.append({
                    'text': text.strip(),
                    'start': event.get('tStartMs') / 1000,
                    'duration': event.get('dDurationMs', 0) / 1000
                })
            print(f"Successfully fetched transcript with {len(transcript)} entries using httpx")
            return transcript
    try:
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(_fetch())
        else:
            return asyncio.run(_fetch())
    except Exception as e:
        print(f"Error fetching transcript with httpx: {e}")
        traceback.print_exc()
        raise Exception(f"Failed to fetch transcript with httpx: {str(e)}")
