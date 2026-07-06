const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());
const fs = require('fs');

const URL = 'https://americanliterature.com/short-stories-for-children/';

async function scrape() {
    const browser = await puppeteer.launch({ 
        headless: "new",
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    console.log(`Navigating to ${URL}...`);
    await page.goto(URL, { waitUntil: 'domcontentloaded' });
    
    console.log('Waiting for potential Cloudflare challenge...');
    await new Promise(r => setTimeout(r, 8000));
    
    const content = await page.content();
    fs.writeFileSync('page.html', content);
    console.log('Saved page.html');
    
    await browser.close();
}

scrape().catch(console.error);
