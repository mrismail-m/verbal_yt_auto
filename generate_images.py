import os
import json
import time
import argparse
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types
import io
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

def sanitize_filename(name: str) -> str:
    # Remove invalid characters for filenames
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def generate_fallback_image(image_path: str, title: str, scene_number: int, prompt_text: str, narration: str):
    # Width and height for a vertical YouTube Short (9:16)
    width, height = 1080, 1920
    # Stylish dark slate background
    image = Image.new("RGB", (width, height), color="#1e222b")
    draw = ImageDraw.Draw(image)
    
    # Try to load a clean system font, fall back to default if not found
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    
    title_font = None
    body_font = None
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                title_font = ImageFont.truetype(path, 60)
                body_font = ImageFont.truetype(path, 40)
                break
            except Exception:
                pass
                
    if title_font is None:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        
    # Draw title header
    draw.text((540, 250), title.upper(), fill="#ffd700", font=title_font, anchor="mm")
    draw.text((540, 350), f"SCENE {scene_number}", fill="#ffffff", font=body_font, anchor="mm")
    
    # Wrap text
    text_to_wrap = narration if narration else prompt_text
    wrapped_lines = []
    words = text_to_wrap.split()
    current_line = []
    for word in words:
        current_line.append(word)
        line_str = " ".join(current_line)
        # Check text width
        try:
            bbox = draw.textbbox((0, 0), line_str, font=body_font)
            line_width = bbox[2] - bbox[0]
        except Exception:
            # Fallback for old PIL versions
            line_width = len(line_str) * 20
            
        if line_width > 900:
            current_line.pop()
            wrapped_lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        wrapped_lines.append(" ".join(current_line))
        
    # Draw wrapped text centered vertically
    y = 800
    for line in wrapped_lines:
        draw.text((540, y), line, fill="#e1e1e1", font=body_font, anchor="mm")
        y += 60
        
    # Draw a thin gold border for aesthetic style
    draw.rectangle([20, 20, 1060, 1900], outline="#ffd700", width=4)
        
    image.save(image_path, "JPEG")
    print(f"     [Fallback] Generated text-only scene card at {image_path}")

def generate_images(file_path: str, test_mode: bool = False, story_title: str = None):
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
        if story_title and title != story_title:
            continue
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
            narration = scene.get("narration", "")
            
            if not scene_number or not prompt_text:
                continue
                
            image_filename = f"scene_{scene_number:02d}.jpeg"
            image_path = os.path.join(story_dir, image_filename)
            
            if os.path.exists(image_path):
                print(f"  -> Skipping {image_filename}, already exists.")
                continue

            print(f"  -> Generating {image_filename}...")
            
            try:
                # Use gemini-2.5-flash-image for image generation via generate_content
                result = client.models.generate_content(
                    model='gemini-2.5-flash-image',
                    contents=prompt_text,
                    config=types.GenerateContentConfig(
                        response_modalities=["TEXT", "IMAGE"]
                    )
                )
                
                image_saved = False
                if result.candidates and result.candidates[0].content.parts:
                    for part in result.candidates[0].content.parts:
                        if part.inline_data is not None:
                            image_bytes = part.inline_data.data
                            image = Image.open(io.BytesIO(image_bytes))
                            image.save(image_path, "JPEG")
                            print(f"     Saved {image_path} via Gemini API")
                            processed_images += 1
                            image_saved = True
                            break
                            
                if not image_saved:
                    print("     Failed: No image inline data returned. Generating fallback card...")
                    generate_fallback_image(image_path, title, scene_number, prompt_text, narration)
                    processed_images += 1
                
                # Rate limit delay
                time.sleep(4)
                
            except Exception as e:
                print(f"     Gemini API Error: {e}. Generating fallback card...")
                generate_fallback_image(image_path, title, scene_number, prompt_text, narration)
                processed_images += 1
                time.sleep(1)

        if test_mode:
            print("\nTest mode enabled. Stopping after 1 item.")
            break

    print(f"\nFinished processing. Generated {processed_images} new images.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate images for stories using Gemini Imagen 3.")
    parser.add_argument("--file", type=str, default="scraper/stories.json", help="Path to stories.json")
    parser.add_argument("--test", action="store_true", help="Run on only the first item")
    parser.add_argument("--story", type=str, default=None, help="Process only the story with this title")
    args = parser.parse_args()

    generate_images(args.file, args.test, args.story)
