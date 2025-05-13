"""
OpenAI API integration service
"""
import traceback
import os
from typing import Dict, Any, Optional, List
from openai import OpenAI, AsyncOpenAI
import openai  # For logging
from api.config import Config


# Enable OpenAI debug logging for full request/response logs
openai.log = "debug"

# Initialize OpenAI clients
openai_client = None
async_openai_client = None

if Config.OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        async_openai_client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        print("OpenAI clients configured")
    except Exception as e:
        print(f"ERROR configuring OpenAI clients: {e}")
        traceback.print_exc()
else:
    print("Warning: OpenAI API key not found in environment variables")

if async_openai_client is None:
    print("CRITICAL: async_openai_client is still None after initialization!")

def create_chapter_prompt(video_duration_minutes: float) -> str:
    """
    Create a flexible prompt for generating chapter titles based on natural content transitions.

    Args:
        video_duration_minutes: Duration of the video in minutes

    Returns:
        System prompt for the OpenAI API
    """
    # Format timestamp based on video duration
    is_long_video = video_duration_minutes > 60
    # For long videos, we use a mixed format (MM:SS for <60min, HH:MM:SS for >60min)
    # But we'll use MM:SS as the base format in the prompt
    timestamp_format = "MM:SS"

    # Enhanced prompt with USP messaging about viewer retention
    system_prompt = (
        f"You are an expert YouTube strategist and copywriter.\n\n"

        "## GOAL\n"
        "Generate concise, compelling YouTube chapter titles that keep viewers watching until the very end.\n"
        "Each title should spark interest while summarizing what the viewer will learn or experience — balancing mystery with meaning.\n"
        "The final chapter should feel like a climax — a payoff for the viewer's attention.\n\n"

        "## CHAPTER COUNT - VERY IMPORTANT\n"
        "- For videos under 10 minutes: Create 5-7 chapters maximum\n"
        "- For videos 10-20 minutes: Create 7-10 chapters maximum\n"
        "- For videos over 20 minutes: Create 10-15 chapters maximum\n"
        "- Focus on MAJOR content transitions only - not every small topic change\n"
        "- Quality over quantity: Fewer, more meaningful chapters are better than many small ones\n\n"

        "## FORMAT\n"
        f"- Use only this format: `{'MM:SS or HH:MM:SS (depending on timestamp)' if is_long_video else timestamp_format} Chapter Title`\n"
        "- One chapter per line\n"
        "- No markdown, notes, or commentary\n\n"

        f"## TIMESTAMP FORMAT - VERY IMPORTANT\n"
        f"- For videos under 60 minutes: Use MM:SS format (e.g., 05:30)\n"
        f"- For videos over 60 minutes:\n"
        f"  * For timestamps under 60 minutes: Use MM:SS format (e.g., 05:30, 45:20)\n"
        f"  * For timestamps over 60 minutes: Use HH:MM:SS format (e.g., 01:05:30, 02:15:45)\n"
        f"- The first chapter MUST always start at 00:00 regardless of where the transcript starts\n"
        f"- For videos over 60 minutes, when you see timestamps like 60:48, 75:20 in the transcript, convert them to HH:MM:SS format (01:00:48, 01:15:20)\n\n"

        "## RULES\n"
        "1. Start at **00:00** with an engaging introduction.\n"
        "2. End with a compelling conclusion chapter.\n"
        "3. Use real transitions from the transcript — never invent timestamps.\n"
        "4. Chapters should follow natural flow (typically every 2–6 mins between key moments).\n"
        "5. Titles should be under 40 characters, ideally 20–30.\n"
        "6. Use casual, emotional, or intriguing phrasing without excessive clickbait.\n"
        "7. Prioritize MAJOR transitions only - be selective and strategic.\n"
        "8. Timestamp accuracy is crucial — no rounding or patterning.\n"
        "9. Keywords and emotion should reflect the transcript's voice.\n"
        "10. Each title should provoke curiosity while clearly hinting at the value or lesson in the chapter — avoid vague clickbait or generic summaries.\n\n"


        "### Follow the Step-by-Step Process:\n"
        "1. **Analyze the full transcript** to understand the general context, content type, and natural structure.\n"
        "2. **Determine appropriate chapter count** based on video length:\n"
        "   - Under 10 minutes: 5-7 chapters maximum\n"
        "   - 10-20 minutes: 7-10 chapters maximum\n"
        "   - Over 20 minutes: 10-15 chapters maximum\n"
        "3. **Identify only the MAJOR transitions** - be highly selective and focus on main topic changes.\n"
        "4. **Craft strong titles** with emotional triggers (curiosity, surprise, controversey etc.). In friendly tone of void\n"
        "5. **Verify timestamps**:\n"
        "   - Match transitions exactly — no rounding or regular intervals.\n"
        "   - Ensure timestamps are in ascending order and fully cover the video.\n"
        f"   - {'For videos over 60 minutes, ensure all timestamps are in HH:MM:SS format.' if is_long_video else ''}\n\n"
    )

    return system_prompt


def create_final_reminder(video_duration_minutes: float) -> str:
    """
    Create a final reminder to be appended after the transcript in the OpenAI request.

    Args:
        video_duration_minutes: Duration of the video in minutes

    Returns:
        Final reminder text for the OpenAI API
    """
    # Format timestamp based on video duration
    is_long_video = video_duration_minutes > 60
    # For long videos, we use a mixed format (MM:SS for <60min, HH:MM:SS for >60min)
    # But we'll use MM:SS as the base format in the prompt
    timestamp_format = "MM:SS"

    final_reminder = (
        "\n### 🔍 FINAL CHECKLIST - STRICTLY FOLLOW THESE GUIDELINES\n"
        f"- ✓ Chapters are formatted: `{'MM:SS or HH:MM:SS (depending on timestamp)' if is_long_video else timestamp_format} Chapter Title`\n"
        "- ✓ Start at 00:00 with an engaging introduction\n"
        "- ✓ End with a compelling conclusion chapter (emotional or narrative payoff)\n"
        "- ✓ Titles are under 40 characters (ideally 20–30)\n"
        "- ✓ Each title clearly communicates value **and** provokes curiosity\n"
        "- ✓ Use intrigue techniques (info gaps, open loops, surprise, provocation)\n"
        "- ✓ All timestamps must be exact — pulled directly from transcript\n"
        "- ✓ No fabricated, rounded, or evenly spaced timestamps\n"
        f"- ✓ {'For videos over 60 minutes: Use MM:SS format for timestamps under 60 minutes and HH:MM:SS format for timestamps over 60 minutes' if is_long_video else 'For videos under 60 minutes, use MM:SS format (e.g., 05:30)'}\n"
        "- ✓ No extra commentary, markdown, notes, or formatting outside the required structure"
    )

    return final_reminder


async def generate_chapters_with_openai(system_prompt: str, video_id: str, formatted_transcript: str, video_duration_minutes: float = 60, timeout: int = 30) -> Optional[str]:
    """
    Generate chapters using OpenAI with better timestamp distribution.

    Args:
        system_prompt: System prompt for the OpenAI API
        video_id: YouTube video ID
        formatted_transcript: Formatted transcript text
        video_duration_minutes: Duration of the video in minutes (used for final reminder)
        timeout: Timeout for the OpenAI API call in seconds

    Returns:
        Generated chapters or None if all models fail
    """
    if not async_openai_client:
        print("OpenAI async client not configured, cannot generate chapters")
        return None

    print(f"Generating chapters for {video_id}")

    # Create the final reminder using the provided video duration
    final_reminder = create_final_reminder(video_duration_minutes)

    # Model preference: gpt-4.1 as primary, gpt-4.1-mini as secondary
    models_to_try = [
        "gpt-4.1",
        "gpt-4.1-mini",
    ]

    for model in models_to_try:
        try:
            import time
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Trying model: {model}, timeout={timeout}s")

            # Prepare the input with transcript, system prompt repeat, and final reminder
            combined_input = f"{formatted_transcript}\n\n---\n\n{system_prompt}\n\n---\n\n{final_reminder}"

            print("[OPENAI-REQUEST] Parameters:", {
                "model": model,
                "input": combined_input[:100] + ("..." if len(combined_input) > 100 else ""),
                "instructions": system_prompt[:100] + ("..." if len(system_prompt) > 100 else ""),
                "temperature": 0.3,
                "max_output_tokens": 2048,
                "timeout": timeout
            })
            print("[OPENAI] About to call OpenAI API (AsyncOpenAI.responses.create)")
            start = time.time()
            try:
                # Use the updated signature with the new structure:
                response = await async_openai_client.responses.create(
                    model=model,
                    instructions=system_prompt,
                    input=combined_input,
                    temperature=0.3,
                    max_output_tokens=2048,
                    timeout=timeout
                )
                print("[OPENAI] OpenAI API call returned from AsyncOpenAI.responses.create")
            except openai.APITimeoutError:
                print(f"[OPENAI] OpenAI API: Timed out waiting for OpenAI API response for model {model}")
                continue
            except openai.APIStatusError as exc:
                print(f"[OPENAI] APIStatusError: {exc.status_code} {exc.response}")
                continue
            elapsed = time.time() - start
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Model {model} call succeeded in {elapsed:.2f}s")
            print(f"[OPENAI-RESPONSE] Raw response: {getattr(response, 'output_text', None)}")
            chapters = getattr(response, 'output_text', None)
            if not chapters:
                print("No output_text in response, trying another model")
                continue
            chapter_lines = chapters.splitlines()
            if not chapter_lines or len(chapter_lines) < 2:
                print("Not enough chapters, trying another model")
                continue

            # Check if the first chapter starts at 00:00
            if not chapter_lines[0].startswith("00:00"):
                print("WARNING: First chapter doesn't start at 00:00, fixing it")
                # Extract the title from the first chapter
                first_chapter_parts = chapter_lines[0].split(' ', 1)
                first_chapter_title = first_chapter_parts[1] if len(first_chapter_parts) > 1 else "Introduction"

                # Replace the first chapter with one that starts at 00:00
                chapter_lines[0] = f"00:00 {first_chapter_title}"
                chapters = "\n".join(chapter_lines)

            # For videos longer than 60 minutes, apply mixed format:
            # - MM:SS for timestamps under 60 minutes
            # - HH:MM:SS for timestamps over 60 minutes
            if video_duration_minutes > 60:
                fixed_chapter_lines = []
                for line in chapter_lines:
                    parts = line.split(' ', 1)
                    if len(parts) < 2:
                        fixed_chapter_lines.append(line)
                        continue

                    timestamp, title = parts

                    # Parse the timestamp to get total seconds
                    try:
                        if timestamp.count(':') == 1:  # MM:SS format
                            minutes, seconds = map(int, timestamp.split(':'))
                            total_seconds = minutes * 60 + seconds
                        elif timestamp.count(':') == 2:  # HH:MM:SS format
                            hours, minutes, seconds = map(int, timestamp.split(':'))
                            total_seconds = hours * 3600 + minutes * 60 + seconds
                        else:
                            # Invalid format, keep original
                            fixed_chapter_lines.append(line)
                            continue

                        # Apply the mixed format rule:
                        if total_seconds < 3600:  # Less than 60 minutes
                            # Format as MM:SS
                            minutes = total_seconds // 60
                            seconds = total_seconds % 60
                            new_timestamp = f"{minutes:02d}:{seconds:02d}"
                        else:  # 60 minutes or more
                            # Format as HH:MM:SS
                            hours = total_seconds // 3600
                            minutes = (total_seconds % 3600) // 60
                            seconds = total_seconds % 60
                            new_timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                        fixed_chapter_lines.append(f"{new_timestamp} {title}")
                    except ValueError:
                        # If parsing fails, keep the original
                        fixed_chapter_lines.append(line)

                chapters = "\n".join(fixed_chapter_lines)

            # All basic checks passed
            return chapters
        except Exception as e:
            import traceback
            import sys
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error generating chapters with {model}: {type(e).__name__}")
            print(f"Error details: {str(e)}")
            traceback.print_exc()
            # Enhanced: If the exception has a response or request attribute (httpx/OpenAI), log it
            if hasattr(e, 'response') and e.response is not None:
                print(f"Exception response status: {getattr(e.response, 'status_code', None)}")
                print(f"Exception response content: {getattr(e.response, 'text', None)}")
            if hasattr(e, 'request') and e.request is not None:
                print(f"Exception request info: {e.request}")
            # Log the full exception chain if available
            _, exc_value, _ = sys.exc_info()
            while exc_value and exc_value.__cause__:
                print(f"Caused by: {type(exc_value.__cause__).__name__}: {exc_value.__cause__}")
                exc_value = exc_value.__cause__
            continue

    print("All OpenAI models failed to generate chapters")
    return None
