"""
Data models and schemas for the API
"""
from typing import Dict, List, Any, Optional

class ChapterRequest:
    """Request model for chapter generation"""
    def __init__(self, video_id: str):
        self.video_id = video_id
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'ChapterRequest':
        """Create instance from JSON data"""
        return cls(video_id=data.get('videoId', ''))

class ChapterResponse:
    """Response model for chapter generation"""
    def __init__(self, 
                 success: bool, 
                 video_id: str, 
                 chapters: Optional[str] = None, 
                 from_cache: bool = False, 
                 error: Optional[str] = None):
        self.success = success
        self.video_id = video_id
        self.chapters = chapters
        self.from_cache = from_cache
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            'success': self.success,
            'videoId': self.video_id
        }
        
        if self.chapters:
            result['chapters'] = self.chapters
        
        if self.from_cache:
            result['fromCache'] = True
            
        if self.error:
            result['error'] = self.error
            
        return result
