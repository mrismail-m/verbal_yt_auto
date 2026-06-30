import fs from 'fs';
import path from 'path';
import { google } from 'googleapis';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Read credentials
const credentialsPath = path.resolve(__dirname, '../client_secret_2_393682492602-08vva3q34l103pmvh2hklnfvou79e4ck.apps.googleusercontent.com.json');
const keys = JSON.parse(fs.readFileSync(credentialsPath, 'utf8')).installed;

import 'dotenv/config';

const REDIRECT_URI = 'http://localhost:3000';
const REFRESH_TOKEN = process.env.YOUTUBE_REFRESH_TOKEN;
if (!REFRESH_TOKEN) {
  throw new Error("YOUTUBE_REFRESH_TOKEN is not set in environment variables.");
}

const oauth2Client = new google.auth.OAuth2(keys.client_id, keys.client_secret, REDIRECT_URI);
oauth2Client.setCredentials({ refresh_token: REFRESH_TOKEN });

const youtube = google.youtube({ version: 'v3', auth: oauth2Client });
const youtubeAnalytics = google.youtubeAnalytics({ version: 'v2', auth: oauth2Client });

async function getAnalytics() {
  try {
    console.log("Fetching uploads playlist ID...");
    // 1. Get the authenticated user's uploads playlist ID
    const channelRes = await youtube.channels.list({
      part: 'contentDetails',
      mine: true
    });
    
    if (!channelRes.data.items || channelRes.data.items.length === 0) {
      throw new Error('Channel not found.');
    }
    
    const uploadsPlaylistId = channelRes.data.items[0].contentDetails.relatedPlaylists.uploads;

    console.log("Fetching recent videos...");
    // 2. Get the last 15 videos uploaded
    const playlistRes = await youtube.playlistItems.list({
      part: 'snippet',
      playlistId: uploadsPlaylistId,
      maxResults: 15
    });

    const now = new Date();
    const twoDaysAgo = new Date(now.getTime() - (48 * 60 * 60 * 1000));

    // Filter videos uploaded in the last 48 hours
    const recentVideos = playlistRes.data.items.filter(item => {
      const publishedAt = new Date(item.snippet.publishedAt);
      return publishedAt >= twoDaysAgo;
    });

    if (recentVideos.length === 0) {
      console.log('No videos uploaded in the last 48 hours. Nothing to report.');
      return;
    }

    const videoIds = recentVideos.map(item => item.snippet.resourceId.videoId).join(',');
    
    console.log(`Found ${recentVideos.length} recent videos. Fetching analytics...`);

    // Analytics API requires dates in YYYY-MM-DD format
    // Since Analytics data is delayed, we query from 7 days ago to today
    const sevenDaysAgo = new Date(now.getTime() - (7 * 24 * 60 * 60 * 1000));
    const formatDate = (d) => d.toISOString().split('T')[0];

    // 3. Query YouTube Analytics API for those videos
    const analyticsRes = await youtubeAnalytics.reports.query({
      ids: 'channel==MINE',
      startDate: formatDate(sevenDaysAgo),
      endDate: formatDate(now),
      metrics: 'views,estimatedMinutesWatched,averageViewDuration',
      dimensions: 'video',
      filters: `video==${videoIds}`
    });

    const rows = analyticsRes.data.rows || [];
    
    // Map data back to video titles
    let reportText = '📊 **Daily YouTube Analytics Report** 📊\n*Videos uploaded in the last 48h*\n\n';
    
    recentVideos.forEach(video => {
      const vId = video.snippet.resourceId.videoId;
      const title = video.snippet.title;
      const row = rows.find(r => r[0] === vId);
      
      const views = row ? row[1] : 0;
      const watchTime = row ? Math.round(row[2]) : 0;
      const avgDuration = row ? Math.round(row[3]) : 0;

      reportText += `**${title}**\n`;
      reportText += `👁️ Views: ${views}\n`;
      reportText += `⏱️ Watch Time: ${watchTime} mins\n`;
      reportText += `🔄 Avg Duration: ${avgDuration} sec\n`;
      reportText += `🔗 https://youtu.be/${vId}\n\n`;
    });

    console.log("Formatting report:\n", reportText);

    // 4. Post to Discord
    const webhookUrl = 'https://discord.com/api/webhooks/1490291314045222992/QsHbOl4H3qTGGIhC65zcAPe10rXqrW4DsQffdtvVrem7-SYdEtMWL1raPQlHQW8z9ELB';
    await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: reportText }),
    });

    console.log('Analytics posted to Discord successfully.');

  } catch (error) {
    console.error('Error fetching analytics:', error.message);
  }
}

getAnalytics();
