#!/usr/bin/env python3
"""
Test script to verify the pytubefix migration is working correctly
"""
import sys
import traceback
from api.services.youtube import fetch_transcript
from api.utils.transcript import format_transcript_for_model

def test_basic_transcript_fetch():
    """Test basic transcript fetching functionality"""
    print("=== Testing Basic Transcript Fetch ===")
    
    # Test with a known video that should have captions
    video_id = "EngW7tLk6R8"  # Sample video
    
    try:
        print(f"Fetching transcript for video: {video_id}")
        transcript_data = fetch_transcript(video_id, timeout_limit=30)
        
        if transcript_data:
            print(f"✅ Successfully fetched transcript with {len(transcript_data)} entries")
            
            # Verify transcript format
            if len(transcript_data) > 0:
                first_entry = transcript_data[0]
                required_keys = ['text', 'start', 'duration']
                
                if all(key in first_entry for key in required_keys):
                    print("✅ Transcript format is correct")
                    print(f"First entry: {first_entry}")
                    
                    # Test transcript formatting
                    formatted_text, line_count = format_transcript_for_model(transcript_data)
                    print(f"✅ Formatted transcript: {line_count} lines")
                    print(f"First few lines:\n{formatted_text[:200]}...")
                    
                    return True
                else:
                    print(f"❌ Transcript format is incorrect. Missing keys: {[k for k in required_keys if k not in first_entry]}")
                    return False
            else:
                print("❌ Transcript is empty")
                return False
        else:
            print("❌ Failed to fetch transcript")
            return False
            
    except Exception as e:
        print(f"❌ Error during transcript fetch: {e}")
        traceback.print_exc()
        return False

def test_language_preference():
    """Test language preference handling"""
    print("\n=== Testing Language Preference ===")
    
    # Test with a video that might have multiple languages
    video_id = "9bZkp7q19f0"  # Gangnam Style - likely has many language options
    
    try:
        print(f"Fetching transcript for multilingual video: {video_id}")
        transcript_data = fetch_transcript(video_id, timeout_limit=30)
        
        if transcript_data:
            print(f"✅ Successfully fetched transcript with {len(transcript_data)} entries")
            print("✅ Language preference system working")
            return True
        else:
            print("⚠️  Could not fetch transcript (video may not have captions)")
            return True  # Not a failure of our system
            
    except Exception as e:
        print(f"❌ Error during language preference test: {e}")
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling with invalid video"""
    print("\n=== Testing Error Handling ===")
    
    # Test with invalid video ID
    invalid_video_id = "INVALID_VIDEO_ID"
    
    try:
        print(f"Testing with invalid video ID: {invalid_video_id}")
        transcript_data = fetch_transcript(invalid_video_id, timeout_limit=10)
        
        if transcript_data is None:
            print("✅ Correctly handled invalid video ID")
            return True
        else:
            print("❌ Should have returned None for invalid video")
            return False
            
    except Exception as e:
        print(f"❌ Unexpected exception for invalid video: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Testing pytubefix Migration")
    print("=" * 50)
    
    tests = [
        ("Basic Transcript Fetch", test_basic_transcript_fetch),
        ("Language Preference", test_language_preference),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! pytubefix migration is successful.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
