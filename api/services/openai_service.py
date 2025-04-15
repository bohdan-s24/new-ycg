"""
OpenAI API integration service
"""
import traceback
import os
from typing import Dict, Any, Optional, List
from openai import OpenAI, AsyncOpenAI
from api.config import Config


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
    
    # Use the original prompt logic
    system_prompt = (
        f"You are an expert in YouTube content optimization and copywriting.\n\n"

        "Your task is to create short, punchy, emotionally compelling YouTube chapter titles that boost watch time and engagement.\n"
        "Think like a top-tier strategist. Titles must feel urgent, powerful, and irresistible.\n\n"

        "### CORE RULES:\n"
        "1. Start the first chapter at **00:00** (Introduction) and cover the entire video.\n"
        "2. Use **real transitions** from the transcript — never make up timestamps.\n"
        "3. Include **both** an introduction and conclusion chapter.\n"
        "4. Titles should be 30–50 characters (max 80), emotionally engaging, and written in a casual, clickbait-style tone.\n"
        "5. Chapters should be spaced naturally (typically 2–6 minutes), with balanced distribution across the video.\n"
        f"6. Format each chapter like this: `{timestamp_format} Chapter Title` (each on a new line).\n\n"

        "### HOW TO SPOT CONTENT BREAKS:\n"
        "- Numbering: 'first', 'tip #2', 'step 3'\n"
        "- Transitions: 'next', 'moving on', 'let's talk about'\n"
        "- Topic shifts: 'as for...', 'regarding...', 'when it comes to...'\n"
        "- Cues in transcript: [music], [pause], [transition]\n"
        "- Intro/Outro markers: 'in this video...', 'to summarize...', 'final thoughts...'\n\n"

        "### Follow the Step-by-Step Process:\n"
        "1. **Analyze the full transcript** to understand the general context, content type (list, tutorial, story, etc.) and natural structure.\n"
        "2. **Identify 10–15 key transitions or 'aha' moments** (more if it's list-based — 1 chapter per item is OK).\n"
        "3. **Craft strong titles** with emotional triggers (curiosity, surprise, controversey, etc.). Use keywords from the transcript and avoid banal cliches. Highlight unique or shocking info.\n"
        "4. **Verify timestamps**:\n"
        "   - Match transitions exactly — no rounding or regular intervals.\n"
        "   - Ensure timestamps are in ascending order and fully cover the video.\n\n"

        "### FINAL OUTPUT FORMAT:\n"
        f"- Use ONLY this format: `{timestamp_format} Chapter Title`\n"
        "- Each chapter on a new line\n"
        "- NO extra text, notes, markdown, or commentary\n\n"

        "###  QUALITY CHECK:\n"
        "- ✓ 00:00 introduction is present\n"
        "- ✓ Clear chapter near the end (conclusion)\n"
        "- ✓ All major content transitions captured\n"
        "- ✓ Accurate timestamps from transcript only\n"
        "- ✓ No even intervals or timestamp patterns\n"
        "- ✓ 10–15 chapters unless list-based\n"
        "- ✓ All titles under 80 characters\n"
    )
    
    return system_prompt


async def generate_chapters_with_openai(system_prompt: str, video_id: str, formatted_transcript: str, timeout: int = 30) -> Optional[str]:
    """
    Generate chapters using OpenAI with better timestamp distribution.
    
    Args:
        system_prompt: System prompt for the OpenAI API
        video_id: YouTube video ID
        formatted_transcript: Formatted transcript text
        timeout: Timeout for the OpenAI API call in seconds
        
    Returns:
        Generated chapters or None if all models fail
    """
    if not async_openai_client:
        print("OpenAI async client not configured, cannot generate chapters")
        return None
    
    print(f"Generating chapters for {video_id}")
    
    models_to_try = [
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-3.5-turbo-0125",
        "gpt-3.5-turbo"
    ]
    
    for model in models_to_try:
        try:
            print(f"Trying model: {model}")
            
            response = await async_openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": formatted_transcript}
                ],
                timeout=timeout
            )
            
            chapters = response.choices[0].message.content.strip()
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
            print(f"Error generating chapters with {model}: {type(e).__name__}")
            print(f"Error details: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print("All OpenAI models failed to generate chapters")
    return None
