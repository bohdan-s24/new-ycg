#!/usr/bin/env python3
"""
Test script to verify the pytubefix YouTube transcript implementation
"""
import sys
from pytubefix import YouTube
import traceback

def test_api():
    """Test the pytubefix API method"""
    print("Testing pytubefix API method...")
    try:
        video_id = "EngW7tLk6R8"  # Sample YouTube video ID
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Create YouTube object
        yt = YouTube(video_url)

        # Check if captions are available
        if not yt.captions:
            print("No captions available for this video")
            return False

        available_captions = list(yt.captions.keys())
        print("Available captions:")
        for lang_code in available_captions:
            caption = yt.captions[lang_code]
            print(f"  - {lang_code} ({caption.name})")

        print(f"Found {len(available_captions)} available captions")

        # Try to get a caption
        if available_captions:
            # Get the first available caption
            first_lang = available_captions[0]
            caption = yt.captions[first_lang]

            # Generate SRT captions
            srt_captions = caption.generate_srt_captions()

            # Count entries by splitting SRT content
            blocks = srt_captions.strip().split('\n\n')
            entry_count = len([block for block in blocks if block.strip()])

            print(f"✓ Successfully retrieved captions in {first_lang} with {entry_count} entries")

            if blocks:
                print(f"First block: {blocks[0][:200]}...")

            # Try to generate text captions as well
            try:
                txt_captions = caption.generate_txt_captions()
                lines = txt_captions.strip().split('\n')
                print(f"✓ Successfully generated text captions with {len(lines)} lines")
                if lines:
                    print(f"First line: {lines[0]}")
            except Exception as e:
                print(f"Text caption generation failed: {e}")
        else:
            print("No captions available for this video")

        return True
    except Exception as e:
        print(f"✗ API test failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"Testing pytubefix YouTube transcript implementation")
    print(f"Python version: {sys.version}")

    result = test_api()

    if result:
        print("\n✓ Test passed!")
        sys.exit(0)
    else:
        print("\n✗ Test failed!")
        sys.exit(1)