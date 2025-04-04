"""
Transcript formatting utilities
"""
from typing import List, Dict, Any, Tuple


def format_transcript_for_model(transcript_list: List[Dict[str, Any]]) -> Tuple[str, int]:
    """
    Format transcript for processing - using full transcript since we have large context windows
    
    Args:
        transcript_list: List of transcript entries with text, start time, and duration
        
    Returns:
        Tuple of (formatted transcript string, number of lines)
    """
    lines = []
    for entry in transcript_list:
        start_seconds = entry['start']
        minutes = int(start_seconds // 60)
        seconds = int(start_seconds % 60)
        timestamp = f"{minutes:02d}:{seconds:02d}"
        lines.append(f"{timestamp} - {entry['text']}")
    
    formatted_text = "\n".join(lines)
    return formatted_text, len(lines)


def format_transcript(transcript_list: List[Dict[str, Any]]) -> str:
    """
    Legacy function for compatibility - use format_transcript_for_model instead
    """
    formatted_text, _ = format_transcript_for_model(transcript_list)
    return formatted_text
