"""
Simple in-memory cache implementation for chapter data
"""
from typing import Dict, Any, Optional

# Global cache for chapters
CHAPTERS_CACHE: Dict[str, Dict[str, str]] = {}

def get_from_cache(video_id: str) -> Optional[Dict[str, str]]:
    """
    Get cached data for a video ID. Returns a dict with keys 'chapters' and 'formatted_transcript'.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Cached data or None if not found
    """
    return CHAPTERS_CACHE.get(video_id)

def add_to_cache(video_id: str, chapters: str, formatted_transcript: str) -> None:
    """
    Add chapters and formatted transcript to cache for a video ID.
    
    Args:
        video_id: YouTube video ID
        chapters: Chapters data to cache
        formatted_transcript: Formatted transcript data to cache
    """
    CHAPTERS_CACHE[video_id] = {
        'chapters': chapters,
        'formatted_transcript': formatted_transcript
    }
