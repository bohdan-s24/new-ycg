"""
OpenAI API integration service
"""
import traceback
import os
from typing import Dict, Any, Optional, List
from openai import OpenAI

from api.config import Config


# Initialize OpenAI client
openai_client = None
if Config.OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        print("OpenAI client configured")
    except Exception as e:
        print(f"ERROR configuring OpenAI client: {e}")
        traceback.print_exc()
else:
    print("Warning: OpenAI API key not found in environment variables")


def create_chapter_prompt(video_duration_minutes: float) -> str:
    """
    Create a flexible prompt for generating chapter titles based on natural content transitions.

    Args:
        video_duration_minutes: Duration of the video in minutes

    Returns:
        System prompt for the OpenAI API
    """
    # Format duration for display
    if video_duration_minutes >= 60:
        hours, minutes = divmod(int(video_duration_minutes), 60)
        duration_display = f"{hours} hour{'s' if hours > 1 else ''} and {minutes} minute{'s' if minutes != 1 else ''}"
        end_timestamp = f"{hours}:{minutes:02d}:00"
        timestamp_format = "HH:MM:SS"
    else:
        duration_display = f"{int(video_duration_minutes)} minute{'s' if video_duration_minutes != 1 else ''}"
        end_timestamp = f"{int(video_duration_minutes)}:00"
        timestamp_format = "MM:SS"

    system_prompt = (
        f"You are an expert in YouTube content optimization and copywriting.\n\n"

        "Your task is to generate short, punchy, and emotionally compelling chapter titles that maximize watch time and engagement. "
        "Think like a top-tier content strategist who knows how to make viewers stay longer, click, and engage. "
        "Create titles that feel urgent, powerful, and engaging—like something viewers can't ignore.\n\n"

        "### **Critical Rules:**\n"
        "1. **Natural Content Structure:** Understand the video's inherent structure and identify key moments paying attention to ALL natural transitions in the content. \n"
        "2. **Complete Coverage:** First chapter MUST start at 00:00 and chapters must cover the entire video to its end.\n"
        "3. **Accurate Timestamps:** Every timestamp MUST correspond to actual topic transitions in the transcript. NO arbitrary timestamps.\n"
        "4. **Special Attention to Intro/Conclusion:** Always create separate chapters for introduction and conclusion sections, even if they're brief.\n"
        "5. **Title Requirements:** Each title should be aproximatly 30-50 characters, maximum limit is 80 characters, crafted in a clickbait-style tone with emotional triggers.\n"
        "6. **Chapter Length Guidance:** Typically aim for chapters of 2-6 minutes in length for optimal viewer experience, but adjust based on content. Brief intros/conclusions can be shorter, complex topics can be longer.\n"
        "7. **Balanced distribution:** Ensure the chapters are distributed evenly across the entire video duration, not just clustered at the beginning.\n"
        f"8. **Output Format:** Strictly follow '{timestamp_format} Chapter Title' with each chapter on a new line.\n\n"

        "### **Content Transition Indicators:**\n"
        "Pay special attention to these transition signals in the transcript:\n"
        "- Numerical indicators: 'first', 'second', 'third', 'step 1', 'tip #2', etc.\n"
        "- Transition phrases: 'now', 'next', 'let's talk about', 'moving on to', 'another thing'\n"
        "- Topic shifts: 'speaking of', 'when it comes to', 'as for', 'regarding'\n"
        "- Concluding phrases: 'in conclusion', 'to summarize', 'finally', 'wrapping up'\n"
        "- Introduction markers: 'today we'll discuss', 'in this video', 'I want to share'\n"
        "- Audio cues mentioned in transcript: [music], [pause], [transition]\n\n"

        "### **Step-by-Step Process:**\n"
        "1. **Comprehensive Transcript Analysis:**\n"
        "   - Analyze the ENTIRE transcript first to understand the video's structure, general context, and the overall narrative.\n"
        "   - Identify if it's a tutorial, list-based content, story, interview, or other format.\n"
        "   - Recognize the natural segments that make up the content.\n\n"

        "2. **Identify ALL Key moments:**\n"
        "   - Find EVERY significant content transitions, insights, and 'aha' moments throughout the transcript.\n"
        "   - For list-based content (ideas, tools, methods, tips, etc), identify each list item as a potential chapter.\n"
        "   - Always mark the introduction and conclusion, regardless of length.\n\n"

        "3. **Create Compelling Titles:**\n"
        "   - Craft  catchy, clickbait-style titles that accurately represent each section.\n"
        "   - Use casual tone of voice and emotional triggers such as curiosity, surprise, excitement, or controversy.\n"
        "   - For list items, incorporate numbers or key terms from the transcript.\n"
        "   - Make introduction and conclusion titles particularly compelling and intriguing to motivate user watch untill the end. \n\n"

        "4. **Verify Timestamps and Structure:**\n"
        "   - Ensure every timestamp corresponds to an actual content transition.\n"
        "   - Verify that timestamps flow logically and cover the entire video.\n"
        "   - Copy the timestamp **exactly as it appears in the transcript**. Do not alter, round, or approximate any digit.\n"
        "   - Avoid patterns like regular 3-minute intervals.\n"
        "   - Check that no chapter is missing and no significant content shift is overlooked.\n\n"
    )

    # Final reminder
    system_prompt += (
        "### **FINAL OUTPUT FORMAT:**\n"
        "- Include ALL identified content transitions as chapters\n"
        f"- Each on a new line in the format: '{timestamp_format} Chapter Title'\n"
        "- NO additional commentary or explanation\n\n"

        "### **QUALITY CHECK:**\n"
        "- ✓ Introduction chapter starts at 00:00\n"
        "- ✓ Conclusion chapter near the end of the video\n"
        "- ✓ ALL major content transitions identified\n"
        "- ✓ Timestamps correspond to actual topic changes in transcript\n"
        "- ✓ NO arbitrary or pattern-based timestamps\n"
        "- ✓ ALL chapters have engaging titles under 80 characters\n"
    )

    return system_prompt


def generate_chapters_with_openai(system_prompt: str, video_id: str, formatted_transcript: str) -> Optional[str]:
    """
    Generate chapters using OpenAI with better timestamp distribution.

    Args:
        system_prompt: System prompt for the OpenAI API
        video_id: YouTube video ID
        formatted_transcript: Formatted transcript text

    Returns:
        Generated chapters or None if all models fail
    """
    if not openai_client:
        print("ERROR: OpenAI client not configured")
        return None

    print(f"Generating chapters for video: {video_id}")
    print(f"Transcript length: {len(formatted_transcript)} characters")

    # Extract video duration from the last transcript entry
    transcript_lines = formatted_transcript.split('\n')
    video_duration_minutes = None

    if transcript_lines:
        try:
            # Find the last line with a timestamp
            for line in reversed(transcript_lines):
                if ' - ' in line:  # Look for the timestamp separator
                    parts = line.split(' - ', 1)
                    if len(parts) == 2:
                        timestamp_str = parts[0].strip()
                        # Handle HH:MM:SS or MM:SS formats
                        if timestamp_str.count(':') == 2:  # HH:MM:SS
                            h, m, s = map(int, timestamp_str.split(':'))
                            last_timestamp_seconds = h * 3600 + m * 60 + s
                        else:  # MM:SS
                            m, s = map(int, timestamp_str.split(':'))
                            last_timestamp_seconds = m * 60 + s

                        video_duration_minutes = last_timestamp_seconds / 60
                        print(f"Estimated video duration from transcript: {video_duration_minutes:.2f} minutes")
                        break

            if video_duration_minutes is None:
                # Fallback: use a default duration if we couldn't extract it
                video_duration_minutes = 10.0  # Default to 10 minutes
                print(f"Using default video duration: {video_duration_minutes:.2f} minutes")
        except Exception as e:
            print(f"Could not extract duration from transcript: {e}")
            # Fallback to a default duration
            video_duration_minutes = 10.0
            print(f"Using default video duration after error: {video_duration_minutes:.2f} minutes")

    # Prepare the user content prompt
    user_content = f"Generate chapters for this video transcript:\n\n{formatted_transcript}"

    # Try each model in order of preference
    for model in Config.OPENAI_MODELS:
        try:
            print(f"Trying to generate chapters with {model}")

            # Make sure we have a valid system prompt
            if system_prompt is None:
                # Create a default system prompt if none was provided
                system_prompt = create_chapter_prompt(video_duration_minutes or 10.0)  # Default to 10 minutes if unknown
                print(f"Created default system prompt for video duration: {video_duration_minutes or 10.0} minutes")

            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.7,  # Slightly lower temperature for more consistent results
                max_tokens=2000
            )

            chapters = response.choices[0].message.content

            # Validate chapters format
            chapter_lines = chapters.strip().split("\n")
            if len(chapter_lines) < 3:
                print(f"WARNING: Generated only {len(chapter_lines)} chapters, which is too few")
                continue

            # Check if first chapter starts at 00:00
            if not chapter_lines[0].startswith("00:00"):
                print("WARNING: First chapter doesn't start at 00:00, trying another model")
                continue

            # All basic checks passed
            print(f"Successfully generated {len(chapter_lines)} chapters")
            return chapters

        except Exception as e:
            print(f"Error generating chapters with {model}: {type(e).__name__}")
            print(f"Error details: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    print("All OpenAI models failed to generate chapters")
    return None
