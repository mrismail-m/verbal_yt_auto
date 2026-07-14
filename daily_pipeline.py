import os
import json
import subprocess
import requests
import sys
import re

def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def main():
    stories_file = "scraper/stories.json"
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1490291314045222992/QsHbOl4H3qTGGIhC65zcAPe10rXqrW4DsQffdtvVrem7-SYdEtMWL1raPQlHQW8z9ELB")

    if not os.path.exists(stories_file):
        print(f"Error: {stories_file} not found.")
        sys.exit(1)

    # 1. Run prompt generation to ensure stories have image_prompts
    print("Step 1: Running generate_image_prompts.py to generate prompts...")
    subprocess.run([sys.executable, "generate_image_prompts.py", "--file", stories_file], check=True)

    # Load stories to find the first unused story
    with open(stories_file, "r", encoding="utf-8") as f:
        stories = json.load(f)

    selected_story = None
    selected_idx = -1
    for idx, story in enumerate(stories):
        if not story.get("used"):
            # Ensure it has image_prompts generated
            if "image_prompts" in story:
                selected_story = story
                selected_idx = idx
                break

    if not selected_story:
        print("No unused stories with image prompts found! Checking if we can use one without prompts...")
        for idx, story in enumerate(stories):
            if not story.get("used"):
                selected_story = story
                selected_idx = idx
                break
        
        if not selected_story:
            print("All stories have been processed!")
            sys.exit(0)

    title = selected_story["title"]
    print(f"\nSelected Story: {title}")

    # 2. Generate images for the selected story
    print(f"\nStep 2: Generating images for '{title}'...")
    subprocess.run([sys.executable, "generate_images.py", "--file", stories_file, "--story", title], check=True)

    # 3. Compile the video for the selected story with 2.5s duration and captions burned in, and send to Discord
    print(f"\nStep 3: Creating captioned video for '{title}' (2.5s per image) and sharing to Discord...")
    subprocess.run([
        sys.executable, "create_video_with_captions.py",
        "--file", stories_file,
        "--story", title,
        "--duration", "2.5",
        "--webhook", webhook_url
    ], check=True)

    # 6. Mark as used and save stories.json
    selected_story["used"] = True
    with open(stories_file, "w", encoding="utf-8") as f:
        json.dump(stories, f, indent=2, ensure_ascii=False)
    print(f"\nStep 5: Marked '{title}' as used in stories.json.")

if __name__ == "__main__":
    main()
