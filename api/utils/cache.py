"""
Simple in-memory cache implementation for chapter data
"""
from typing import Dict, Any, Optional

# Global cache for chapters
CHAPTERS_CACHE: Dict[str, Dict[str, str]] = {}

def get_from_cache(video_id: str) -> Optional[Dict[str, str]]:
    """
    Get cached data for a video ID. Returns a dict with keys 'chapters' and 'transcript'.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Cached data or None if not found
    """
    return CHAPTERS_CACHE.get(video_id)

def add_to_cache(video_id: str, chapters: str, transcript: str) -> None:
    """
    Add chapters and the transcript (not concatenated prompt) to cache for a video ID.
    """
    CHAPTERS_CACHE[video_id] = {
        'chapters': chapters,
        'transcript': transcript
    }
