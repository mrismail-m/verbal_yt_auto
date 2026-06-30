import fs from 'fs';
import path from 'path';
import { bundle } from '@remotion/bundler';
import { getCompositions, renderMedia } from '@remotion/renderer';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DATA_FILE = path.resolve(__dirname, '../verbal_mcqs.json');
const OUT_DIR = path.resolve(__dirname, './out');

function pickQuestions(data, count) {
  const unused = data.filter(q => !q.used);
  const picked = [];
  
  // Group unused by subcategory
  const byCategory = {};
  for (const q of unused) {
    if (!byCategory[q.subcategory]) {
      byCategory[q.subcategory] = [];
    }
    byCategory[q.subcategory].push(q);
  }

  // To rotate through categories
  const categories = Object.keys(byCategory);
  if (categories.length === 0) return [];
  
  let currentCatIndex = 0;
  
  while (picked.length < count && Object.values(byCategory).some(arr => arr.length > 0)) {
    let attempts = 0;
    while (attempts < categories.length) {
      const cat = categories[currentCatIndex];
      if (byCategory[cat] && byCategory[cat].length > 0) {
        const selected = byCategory[cat].shift();
        picked.push(selected);
        currentCatIndex = (currentCatIndex + 1) % categories.length;
        break; // found one, break out of attempts loop
      }
      currentCatIndex = (currentCatIndex + 1) % categories.length;
      attempts++;
    }
  }

  return picked;
}

async function main() {
  if (!fs.existsSync(OUT_DIR)) {
    fs.mkdirSync(OUT_DIR);
  }

  const rawData = fs.readFileSync(DATA_FILE, 'utf-8');
  let data = JSON.parse(rawData);

  const pickedQuestions = pickQuestions(data, 15);

  if (pickedQuestions.length === 0) {
    console.log("No unused questions found.");
    return;
  }

  console.log(`Picked ${pickedQuestions.length} questions. Building Remotion project...`);

  // Bundle the project
  const bundleLocation = await bundle({
    entryPoint: path.resolve(__dirname, './src/index.ts'),
    webpackOverride: (config) => config,
  });

  console.log("Bundle created at", bundleLocation);

  const inputProps = {
    questions: pickedQuestions.map(q => ({
      question: q.question,
      option_a: q.option_a,
      option_b: q.option_b,
      option_c: q.option_c,
      option_d: q.option_d,
      correct_option: q.correct_option.toLowerCase(),
    }))
  };

  console.log(`Rendering single quiz video with ${pickedQuestions.length} questions...`);

  const compositions = await getCompositions(bundleLocation, {
    inputProps,
  });

  const composition = compositions.find((c) => c.id === 'Quiz');

  if (!composition) {
    throw new Error("No composition with the ID Quiz found.");
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const outputLocation = path.join(OUT_DIR, `quiz-${timestamp}.mp4`);

  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: 'h264',
    outputLocation,
    inputProps,
  });

  console.log(`Rendered ${outputLocation}`);
  
  // Try to upload
  try {
    const { uploadVideo } = await import('./upload.mjs');
    await uploadVideo(outputLocation, pickedQuestions);
  } catch (err) {
    console.log("Skipping upload due to error or missing credentials:", err.message);
  }

  // Mark as used
  for (const q of pickedQuestions) {
    const idx = data.findIndex(item => item.id === q.id);
    if (idx !== -1) {
      data[idx].used = true;
    }
  }

  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
  console.log(`Updated ${DATA_FILE} with used status.`);
}

main().catch(console.error);
