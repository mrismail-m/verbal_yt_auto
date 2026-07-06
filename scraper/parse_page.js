const fs = require('fs');
const cheerio = require('cheerio');

const content = fs.readFileSync('page.html', 'utf8');
const $ = cheerio.load(content);

const links = [];
$('a').each((i, el) => {
    const href = $(el).attr('href');
    const text = $(el).text().trim();
    if (href && href.startsWith('/childrens-stories/')) {
        links.push({ href, text });
    }
});

console.log(JSON.stringify(links, null, 2));
console.log(`Total children's stories links found: ${links.length}`);
