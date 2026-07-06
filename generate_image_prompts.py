import json
import os
import time
import argparse
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()
from google import genai
from google.genai import types

# Define the structured output schema using Pydantic
class Scene(BaseModel):
    scene_number: int = Field(description="The sequential number of the scene.")
    image_prompt: str = Field(description="detailed visual description of this scene's action and setting, framed for a 9:16 vertical video — MUST include the exact art_style text verbatim so every image in the sequence looks visually consistent")
    duration_seconds: int = Field(description="Duration in seconds, e.g. 4")

class VideoContent(BaseModel):
    video_title: str = Field(description="punchy YouTube title under 60 chars, include #Shorts")
    video_description: str = Field(description="2-3 sentence description with 3-5 relevant hashtags including #Shorts")
    art_style: str = Field(description="one locked art style + character description string, e.g. 'warm watercolor storybook illustration, soft pastel palette. Characters: [describe each recurring character's distinct visual features so they stay consistent across scenes]'")
    scenes: list[Scene] = Field(description="List of 6-8 visual scenes.")

def process_stories(file_path: str, test_mode: bool = False):
    # Ensure API key is set
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        return

    # Initialize Gemini client
    client = genai.Client()

    # Load stories
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            stories = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Could not parse JSON from {file_path}.")
            return

    print(f"Loaded {len(stories)} stories from {file_path}.")

    processed_count = 0

    for i, story in enumerate(stories):
        title = story.get("title", f"Story {i}")
        
        # Check if already processed
        if "image_prompts" in story:
            print(f"[{i+1}/{len(stories)}] Skipping '{title}' - already processed.")
            continue

        print(f"[{i+1}/{len(stories)}] Processing '{title}'...")
        story_text = story.get("text", "")
        if not story_text:
            print(f"  Warning: No text found for '{title}'. Skipping.")
            continue

        prompt = f"""
You are a creative director for a children's YouTube Shorts channel that creates silent, visual-only story retellings.

STORY TITLE: {title}
STORY TEXT: {story_text}

Break the story into 6-8 visual scenes. Return STRICT JSON only — no markdown fences, no preamble, no explanation.

{{
  "video_title": "punchy YouTube title under 60 chars, include #Shorts",
  "video_description": "2-3 sentence description with 3-5 relevant hashtags including #Shorts",
  "art_style": "one locked art style + character description string, e.g. 'warm watercolor storybook illustration, soft pastel palette. Characters: [describe each recurring character's distinct visual features so they stay consistent across scenes]'",
  "scenes": [
    {{
      "scene_number": 1,
      "image_prompt": "detailed visual description of this scene's action and setting, framed for a 9:16 vertical video — MUST include the exact art_style text verbatim so every image in the sequence looks visually consistent",
      "duration_seconds": 4
    }}
  ]
}}
"""

        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=VideoContent,
                    temperature=0.7,
                ),
            )
            
            # The structured output is in response.text as JSON string.
            # Parse it to a dict and store it in the story.
            result_json = json.loads(response.text)
            story["image_prompts"] = result_json
            
            # Save immediately
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(stories, f, indent=2, ensure_ascii=False)
                
            print(f"  Success: Generated {len(result_json.get('scenes', []))} scenes.")
            processed_count += 1
            
            if test_mode:
                print("\nTest mode enabled. Stopping after 1 item.")
                break
                
            # Rate limit delay (adjust as needed)
            time.sleep(3)
            
        except Exception as e:
            print(f"  Error processing '{title}': {e}")
            time.sleep(5)  # Wait a bit longer on error

    print(f"\nFinished processing. Newly generated: {processed_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate image prompts for stories using Gemini.")
    parser.add_argument("--file", type=str, default="scraper/stories.json", help="Path to stories.json")
    parser.add_argument("--test", action="store_true", help="Run on only the first unprocessed item")
    args = parser.parse_args()

    process_stories(args.file, args.test)
