"""
YouTube transcript fetching services
"""
import json
import time
import traceback
import requests
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
            if use_proxy and Config.get_webshare_proxy_config():
                proxy_config = Config.get_webshare_proxy_config()
                transcript_list = YouTubeTranscriptApi.get_transcript(
                    video_id,
                    proxies=proxy_config,
                    languages=Config.TRANSCRIPT_LANGUAGES
                )
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

    # If we get here, try the requests-based approach as a last resort
    if time_left():
        try:
            print("Trying requests-based transcript fetching as fallback")
            proxy_dict = Config.get_proxy_dict() if Config.get_proxy_dict() else None
            transcript_data = fetch_transcript_with_requests(video_id, proxy_dict=proxy_dict)
            return transcript_data
        except Exception as e:
            print(f"Requests-based fallback also failed: {e}")
    
    print(f"Failed to fetch transcript for {video_id} after all attempts")
    return None


def fetch_transcript_with_requests(video_id: str, proxy_dict: Optional[Dict[str, str]] = None, timeout: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch YouTube transcript using requests library with proxy support
    
    Args:
        video_id: YouTube video ID
        proxy_dict: Proxy configuration for requests
        timeout: Request timeout in seconds
        
    Returns:
        List of transcript entries or raises an exception if failed
    """
    print(f"Attempting to fetch transcript for {video_id} using requests with proxies: {bool(proxy_dict)}")
    
    # Create a session for this request
    session = requests.Session()
    if proxy_dict:
        session.proxies.update(proxy_dict)
    
    # First get the video page to extract available captions
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        print(f"Fetching video page with proxies: {bool(proxy_dict)}")
        response = session.get(video_url, timeout=timeout)
        response.raise_for_status()
        
        # Find the captions URL in the page
        html = response.text
        
        # Extract ytInitialPlayerResponse JSON
        start_marker = 'ytInitialPlayerResponse = '
        end_marker = '};'
        
        start_idx = html.find(start_marker)
        if start_idx == -1:
            raise Exception("Could not find player response in page")
        
        start_idx += len(start_marker)
        end_idx = html.find(end_marker, start_idx) + 1
        
        player_response_json = html[start_idx:end_idx]
        player_response = json.loads(player_response_json)
        
        # Find caption tracks
        captions_data = player_response.get('captions', {}).get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
        
        if not captions_data:
            raise Exception("No captions found for this video")
        
        # Try to find English captions
        caption_url = None
        for track in captions_data:
            if track.get('languageCode') in Config.TRANSCRIPT_LANGUAGES:
                caption_url = track.get('baseUrl')
                break
        
        # If no English captions, use the first available
        if not caption_url and captions_data:
            caption_url = captions_data[0].get('baseUrl')
        
        if not caption_url:
            raise Exception("No valid caption URL found")
        
        # Add format parameter for JSON
        caption_url += "&fmt=json3"
        
        # Fetch the captions
        print(f"Fetching captions from {caption_url}")
        captions_response = session.get(caption_url, timeout=timeout)
        captions_response.raise_for_status()
        
        captions_data = captions_response.json()
        
        # Process the transcript
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
        
        print(f"Successfully fetched transcript with {len(transcript)} entries using requests")
        return transcript
        
    except Exception as e:
        print(f"Error fetching transcript with requests: {e}")
        traceback.print_exc()
        raise Exception(f"Failed to fetch transcript with requests: {str(e)}")
