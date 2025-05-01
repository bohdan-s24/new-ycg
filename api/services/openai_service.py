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
    timestamp_format = "MM:SS"
    if video_duration_minutes > 60:
        timestamp_format = "HH:MM:SS"

    # Enhanced prompt with USP messaging about viewer retention
    system_prompt = (
        f"You are an expert YouTube strategist and copywriter.\n\n"

        "## GOAL\n"
        "Generate concise, compelling YouTube chapter titles that keep viewers watching until the very end.\n"
        "The final chapter should feel like a climax — a payoff for the viewer's attention.\n\n"

        "## FORMAT\n"
        f"- Use only this format: `{timestamp_format} Chapter Title`\n"
        "- One chapter per line\n"
        "- No markdown, notes, or commentary\n\n"

        "## RULES\n"
        "1. Start at **00:00** with an engaging introduction.\n"
        "2. End with a compelling conclusion chapter.\n"
        "3. Use real transitions from the transcript — never invent timestamps.\n"
        "4. Chapters should follow natural flow (typically every 2–6 mins between key moments).\n"
        "5. Titles should be under 50 characters, ideally 20–40.\n"
        "6. Use casual, emotional, or intriguing phrasing without excessive clickbait.\n"
        "7. Identify 5–15 key transitions or topic changes (fewer chapters for shorter videos).\n"
        "8. Timestamp accuracy is crucial — no rounding or patterning.\n"
        "9. Keywords and emotion should reflect the transcript's voice.\n"
        "10. Each title should provoke curiosity to watch this chapter.\n\n"

        "## HOW TO DETECT TRANSITIONS\n"
        "- Numbering: 'first', 'tip #2', 'step 3'\n"
        "- Phrasing: 'next', 'moving on', 'another thing is...'\n"
        "- Shifts: 'as for...', 'regarding...', 'to summarize...'\n"
        "- Cues: [music], [pause], [transition], 'in this video...', 'final thoughts...'\n\n"

        "### Follow the Step-by-Step Process:\n"
        "1. **Analyze the full transcript** to understand the general context, content type (list, tutorial, story, etc.) and natural structure.\n"
        "2. **Identify 5–15 key transitions or 'aha' moments** (more if it's list-based — 1 chapter per item is OK).\n"
        "3. **Craft strong titles** with emotional triggers (curiosity, surprise, controversey, etc.). Use keywords from the transcript and avoid banal cliches. Highlight unique or shocking info.\n"
        "4. **Verify timestamps**:\n"
        "   - Match transitions exactly — no rounding or regular intervals.\n"
        "   - Ensure timestamps are in ascending order and fully cover the video.\n\n"
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
    timestamp_format = "MM:SS"
    if video_duration_minutes > 60:
        timestamp_format = "HH:MM:SS"

    final_reminder = (
        "\n### 🔍 FINAL CHECKLIST\n"
        f"- ✓ Chapters are formatted: `{timestamp_format} Chapter Title`\n"
        "- ✓ Start at 00:00 with introduction\n"
        "- ✓ End with a conclusion (curiosity peak)\n"
        "- ✓ Each chapter naturally follows the previous (no gaps)\n"
        "- ✓ Aim for 5-15 chapters (fewer for shorter videos)\n"
        "- ✓ Titles are under 50 characters, ideally 20-40\n"
        "- ✓ All timestamps are real and from transcript only\n"
        "- ✓ No even timestamp spacing or fabricated patterns\n"
        "- ✓ Each title is concise and provokes curiosity\n"
        "- ✓ Last chapter feels like a climax or payoff\n"
        "- ✓ No additional explanations, summaries, or markdown"
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

            # Prepare the input with transcript and final reminder
            combined_input = f"{formatted_transcript}\n\n---\n\n{final_reminder}"

            print("[OPENAI-REQUEST] Parameters:", {
                "model": model,
                "input": combined_input[:100] + ("..." if len(combined_input) > 100 else ""),
                "instructions": system_prompt[:100] + ("..." if len(system_prompt) > 100 else ""),
                "temperature": 0.7,
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
                    temperature=0.7,
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
            if not chapter_lines[0].startswith("00:00"):
                print("WARNING: First chapter doesn't start at 00:00, trying another model")
                continue
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
