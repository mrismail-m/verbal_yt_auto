const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());
const fs = require('fs');
const cheerio = require('cheerio');

const URL = 'https://americanliterature.com/childrens-stories/the-three-little-pigs';

async function scrape() {
    const browser = await puppeteer.launch({ 
        headless: "new",
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    console.log(`Navigating to ${URL}...`);
    await page.goto(URL, { waitUntil: 'domcontentloaded' });
    
    await new Promise(r => setTimeout(r, 5000));
    
    const content = await page.content();
    fs.writeFileSync('story_page.html', content);
    
    const $ = cheerio.load(content);
    // Find where the story text is stored
    // Typically in a div or article
    let storyText = $('div[itemprop="articleBody"]').text().trim();
    if (!storyText) {
       storyText = $('article').text().trim();
    }
    
    console.log('Extracted text preview:');
    console.log(storyText.substring(0, 200));
    
    await browser.close();
}

scrape().catch(console.error);
