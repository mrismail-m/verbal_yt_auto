import os
import json
import re
import subprocess
import argparse

def sanitize_filename(name: str) -> str:
    # Remove invalid characters for filenames
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def create_videos(file_path: str, story_title: str = None, force_duration: float = None):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        stories = json.load(f)

    base_dir = "generated_images"
    if not os.path.exists(base_dir):
        print(f"Error: Directory {base_dir} not found. Please run generate_images.py first.")
        return

    processed_videos = 0

    for i, story in enumerate(stories):
        title = story.get("title", f"Story {i}")
        if story_title and title != story_title:
            continue
            
        prompts_data = story.get("image_prompts")
        
        if not prompts_data or "scenes" not in prompts_data:
            continue

        safe_title = sanitize_filename(title)
        story_dir = os.path.join(base_dir, safe_title)
        
        if not os.path.exists(story_dir):
            continue

        scenes = prompts_data["scenes"]
        output_video = os.path.join(story_dir, f"{safe_title}_shorts.mp4")
        concat_file_path = os.path.join(story_dir, "concat.txt")

        # Check if we have all images for the scenes
        valid_scenes = []
        for scene in scenes:
            scene_number = scene.get("scene_number")
            duration = force_duration if force_duration is not None else scene.get("duration_seconds", 4)
            image_filename = f"scene_{scene_number:02d}.jpeg"
            image_path = os.path.join(story_dir, image_filename)
            
            if os.path.exists(image_path):
                valid_scenes.append({
                    "filename": image_filename,
                    "duration": duration
                })
        
        if not valid_scenes:
            print(f"[{i+1}/{len(stories)}] No images found for '{title}', skipping.")
            continue
            
        print(f"[{i+1}/{len(stories)}] Creating video for '{title}' ({len(valid_scenes)} scenes)...")

        # Write the ffmpeg concat demuxer file
        with open(concat_file_path, "w", encoding="utf-8") as f:
            for scene in valid_scenes:
                f.write(f"file '{scene['filename']}'\n")
                f.write(f"duration {scene['duration']}\n")
            # FFmpeg concat demuxer quirk: the last file needs to be specified again without a duration
            f.write(f"file '{valid_scenes[-1]['filename']}'\n")

        # Run ffmpeg
        # We enforce 1080x1920. We scale while maintaining aspect ratio, and pad with black if needed.
        # -r 30 ensures a smooth 30fps output
        ffmpeg_cmd = [
            "ffmpeg", "-y", 
            "-f", "concat", 
            "-safe", "0", 
            "-i", concat_file_path,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-c:v", "libx264",
            "-r", "30",
            output_video
        ]

        try:
            # We redirect stdout/stderr so it doesn't spam the console, but capture it in case of error
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            print(f"  -> Successfully created video: {output_video}")
            processed_videos += 1
        except subprocess.CalledProcessError as e:
            print(f"  -> Error creating video for '{title}'")
            print(f"FFmpeg error output: {e.stderr.decode('utf-8')}")
            
        # Clean up the temporary concat file
        if os.path.exists(concat_file_path):
            os.remove(concat_file_path)

    print(f"\nFinished. Created {processed_videos} videos.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create 1080x1920 videos from generated story images.")
    parser.add_argument("--file", type=str, default="scraper/stories.json", help="Path to stories.json")
    parser.add_argument("--story", type=str, default=None, help="Process only the story with this title")
    parser.add_argument("--duration", type=float, default=None, help="Force duration in seconds for each image")
    args = parser.parse_args()

    create_videos(args.file, args.story, args.duration)
