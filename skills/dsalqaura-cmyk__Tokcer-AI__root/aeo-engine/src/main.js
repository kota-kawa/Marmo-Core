import fs from 'fs-extra';
import path from 'path';
import axios from 'axios';
import dotenv from 'dotenv';
import { injectInternalLinks } from './linker.js';

dotenv.config();

const CONFIG_PATH = './config';
const INPUT_PATH = './inputs';
const OUTPUT_PATH = './outputs';
const BUDGET_FILE = path.join(CONFIG_PATH, 'token_budget.json');

// Helper to get or initialize daily token budget
async function getOrInitBudget() {
  const today = new Date().toISOString().split('T')[0];
  try {
    if (await fs.exists(BUDGET_FILE)) {
      const budget = await fs.readJson(BUDGET_FILE);
      if (budget.last_updated === today) {
        return budget;
      }
    }
  } catch (err) {
    // Ignore and recreate
  }
  
  const newBudget = { 
    last_updated: today, 
    tokens_used_today: 0, 
    daily_limit: 2048 
  };
  await fs.writeJson(BUDGET_FILE, newBudget, { spaces: 2 });
  return newBudget;
}

// Helper to update daily token budget after a successful API call
async function updateBudget(tokensUsed) {
  const budget = await getOrInitBudget();
  budget.tokens_used_today += tokensUsed;
  await fs.writeJson(BUDGET_FILE, budget, { spaces: 2 });
  console.log(`📊 [BUDGET GUARD] Penggunaan Token Harian: ${budget.tokens_used_today} / ${budget.daily_limit} (Terpakai Baru: +${tokensUsed})`);
}

// Helper to call AI API (OpenAI / DeepSeek Compatible / Gemini Free Tier)
async function callAI(prompt, systemPrompt = '') {
  const geminiKey = process.env.GEMINI_API_KEY || process.env.VITE_GEMINI_API_KEY;
  const apiKey = process.env.AI_API_KEY;
  const apiBase = process.env.AI_API_BASE || 'https://api.deepseek.com'; // Default ke DeepSeek
  const model = process.env.AI_MODEL || 'deepseek-chat';

  // 1. Check budget before making any API call
  const budget = await getOrInitBudget();
  if (budget.tokens_used_today >= budget.daily_limit) {
    console.warn(`⚠️ [BUDGET GUARD] Batas penggunaan harian ${budget.daily_limit} token telah tercapai (${budget.tokens_used_today} terpakai). Eksekusi AI dibatalkan demi hemat biaya.`);
    return null;
  }

  // Jika ada Gemini Key, gunakan Gemini 1.5 Flash (Rp 0,- Free Tier)
  if (geminiKey && geminiKey !== 'your_api_key_here') {
    try {
      console.log(`🤖 [Gemini 1.5 Flash] Menggunakan model Gemini Free Tier (Rp 0)...`);
      const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${geminiKey}`;
      
      // Menggabungkan system prompt ke dalam content
      const fullText = systemPrompt ? `${systemPrompt}\n\nUSER PROMPT:\n${prompt}` : prompt;
      
      const response = await axios.post(url, {
        contents: [{
          parts: [{
            text: fullText
          }]
        }],
        generationConfig: {
          temperature: 0.2
        }
      }, {
        headers: { 'Content-Type': 'application/json' }
      });

      const content = response.data.candidates?.[0]?.content?.parts?.[0]?.text || null;
      // Estimasi token kasar (1 kata ≈ 1.3 token) untuk budget guard harian
      const wordCount = fullText.split(/\s+/).length + (content ? content.split(/\s+/).length : 0);
      const estimatedTokens = Math.ceil(wordCount * 1.3);
      
      if (estimatedTokens > 0) {
        await updateBudget(estimatedTokens);
      }
      return content;
    } catch (error) {
      const errorMsg = error.response?.data?.error?.message || error.message;
      console.error(`❌ [Gemini Error] Call Failed: ${errorMsg}`);
      console.log(`🔄 Mengalihkan ke fallback DeepSeek/OpenAI...`);
    }
  }

  if (!apiKey || apiKey === 'your_api_key_here') {
    console.error('❌ [ERROR] AI_API_KEY atau GEMINI_API_KEY belum diisi!');
    return null;
  }

  try {
    const response = await axios.post(`${apiBase}/chat/completions`, {
      model: model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: prompt }
      ],
      temperature: 0.2, // Low temperature for strictly stable and factual content
      max_tokens: 4000
    }, {
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      }
    });

    const content = response.data.choices?.[0]?.message?.content || null;
    const tokensUsed = response.data.usage?.total_tokens || 0;
    
    // 2. Update usage record
    if (tokensUsed > 0) {
      await updateBudget(tokensUsed);
    }

    return content;
  } catch (error) {
    const errorMsg = error.response?.data?.error?.message || error.message;
    console.error(`❌ [ERROR] AI Call Failed: ${errorMsg}`);
    return null;
  }
}

async function runPipeline() {
  console.log('🚀 [TOKCER AEO] Memulai Pipeline GEO Engine...');

  try {
    // 1. Load Knowledge & Keywords Map
    const brandVoice = await fs.readFile(path.join(CONFIG_PATH, 'brand_guidelines.md'), 'utf-8');
    const targetPersona = await fs.readFile(path.join(CONFIG_PATH, 'target_persona.md'), 'utf-8');
    
    let keywordMap = {};
    const keywordsPath = path.join(CONFIG_PATH, 'keywords_map.json');
    if (await fs.exists(keywordsPath)) {
      keywordMap = await fs.readJson(keywordsPath);
      console.log(`🔗 [Agent 4] Kamus kata kunci tautan internal berhasil dimuat (${Object.keys(keywordMap).length} kata kunci).`);
    } else {
      console.warn(`⚠️ [Agent 4] File ${keywordsPath} tidak ditemukan. Pengait internal dinonaktifkan.`);
    }

    // 2. Read Inputs
    const files = await fs.readdir(INPUT_PATH);
    const transcripts = files.filter(f => f.endsWith('.txt') || f.endsWith('.md'));

    if (transcripts.length === 0) {
      console.log('ℹ️ Tidak ada transkrip baru di folder /inputs. Masukkan file .txt untuk memulai.');
      return;
    }

    for (const file of transcripts) {
      console.log(`\n📄 Memproses: ${file}`);
      const transcriptContent = await fs.readFile(path.join(INPUT_PATH, file), 'utf-8');

      // -- PHASE A: STRATEGY --
      console.log('🧠 [Agent 1] Menyusun Strategi Angle...');
      const strategy = await callAI(
        `Analisalah transkrip berikut dan tentukan "Spin Angle" yang paling menarik untuk target persona. \n\nTRANSKRIP:\n${transcriptContent}`,
        `Kamu adalah Strategy Agent untuk Tokcer AI. Gunakan Brand Voice ini:\n${brandVoice}\n\nTarget Persona:\n${targetPersona}`
      );
      if (!strategy) continue;

      // -- PHASE B: GEO OPTIMIZATION --
      console.log('🔮 [Agent 2] Melakukan GEO Optimization...');
      const optimizedContent = await callAI(
        `Gunakan strategi ini: ${strategy}. \nBuatlah konten blog yang sangat dioptimasi untuk Generative Engine Optimization (GEO) agar dikutip oleh LLM. Pastikan kamu menambahkan format Q&A (Tanya-Jawab) yang sering dicari pengguna, serta menyisipkan "AI Markers" berwujud statistik data konkrit (misal: "mampu menurunkan HPP hingga 12.5%", "mempercepat ROI dalam 14 hari").`,
        `Kamu adalah GEO Optimizer untuk Tokcer AI. Pastikan tulisan terstruktur sangat logis, menggunakan format Q&A, memiliki poin-poin tebal (bold), dan data statistik yang berwibawa agar sangat diprioritaskan oleh sistem LLM Scraper.`
      );
      if (!optimizedContent) continue;

      // -- PHASE C: FINAL BLOG GENERATION --
      console.log('✍️ [Agent 3] Menghasilkan Artikel Final...');
      const finalBlog = await callAI(
        `Rapikan hasil optimasi ini menjadi blog post yang mewah dan siap terbit. Tambahkan meta description dan slug. \n\nKONTEN:\n${optimizedContent}`,
        `Kamu adalah Blog Copywriter Tokcer AI. Gunakan format Markdown yang rapi.`
      );
      if (!finalBlog) continue;

      // -- PHASE D: PROGRAMMATIC INTERNAL LINKING --
      console.log('🔗 [Agent 4] Menyuntikkan Tautan Internal secara cerdas...');
      const blogWithLinks = injectInternalLinks(finalBlog, keywordMap);

      // 3. Save Results
      const outputFileName = `GEO_${file}`;
      await fs.writeFile(path.join(OUTPUT_PATH, outputFileName), blogWithLinks);
      console.log(`✅ BERHASIL! Hasil disimpan ke: /outputs/${outputFileName}`);
    }

    console.log('\n✨ [DONE] Seluruh proses pipeline selesai.');
  } catch (err) {
    console.error('❌ [CRITICAL ERROR] Pipeline gagal:', err.message);
  }
}

runPipeline();
