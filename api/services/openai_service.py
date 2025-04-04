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
    # Calculate reasonable chapter count
    suggested_chapter_count = max(5, min(int(video_duration_minutes / 3), 20))
    
    # Create detailed prompt
    prompt = f"""You are a professional video editor specializing in creating accurate YouTube chapters.

TASK:
Analyze the video transcript and create {suggested_chapter_count}-{suggested_chapter_count+5} chapters that accurately capture the content flow and major discussion points in the video.

FORMATTING REQUIREMENTS:
1. Each chapter must begin with its timestamp in MM:SS format, followed by a dash and the chapter title.
2. The first chapter MUST start at 00:00.
3. Format each chapter on a new line: "MM:SS - Chapter Title"
4. Focus on major content transitions and new discussion topics.
5. Chapters should have a natural distribution throughout the entire video.
6. DO NOT use quotation marks or any markdown formatting in your response.
7. Use clear, descriptive chapter titles that precisely reflect the video content at that timestamp.
8. Keep titles concise (2-7 words is ideal).

IMPORTANT:
- DO NOT make up content not in the transcript.
- Ensure chapter timestamps are in strictly ascending order.
- Place chapters at natural transition points where topics change.
- Create well-distributed chapters throughout the entire video length.
- The first chapter MUST be "00:00 - Introduction" or similar title reflective of the beginning content.
- DO NOT include any explanation, notes, or commentary in your response.
- ONLY return the chapters in the specified format.

YOUR RESPONSE MUST FOLLOW THIS EXACT STRUCTURE:
00:00 - Introduction
MM:SS - Chapter Title
MM:SS - Chapter Title
...and so on

The video is approximately {int(video_duration_minutes)} minutes long."""

    return prompt


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
        print("OpenAI client not configured, cannot generate chapters")
        return None
    
    print(f"Generating chapters for {video_id}")
    
    for model in Config.OPENAI_MODELS:
        try:
            print(f"Trying to generate chapters with {model}")
            
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": formatted_transcript}
                ],
                temperature=0.3,
                max_tokens=1024
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
            return chapters
            
        except Exception as e:
            print(f"Error generating chapters with {model}: {type(e).__name__}")
            print(f"Error details: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print("All OpenAI models failed to generate chapters")
    return None
