#!/usr/bin/env python3
"""
Test script to verify the YouTube Transcript API implementation
"""
import sys
from youtube_transcript_api import YouTubeTranscriptApi
import traceback

def test_api():
    """Test the API method"""
    print("Testing API method...")
    try:
        video_id = "EngW7tLk6R8"  # Sample YouTube video ID
        
        # First try to get available transcript languages
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        print("Available transcripts:")
        transcript_count = 0
        available_transcripts = []
        
        # Collect available transcripts
        for transcript in transcript_list:
            transcript_count += 1
            available_transcripts.append(transcript)
            print(f"  - {transcript.language_code} ({transcript.language}), Auto-generated: {transcript.is_generated}")
        
        print(f"Found {transcript_count} available transcripts")
        
        # Try to get a transcript
        if transcript_count > 0:
            # Get the first available transcript
            transcript = available_transcripts[0]
            transcript_data = transcript.fetch()
            print(f"✓ Successfully retrieved transcript in {transcript.language} with {len(transcript_data)} entries")
            first_entry = transcript_data[0]
            print(f"First entry: {first_entry}")
            
            # Try to translate to English
            try:
                print(f"Translating from {transcript.language_code} to English...")
                english_transcript = transcript.translate('en')
                english_data = english_transcript.fetch()
                print(f"✓ Successfully translated transcript to English with {len(english_data)} entries")
                print(f"First entry: {english_data[0]}")
            except Exception as e:
                print(f"Translation failed: {e}")
        else:
            print("No transcripts available for this video")
        
        return True
    except Exception as e:
        print(f"✗ API test failed: {e}")
        traceback.print_exc()
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