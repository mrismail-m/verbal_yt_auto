import fs from 'fs';
import path from 'path';
import { google } from 'googleapis';
import { fileURLToPath } from 'url';
import 'dotenv/config';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Read credentials directly from the client secrets file
const credentialsPath = path.resolve(__dirname, '../client_secret_2_393682492602-08vva3q34l103pmvh2hklnfvou79e4ck.apps.googleusercontent.com.json');
const keys = JSON.parse(fs.readFileSync(credentialsPath, 'utf8')).installed;

const REDIRECT_URI = 'http://localhost:3000';

const REFRESH_TOKEN = process.env.YOUTUBE_REFRESH_TOKEN;
if (!REFRESH_TOKEN) {
  throw new Error("YOUTUBE_REFRESH_TOKEN is not set in environment variables.");
}

const oauth2Client = new google.auth.OAuth2(
  keys.client_id,
  keys.client_secret,
  REDIRECT_URI
);

oauth2Client.setCredentials({
  refresh_token: REFRESH_TOKEN
});

const youtube = google.youtube({
  version: 'v3',
  auth: oauth2Client,
});

async function main() {
  const videoPath = path.resolve(__dirname, '../generated_images/The Three Little Pigs/The Three Little Pigs_shorts.mp4');
  if (!fs.existsSync(videoPath)) {
    throw new Error(`Video file not found at ${videoPath}`);
  }

  // Load the story from stories.json to get metadata
  const storiesPath = path.resolve(__dirname, '../scraper/stories.json');
  const stories = JSON.parse(fs.readFileSync(storiesPath, 'utf8'));
  const story = stories.find(s => s.title === 'The Three Little Pigs');
  if (!story) {
    throw new Error("Story 'The Three Little Pigs' not found in stories.json");
  }

  // Base title from story, removing any existing #Shorts to avoid duplication if we append
  let baseTitle = story.image_prompts.video_title || "Three Little Pigs Outsmart The Big Bad Wolf!";
  baseTitle = baseTitle.replace(/#Shorts/gi, '').trim();
  
  // Create final title with exact tags requested
  const title = `${baseTitle} #shorts #viral #kids #story`;
  
  // Base description
  let baseDesc = story.image_prompts.video_description || "Watch the classic tale of the Three Little Pigs unfold!";
  // Remove existing occurrences of these tags to clean up and append them clearly
  baseDesc = baseDesc.replace(/#Shorts/gi, '').replace(/#viral/gi, '').replace(/#kids/gi, '').replace(/#story/gi, '').trim();
  
  const description = `${baseDesc}

#shorts #viral #kids #story`;

  const tags = ['Three Little Pigs', 'Fairy Tale', 'Kids Story', 'shorts', 'viral', 'kids', 'story'];

  console.log(`\nUploading ${videoPath}...`);
  console.log(`Title: ${title}`);
  console.log(`Description: ${description}`);
  console.log(`Tags: ${JSON.stringify(tags)}`);
  
  const fileSize = fs.statSync(videoPath).size;

  try {
    const response = await youtube.videos.insert({
      part: 'snippet,status',
      requestBody: {
        snippet: {
          title,
          description,
          tags,
          categoryId: '27', // Education
        },
        status: {
          privacyStatus: 'public', // Automatically publish to the public
          selfDeclaredMadeForKids: false,
        },
      },
      media: {
        body: fs.createReadStream(videoPath),
      },
    }, {
      onUploadProgress: evt => {
        const progress = (evt.bytesRead / fileSize) * 100;
        process.stdout.write(`\rUploading: ${Math.round(progress)}%`);
      },
    });

    console.log(`\nUpload successful! Video ID: ${response.data.id}`);
    const videoUrl = `https://youtu.be/${response.data.id}`;
    const shortUrl = `https://www.youtube.com/shorts/${response.data.id}`;
    console.log(`URL: ${videoUrl}`);
    console.log(`Short URL: ${shortUrl}`);

    // Post to Discord (same webhook as the other upload script)
    const webhookUrl = 'https://discord.com/api/webhooks/1490291314045222992/QsHbOl4H3qTGGIhC65zcAPe10rXqrW4DsQffdtvVrem7-SYdEtMWL1raPQlHQW8z9ELB';
    const discordContent = `🎥 **New Story Video Uploaded!**\n\n**Title:** ${title}\n**Link:** ${shortUrl}`;
    
    try {
      await fetch(webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content: discordContent }),
      });
      console.log('Successfully posted to Discord!');
    } catch (discordError) {
      console.error('Failed to post to Discord:', discordError.message);
    }

    return response.data;
  } catch (error) {
    console.error('\nError uploading video:', error.message);
    if (error.response?.data?.error?.message) {
      console.error('API Error:', error.response.data.error.message);
    }
    throw error;
  }
}

main().catch(console.error);
