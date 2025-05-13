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
    # Check if video is longer than 60 minutes
    last_entry = transcript_list[-1] if transcript_list else None
    video_duration_seconds = last_entry['start'] + last_entry['duration'] if last_entry else 0
    is_long_video = video_duration_seconds > 3600  # 60 minutes = 3600 seconds

    lines = []
    for entry in transcript_list:
        start_seconds = entry['start']

        if is_long_video and start_seconds >= 3600:
            # Format as HH:MM:SS for timestamps over 60 minutes in long videos
            hours = int(start_seconds // 3600)
            minutes = int((start_seconds % 3600) // 60)
            seconds = int(start_seconds % 60)
            timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            # Format as MM:SS for shorter videos or timestamps under 60 minutes
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
