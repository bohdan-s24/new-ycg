"""
Test the OpenAI service
"""
import asyncio
from api.services.openai_service import create_chapter_prompt, create_final_reminder, generate_chapters_with_openai

def test_create_chapter_prompt():
    """Test the create_chapter_prompt function"""
    # Test with a short video
    prompt_short = create_chapter_prompt(10)
    assert "MM:SS" in prompt_short
    assert "You are an expert YouTube strategist" in prompt_short
    assert "GOAL" in prompt_short
    assert "FORMAT" in prompt_short
    assert "RULES" in prompt_short
    assert "HOW TO DETECT TRANSITIONS" in prompt_short
    assert "CHAPTER CHAIN STRATEGY" in prompt_short

    # Test with a long video
    prompt_long = create_chapter_prompt(70)
    assert "HH:MM:SS" in prompt_long

def test_create_final_reminder():
    """Test the create_final_reminder function"""
    # Test with a short video
    reminder_short = create_final_reminder(10)
    assert "MM:SS" in reminder_short
    assert "FINAL CHECKLIST" in reminder_short
    assert "Start at 00:00" in reminder_short
    assert "End with a conclusion" in reminder_short
    assert "Last chapter feels like a climax" in reminder_short

    # Test with a long video
    reminder_long = create_final_reminder(70)
    assert "HH:MM:SS" in reminder_long

def test_combined_input_format():
    """Test the combined input format with transcript and final reminder"""
    # Mock transcript
    formatted_transcript = "00:00 - Welcome to this video\n01:30 - First topic\n03:45 - Second topic"

    # Create final reminder
    final_reminder = create_final_reminder(10)

    # Create combined input
    combined_input = f"{formatted_transcript}\n\n---\n\n{final_reminder}"

    # Verify structure
    assert formatted_transcript in combined_input
    assert "---" in combined_input
    assert final_reminder in combined_input

if __name__ == "__main__":
    test_create_chapter_prompt()
    test_create_final_reminder()
    test_combined_input_format()
    print("All tests passed!")
