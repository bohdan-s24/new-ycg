#!/usr/bin/env python3
"""
Test script to verify the YouTube Transcript API implementation
"""
import sys
from youtube_transcript_api import YouTubeTranscriptApi

def test_api():
    """Test the API method"""
    print("Testing API method...")
    try:
        video_id = "EngW7tLk6R8"  # Sample YouTube video ID
        
        # First try to get available transcript languages
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        print("Available transcripts:")
        for transcript in transcript_list:
            print(f"  - {transcript.language_code} ({transcript.language})")
        
        # Try to get a Russian transcript
        transcript = transcript_list.find_transcript(['ru'])
        transcript_data = transcript.fetch()
        print(f"✓ Successfully retrieved transcript with {len(transcript_data)} entries")
        print(f"First entry: {transcript_data[0]}")
        
        # Try to translate to English
        try:
            english_transcript = transcript.translate('en')
            english_data = english_transcript.fetch()
            print(f"✓ Successfully translated transcript to English with {len(english_data)} entries")
            print(f"First entry: {english_data[0]}")
        except Exception as e:
            print(f"Translation failed: {e}")
        
        return True
    except Exception as e:
        print(f"✗ API test failed: {e}")
        return False

if __name__ == "__main__":
    print(f"Testing YouTube Transcript API implementation")
    print(f"Python version: {sys.version}")
    
    result = test_api()
    
    if result:
        print("\n✓ Test passed!")
        sys.exit(0)
    else:
        print("\n✗ Test failed!")
        sys.exit(1) 