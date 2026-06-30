import fs from 'fs';
import path from 'path';
import { google } from 'googleapis';
import http from 'http';
import url from 'url';
import open from 'open';
import destroyer from 'server-destroy';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Read credentials directly from your downloaded JSON file
const credentialsPath = path.resolve(__dirname, '../client_secret_2_393682492602-08vva3q34l103pmvh2hklnfvou79e4ck.apps.googleusercontent.com.json');
const keys = JSON.parse(fs.readFileSync(credentialsPath, 'utf8')).installed;

const REDIRECT_URI = 'http://localhost:3000';

const oauth2Client = new google.auth.OAuth2(keys.client_id, keys.client_secret, REDIRECT_URI);

const scopes = [
  'https://www.googleapis.com/auth/youtube.upload',
  'https://www.googleapis.com/auth/youtube.readonly',
  'https://www.googleapis.com/auth/yt-analytics.readonly',
];

async function authenticate() {
  return new Promise((resolve, reject) => {
    // Start a local server to capture the redirect from Google
    const server = http.createServer(async (req, res) => {
      try {
        if (req.url.indexOf('/') > -1 && req.url.indexOf('code=') > -1) {
          const qs = new url.URL(req.url, 'http://localhost:3000').searchParams;
          res.end('Authentication successful! You can close this tab and return to the terminal.');
          server.destroy();
          
          const { tokens } = await oauth2Client.getToken(qs.get('code'));
          oauth2Client.credentials = tokens;
          resolve(tokens);
        }
      } catch (e) {
        reject(e);
      }
    }).listen(3000, () => {
      // Open the browser to the authorize url
      const authorizeUrl = oauth2Client.generateAuthUrl({
        access_type: 'offline', // IMPORTANT: required to get a refresh token
        prompt: 'consent',      // Force consent screen to guarantee refresh token
        scope: scopes,
      });
      console.log(`Opening browser to authenticate...`);
      console.log(`If your browser doesn't open, manually go to:\n${authorizeUrl}\n`);
      open(authorizeUrl, { wait: false });
    });
    destroyer(server);
  });
}

authenticate().then((tokens) => {
  console.log('\n--- YOUR TOKENS ---');
  if (tokens.refresh_token) {
    console.log('Refresh Token:', tokens.refresh_token);
    console.log('\nCopy the Refresh Token and paste it into upload.mjs!');
  } else {
    console.log('No refresh token received. You might need to go to https://myaccount.google.com/permissions and revoke access, then try again.');
  }
}).catch(console.error);
