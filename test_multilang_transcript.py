#!/usr/bin/env python3
"""
Test script to verify the multi-language transcript fetching
"""
import sys
import json
from youtube_transcript_api import YouTubeTranscriptApi
import traceback
from api.config import Config
from api.services.youtube import fetch_transcript

def test_list_available_transcripts(video_id):
    """Test listing available transcripts for a video"""
    print(f"\n=== Testing available transcripts for video {video_id} ===")
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        print("Available transcripts:")
        transcript_count = 0
        available_languages = []
        
        # Collect available transcripts
        for transcript in transcript_list:
            transcript_count += 1
            available_languages.append(transcript.language_code)
            print(f"  - {transcript.language_code} ({transcript.language}), Auto-generated: {transcript.is_generated}")
        
        print(f"Total available transcripts: {transcript_count}")
        return available_languages
    except Exception as e:
        print(f"Error listing transcripts: {e}")
        traceback.print_exc()
        return []

def test_fetch_transcript(video_id):
    """Test fetching transcript with our service"""
    print(f"\n=== Testing transcript fetching for video {video_id} ===")
    try:
        transcript_data = fetch_transcript(video_id)
        if transcript_data:
            print(f"Successfully fetched transcript with {len(transcript_data)} entries")
            print(f"First entry: {transcript_data[0]}")
            print(f"Last entry: {transcript_data[-1]}")
            return True
        else:
            print("Failed to fetch transcript")
            return False
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        traceback.print_exc()
        return False

def test_fetch_with_specific_languages(video_id, languages):
    """Test fetching transcript with specific languages"""
    print(f"\n=== Testing transcript fetching with specific languages {languages} ===")
    try:
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        if transcript_data:
            print(f"Successfully fetched transcript with {len(transcript_data)} entries")
            print(f"First entry: {transcript_data[0]}")
            print(f"Last entry: {transcript_data[-1]}")
            return True
        else:
            print("Failed to fetch transcript")
            return False
    except Exception as e:
        print(f"Error fetching transcript with specific languages: {e}")
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    # Test videos with different language transcripts
    # You can replace these with videos known to have specific language transcripts
    test_videos = [
        "EngW7tLk6R8",  # Sample video (English)
        "9bZkp7q19f0",  # Gangnam Style (Korean with many translations)
        "Ks-_Mh1QhMc",  # TED Talk (likely to have multiple languages)
    ]
    
    print("=== YouTube Multi-Language Transcript Test ===")
    print(f"Configured languages: {Config.TRANSCRIPT_LANGUAGES}")
    
    for video_id in test_videos:
        print(f"\n\n=== Testing video ID: {video_id} ===")
        
        # List available transcripts
        available_languages = test_list_available_transcripts(video_id)
        
        # Test our transcript fetching service
        test_fetch_transcript(video_id)
        
        # If we have multiple languages available, test with specific ones
        if len(available_languages) > 1:
            # Test with the first non-English language if available
            non_english = [lang for lang in available_languages if not lang.startswith('en')]
            if non_english:
                test_fetch_with_specific_languages(video_id, [non_english[0]])
                # Test with English fallback
                test_fetch_with_specific_languages(video_id, [non_english[0], 'en'])

if __name__ == "__main__":
    main()
