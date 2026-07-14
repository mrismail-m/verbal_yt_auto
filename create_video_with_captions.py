import os
import json
import re
import subprocess
import argparse
import requests
import shutil
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Predefined high-quality captions for "The Three Little Pigs" to ensure perfect layout and storytelling
PREDEFINED_PIGS_CAPTIONS = [
    "Three little pigs set out to seek their fortune and build new homes.",
    "The lazy first pig built a house of straw, but the wolf blew it down!",
    "The second pig built a house of sticks, but it was no match for the wolf.",
    "The smart third pig built a sturdy brick house that would not fall.",
    "Furious, the hungry wolf climbed to the roof to slide down the chimney.",
    "Plop! The wolf fell straight into a boiling pot of hot water!",
    "Safe at last, the three little pigs celebrated their victory!"
]

def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def wrap_text(text: str, max_chars: int = 28) -> str:
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    for word in words:
        if current_length + len(word) + 1 > max_chars:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += len(word) + 1
    if current_line:
        lines.append(" ".join(current_line))
    return "\n".join(lines)

def clean_text_for_ffmpeg(text: str) -> str:
    # Replace standard quotes with premium curly ones to avoid escape issues in FFmpeg
    text = text.replace("'", "’")
    text = text.replace('"', "”")
    # Escape colons and percent signs which are special in drawtext
    text = text.replace(':', '\\:')
    text = text.replace('%', '\\%')
    return text

def get_captions(story, client=None):
    title = story.get("title", "")
    scenes = story.get("image_prompts", {}).get("scenes", [])
    
    # If the story is Three Little Pigs, return the predefined ones
    if title == "The Three Little Pigs" and len(scenes) == len(PREDEFINED_PIGS_CAPTIONS):
        print("Using predefined captions for The Three Little Pigs.")
        return PREDEFINED_PIGS_CAPTIONS

    # Check if captions are already in the story JSON
    captions = [s.get("caption") for s in scenes if s.get("caption")]
    if len(captions) == len(scenes):
        print("Found existing captions in stories.json.")
        return captions

    # Generate using Gemini
    if not client:
        print("Gemini client not initialized. Cannot generate captions.")
        return [f"Scene {s.get('scene_number')}" for s in scenes]

    print(f"Generating captions for '{title}' using Gemini...")
    story_text = story.get("text", "")
    
    scenes_info = [{"scene_number": s.get("scene_number"), "image_prompt": s.get("image_prompt")} for s in scenes]
    
    prompt = f"""
You are a storyteller for kids. For the story "{title}", here is the story text:
{story_text}

Here is the visual sequence of scenes:
{json.dumps(scenes_info, indent=2)}

For each scene, write a short, engaging caption (under 12 words) to overlay on the video.
Return strict JSON as a list of strings in the exact order of the scenes. Do not return markdown formatting.
Example:
[
  "First caption...",
  "Second caption..."
]
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )
        generated_captions = json.loads(response.text)
        if isinstance(generated_captions, list) and len(generated_captions) == len(scenes):
            return generated_captions
        else:
            print("Warning: Generated captions length mismatch, falling back to defaults.")
    except Exception as e:
        print(f"Error generating captions: {e}")
        
    return [f"Scene {s.get('scene_number')}" for s in scenes]

def create_video_with_captions(file_path: str, story_title: str, duration: float, webhook_url: str):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        stories = json.load(f)

    # Find the requested story
    story_idx = -1
    for idx, s in enumerate(stories):
        if s.get("title") == story_title:
            story_idx = idx
            break

    if story_idx == -1:
        print(f"Error: Story '{story_title}' not found in {file_path}.")
        return

    story = stories[story_idx]
    prompts_data = story.get("image_prompts")
    if not prompts_data or "scenes" not in prompts_data:
        print(f"Error: Story '{story_title}' does not have image prompts generated yet.")
        return

    base_dir = "generated_images"
    safe_title = sanitize_filename(story_title)
    story_dir = os.path.join(base_dir, safe_title)
    
    if not os.path.exists(story_dir):
        print(f"Error: Directory {story_dir} not found. Please run generate_images.py first.")
        return

    # Check for Gemini Client
    api_key = os.environ.get("GEMINI_API_KEY")
    client = None
    if api_key:
        client = genai.Client()

    # Get captions
    scenes = prompts_data["scenes"]
    captions = get_captions(story, client)

    # Save captions back to JSON if updated
    updated = False
    for idx, scene in enumerate(scenes):
        if scene.get("caption") != captions[idx]:
            scene["caption"] = captions[idx]
            updated = True

    if updated:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(stories, f, indent=2, ensure_ascii=False)
        print("Updated stories.json with generated captions.")

    # Create temporary directory for individual clips
    temp_dir = os.path.join(story_dir, "temp_clips")
    os.makedirs(temp_dir, exist_ok=True)

    # We need a font file
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if not os.path.exists(font_path):
        # Fallback to Liberation
        font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if not os.path.exists(font_path):
            print("Warning: Font file not found. Captions may fail to render.")

    # Generate individual clips
    valid_clips = []
    print(f"\nGenerating {len(scenes)} individual scene clips...")
    for idx, scene in enumerate(scenes):
        scene_num = scene.get("scene_number")
        image_filename = f"scene_{scene_num:02d}.jpeg"
        image_path = os.path.join(story_dir, image_filename)
        
        if not os.path.exists(image_path):
            print(f"Warning: Image {image_filename} not found, skipping scene.")
            continue

        caption_text = captions[idx]
        wrapped_caption = wrap_text(caption_text, max_chars=26)
        cleaned_caption = clean_text_for_ffmpeg(wrapped_caption)

        clip_filename = f"clip_{scene_num:02d}.mp4"
        clip_path = os.path.join(temp_dir, clip_filename)

        # FFmpeg command to build 2.5s clip with centered, bottom-positioned text
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p,drawtext=fontfile='{font_path}':text='{cleaned_caption}':fontcolor=white:fontsize=44:box=1:boxcolor=black@0.6:boxborderw=18:line_spacing=12:x=(w-text_w)/2:y=h-350",
            "-t", str(duration),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            clip_path
        ]

        try:
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            print(f"  -> Generated clip {idx+1}/{len(scenes)}: {clip_path}")
            valid_clips.append(clip_path)
        except subprocess.CalledProcessError as e:
            print(f"  -> Error generating clip for scene {scene_num}")
            print(f"FFmpeg error: {e.stderr.decode('utf-8')}")

    if not valid_clips:
        print("Error: No clips generated.")
        return

    # Write concat file
    concat_file_path = os.path.join(temp_dir, "concat.txt")
    with open(concat_file_path, "w", encoding="utf-8") as f:
        for clip in valid_clips:
            # Must write relative path or use safe 0
            f.write(f"file '{os.path.basename(clip)}'\n")

    # Concatenate clips
    output_video = os.path.join(story_dir, f"{safe_title}_shorts_captions.mp4")
    print(f"\nConcatenating clips into final video: {output_video}")
    
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file_path,
        "-c", "copy",
        output_video
    ]

    try:
        subprocess.run(concat_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print("  -> Concatenation completed successfully!")
    except subprocess.CalledProcessError as e:
        print("  -> Error concatenating video clips.")
        print(f"FFmpeg error: {e.stderr.decode('utf-8')}")
        return

    # Clean up temp clips directory
    try:
        shutil.rmtree(temp_dir)
        print("  -> Cleaned up temporary clip files.")
    except Exception as e:
        print(f"  -> Warning: failed to delete temp clips: {e}")

    # Send to Discord Webhook
    if webhook_url:
        print(f"\nSharing video and YouTube metadata to Discord...")
        
        # Build YouTube upload details
        base_title = prompts_data.get("video_title", story_title)
        base_title = re.sub(r'#Shorts', '', base_title, flags=re.IGNORECASE).strip()
        yt_title = f"{base_title} #shorts #viral #kids #story"

        base_desc = prompts_data.get("video_description", "Watch this classic kids story!")
        base_desc = re.sub(r'#Shorts|#viral|#kids|#story', '', base_desc, flags=re.IGNORECASE).strip()
        yt_description = f"{base_desc}\n\n#shorts #viral #kids #story"
        
        yt_tags = ["shorts", "viral", "kids", "story", story_title]
        
        scene_captions_str = "\n".join([f"**Scene {idx+1}**: {caption}" for idx, caption in enumerate(captions)])
        
        discord_message = (
            f"🎥 **Daily Story Short: {story_title}**\n"
            f"⏱️ **Duration**: {duration}s per scene (Total: {len(valid_clips)*duration}s)\n\n"
            f"📜 **Burned-in Scene Subtitles:**\n{scene_captions_str}\n\n"
            f"🔴 **YouTube Upload Details (Captions):**\n"
            f"**Title (Max 100 chars):**\n`{yt_title}`\n\n"
            f"**Description:**\n```\n{yt_description}\n```\n"
            f"**Tags:**\n`{', '.join(yt_tags)}`\n"
        )
        
        payload = {"content": discord_message}
        
        try:
            with open(output_video, "rb") as video_file:
                files = {
                    "file": (f"{safe_title}_shorts_captions.mp4", video_file, "video/mp4")
                }
                response = requests.post(webhook_url, data=payload, files=files)
                if response.status_code in [200, 204]:
                    print("Successfully shared video to Discord!")
                else:
                    print(f"Failed to post to Discord. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            print(f"Error sharing to Discord: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create story video with captions burned in and share to Discord.")
    parser.add_argument("--story", type=str, default="The Three Little Pigs", help="Title of the story to process")
    parser.add_argument("--duration", type=float, default=2.5, help="Duration in seconds for each image")
    parser.add_argument("--file", type=str, default="scraper/stories.json", help="Path to stories.json")
    parser.add_argument("--webhook", type=str, default="https://discord.com/api/webhooks/1490291314045222992/QsHbOl4H3qTGGIhC65zcAPe10rXqrW4DsQffdtvVrem7-SYdEtMWL1raPQlHQW8z9ELB", help="Discord Webhook URL")
    args = parser.parse_args()

    create_video_with_captions(args.file, args.story, args.duration, args.webhook)
