import fs from 'fs';
import path from 'path';
import { google } from 'googleapis';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Read credentials directly from your downloaded JSON file
const credentialsPath = path.resolve(__dirname, '../client_secret_2_393682492602-08vva3q34l103pmvh2hklnfvou79e4ck.apps.googleusercontent.com.json');
const keys = JSON.parse(fs.readFileSync(credentialsPath, 'utf8')).installed;

const REDIRECT_URI = 'http://localhost:3000';

import 'dotenv/config';

// REFRESH_TOKEN is loaded from .env locally, or GitHub Secrets in Actions
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

/**
 * Uploads a video to YouTube.
 * @param {string} videoPath - Path to the mp4 file
 * @param {object|array} metadata - Metadata object or array of objects
 */
export async function uploadVideo(videoPath, metadata) {
  let title, description, tags;

  if (Array.isArray(metadata) && metadata.length > 1) {
    // Handling a Quiz video containing multiple questions
    title = `ISSB Intelligence Test Quiz | ${metadata.length} Questions Challenge`;
    description = `Daily ISSB Intelligence Test practice — ${metadata.length} Questions Quiz.
Pause and guess before the timer reveals the answer!

🎯 Practice the full ISSB psych battery (WAT, SCT, SRT) free at ForcePrep-PK: https://www.forceprep.pk
📱 Join our prep community: [WhatsApp/Discord link]
#ISSB #ISSBPrep #IntelligenceTest #Pakistan #ArmedForces #Quiz`;
    tags = ['ISSB', 'Intelligence Test', 'Pakistan', 'Armed Forces', 'Quiz'];
  } else {
    // Handling a single question video
    const qData = Array.isArray(metadata) ? metadata[0] : metadata;
    const { id, subcategory } = qData;
    const displayCategory = subcategory.charAt(0).toUpperCase() + subcategory.slice(1);
    const categoryHashtag = '#' + displayCategory.replace(/\s+/g, '');

    title = `ISSB Intelligence Test — ${displayCategory} #${id} | 5 Second Challenge`;
    description = `Daily ISSB Intelligence Test practice — ${displayCategory} question #${id}.
Pause and guess before the timer reveals the answer!

🎯 Practice the full ISSB psych battery (WAT, SCT, SRT) free at ForcePrep-PK: https://www.forceprep.pk
📱 Join our prep community: [WhatsApp/Discord link]
#ISSB #ISSBPrep #IntelligenceTest #Pakistan #ArmedForces ${categoryHashtag}`;
    tags = ['ISSB', 'Intelligence Test', 'Pakistan', 'Armed Forces', displayCategory];
  }

  console.log(`\nUploading ${videoPath}...`);
  console.log(`Title: ${title}`);
  
  const fileSize = fs.statSync(videoPath).size;

  try {
    const response = await youtube.videos.insert({
      part: 'snippet,status',
      requestBody: {
        snippet: {
          title,
          description,
          tags,
          categoryId: '27', // 27 = Education
        },
        status: {
          privacyStatus: 'private', // Upload as private first, so you can review before publishing
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
    console.log(`URL: ${videoUrl}`);

    // Post to Discord
    const webhookUrl = 'https://discord.com/api/webhooks/1490291314045222992/QsHbOl4H3qTGGIhC65zcAPe10rXqrW4DsQffdtvVrem7-SYdEtMWL1raPQlHQW8z9ELB';
    const discordContent = `🎥 **New Video Uploaded!**\n\n**Title:** ${title}\n**Link:** ${videoUrl}`;
    
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

// Example usage if you want to run this file directly:
if (process.argv[1] === __filename) {
  const videoToUpload = path.resolve(__dirname, './out/v047.mp4');
  if (fs.existsSync(videoToUpload)) {
    uploadVideo(videoToUpload, { id: 'v047', subcategory: 'analogies' }).catch(console.error);
  } else {
    console.log(`File not found: ${videoToUpload}. Update the path to test.`);
  }
}
