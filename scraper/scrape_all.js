const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());
const fs = require('fs');
const cheerio = require('cheerio');
const path = require('path');

const BASE_URL = 'https://americanliterature.com';

async function main() {
    // Read the main page we already saved
    const mainPageHtml = fs.readFileSync('page.html', 'utf8');
    const $ = cheerio.load(mainPageHtml);
    
    const storyLinksMap = new Map();
    $('.story-grid figure.al-figure a').each((i, el) => {
        const href = $(el).attr('href');
        const text = $(el).find('figcaption').text().trim();
        if (href && text) {
            storyLinksMap.set(href, text);
        }
    });

    const linksArray = Array.from(storyLinksMap.keys()).map(link => {
        return {
            url: link.startsWith('http') ? link : BASE_URL + link,
            title: storyLinksMap.get(link)
        };
    });
    
    console.log(`Found ${linksArray.length} stories to scrape.`);
    
    const browser = await puppeteer.launch({ 
        headless: "new",
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();
    const scrapedStories = [];

    for (let i = 0; i < linksArray.length; i++) {
        const item = linksArray[i];
        console.log(`[${i+1}/${linksArray.length}] Scraping ${item.title} -> ${item.url}`);
        
        try {
            await page.goto(item.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
            await new Promise(r => setTimeout(r, 2000)); // Small delay
            
            const pageContent = await page.content();
            const $page = cheerio.load(pageContent);
            
            let storyHtml = '';
            
            let container = $page('div[itemprop="articleBody"]');
            if (container.length === 0) container = $page('div.story-content');
            if (container.length === 0) container = $page('article');
            
            if (container.length > 0) {
                container.find('p, blockquote').each((_, el) => {
                    storyHtml += $page(el).text().trim() + '\n\n';
                });
            }
            
            // Clean up text
            const storyText = storyHtml.trim();
            
            if (storyText) {
                scrapedStories.push({
                    title: item.title,
                    url: item.url,
                    text: storyText
                });
            } else {
                console.log(`  -> Warning: No text found for ${item.url}`);
            }
        } catch (e) {
            console.error(`  -> Failed to scrape ${item.url}:`, e.message);
        }
        
        // Save intermediate results
        if ((i + 1) % 10 === 0) {
            fs.writeFileSync('stories.json', JSON.stringify(scrapedStories, null, 2));
        }
    }
    
    fs.writeFileSync('stories.json', JSON.stringify(scrapedStories, null, 2));
    console.log(`Completed. Saved ${scrapedStories.length} stories to stories.json.`);
    
    await browser.close();
}

main().catch(console.error);
