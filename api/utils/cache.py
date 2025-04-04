"""
Simple in-memory cache implementation for chapter data
"""
from typing import Dict, Any, Optional

# Global cache for chapters
CHAPTERS_CACHE: Dict[str, Any] = {}

def get_from_cache(video_id: str) -> Optional[Any]:
    """
    Get cached chapter data for a video ID
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Cached data or None if not found
    """
    return CHAPTERS_CACHE.get(video_id)

def add_to_cache(video_id: str, data: Any) -> None:
    """
    Add chapter data to cache
    
    Args:
        video_id: YouTube video ID
        data: Chapter data to cache
    """
    CHAPTERS_CACHE[video_id] = data
