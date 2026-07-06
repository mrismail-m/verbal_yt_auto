const fs = require('fs');
const cheerio = require('cheerio');

const content = fs.readFileSync('page.html', 'utf8');
const $ = cheerio.load(content);

const links = [];
$('a').each((i, el) => {
    const href = $(el).attr('href');
    const text = $(el).text().trim();
    if (href && text && href.split('/').length > 2 && !href.includes('css') && !href.includes('js') && !href.startsWith('http')) {
        links.push({ href, text });
    }
});
fs.writeFileSync('all_links.json', JSON.stringify(links, null, 2));
console.log('Written to all_links.json');
