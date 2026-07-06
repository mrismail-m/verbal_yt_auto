import os
import json
import time
import argparse
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image
import io

load_dotenv()

def sanitize_filename(name: str) -> str:
    # Remove invalid characters for filenames
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def generate_images(file_path: str):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        return

    client = genai.Client()

    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        stories = json.load(f)

    # Base output directory
    output_base_dir = "generated_images"
    os.makedirs(output_base_dir, exist_ok=True)

    processed_images = 0

    for i, story in enumerate(stories):
        title = story.get("title", f"Story {i}")
        prompts_data = story.get("image_prompts")
        
        if not prompts_data or "scenes" not in prompts_data:
            continue

        safe_title = sanitize_filename(title)
        story_dir = os.path.join(output_base_dir, safe_title)
        os.makedirs(story_dir, exist_ok=True)

        scenes = prompts_data["scenes"]
        print(f"\n[{i+1}/{len(stories)}] Processing images for '{title}' ({len(scenes)} scenes)")

        for scene in scenes:
            scene_number = scene.get("scene_number")
            prompt_text = scene.get("image_prompt")
            
            if not scene_number or not prompt_text:
                continue
                
            image_filename = f"scene_{scene_number:02d}.jpeg"
            image_path = os.path.join(story_dir, image_filename)
            
            if os.path.exists(image_path):
                print(f"  -> Skipping {image_filename}, already exists.")
                continue

            print(f"  -> Generating {image_filename}...")
            
            try:
                # Use imagen-3.0-generate-002 for image generation
                result = client.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=prompt_text,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type="image/jpeg",
                        aspect_ratio="9:16",
                        # person_generation="ALLOW_ADULT" # Optional: add if needed for character generation
                    )
                )
                
                if result.generated_images:
                    generated_image = result.generated_images[0]
                    # Convert raw bytes to a PIL Image and save
                    image_bytes = generated_image.image.image_bytes
                    image = Image.open(io.BytesIO(image_bytes))
                    image.save(image_path)
                    print(f"     Saved {image_path}")
                    processed_images += 1
                else:
                    print(f"     Failed: No image returned for {image_filename}")
                
                # Rate limit delay for image generation (adjust based on your tier limits)
                time.sleep(4)
                
            except Exception as e:
                print(f"     Error generating {image_filename}: {e}")
                time.sleep(10) # Longer delay on error

    print(f"\nFinished processing. Generated {processed_images} new images.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate images for stories using Gemini Imagen 3.")
    parser.add_argument("--file", type=str, default="scraper/stories.json", help="Path to stories.json")
    args = parser.parse_args()

    generate_images(args.file)
