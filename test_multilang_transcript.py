#!/usr/bin/env python3
"""
Test script to verify the multi-language transcript fetching using pytubefix
"""
import sys
import json
from pytubefix import YouTube
import traceback
from api.config import Config
from api.services.youtube import fetch_transcript

def test_list_available_transcripts(video_id):
    """Test listing available transcripts for a video using pytubefix"""
    print(f"\n=== Testing available transcripts for video {video_id} ===")
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        yt = YouTube(video_url)

        if not yt.captions:
            print("No captions available for this video")
            return []

        available_languages = list(yt.captions.keys())

        print("Available captions:")
        for lang_code in available_languages:
            caption = yt.captions[lang_code]
            print(f"  - {lang_code} ({caption.name})")

        print(f"Total available captions: {len(available_languages)}")
        return available_languages
    except Exception as e:
        print(f"Error listing captions: {e}")
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
    """Test fetching transcript with specific languages using pytubefix"""
    print(f"\n=== Testing transcript fetching with specific languages {languages} ===")
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        yt = YouTube(video_url)

        if not yt.captions:
            print("No captions available for this video")
            return False

        # Try to find a caption in one of the specified languages
        caption = None
        selected_lang = None

        for lang in languages:
            if lang in yt.captions:
                caption = yt.captions[lang]
                selected_lang = lang
                break
            # Try auto-generated format
            auto_lang = f"a.{lang}"
            if auto_lang in yt.captions:
                caption = yt.captions[auto_lang]
                selected_lang = auto_lang
                break

        if not caption:
            print(f"No captions found for languages: {languages}")
            return False

        print(f"Using caption: {selected_lang}")
        srt_captions = caption.generate_srt_captions()

        # Count entries by splitting SRT content
        blocks = srt_captions.strip().split('\n\n')
        entry_count = len([block for block in blocks if block.strip()])

        print(f"Successfully fetched transcript with {entry_count} entries")
        if blocks:
            print(f"First block: {blocks[0][:100]}...")
            print(f"Last block: {blocks[-1][:100]}...")
        return True

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
