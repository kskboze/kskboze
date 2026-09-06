// ============================================================
// server.js
//   このアプリの「サーバー」です。役割は2つだけ。
//     1. public フォルダの中身（画面）をブラウザに渡す
//     2. 画面から届いた質問を Claude（AI）に転送して、答えを返す
//
//   外部ライブラリは一切使っていません（npm install 不要）。
//   起動:  node server.js
// ============================================================

const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { buildSystemPrompt } = require('./prompt.js');

const PORT = Number(process.env.PORT) || 3000;
const MODEL = process.env.ANTHROPIC_MODEL || 'claude-sonnet-5';
const PUBLIC_DIR = path.join(__dirname, 'public');

// ------------------------------------------------------------
// .env ファイルがあれば読み込む（APIキーをコードに直接書かないため）
// ------------------------------------------------------------
function loadDotEnv() {
  const envPath = path.join(__dirname, '.env');
  if (!fs.existsSync(envPath)) return;

  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    const eq = trimmed.indexOf('=');
    if (eq === -1) continue;

    const key = trimmed.slice(0, eq).trim();
    // 前後のクォートは外しておく
    const value = trimmed.slice(eq + 1).trim().replace(/^["']|["']$/g, '');
    if (!process.env[key]) process.env[key] = value;
  }
}
loadDotEnv();

// ------------------------------------------------------------
// 画面ファイル（HTML / CSS / JS）を返すための準備
// ------------------------------------------------------------
const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
};

function sendJson(res, status, data) {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
  });
  res.end(body);
}

function serveStatic(req, res) {
  // "/" でアクセスされたら index.html を返す
  const urlPath = req.url === '/' ? '/index.html' : req.url.split('?')[0];

  // 「../」などで public の外に出られないように、必ず public 配下に閉じ込める
  const filePath = path.join(PUBLIC_DIR, path.normalize(urlPath));
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403).end('Forbidden');
    return;
  }

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('ページが見つかりませんでした');
      return;
    }
    const type = MIME_TYPES[path.extname(filePath)] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': type });
    res.end(content);
  });
}

// ------------------------------------------------------------
// リクエストの本文（JSON）を読み取る
// ------------------------------------------------------------
function readBody(req, limitBytes = 100_000) {
  return new Promise((resolve, reject) => {
    let raw = '';
    req.on('data', (chunk) => {
      raw += chunk;
      if (raw.length > limitBytes) {
        reject(new Error('入力が長すぎます'));
        req.destroy();
      }
    });
    req.on('end', () => {
      try {
        resolve(raw ? JSON.parse(raw) : {});
      } catch {
        reject(new Error('リクエストの形式が正しくありません'));
      }
    });
    req.on('error', reject);
  });
}

// ------------------------------------------------------------
// AI の返事（JSON文字列）を、安全にオブジェクトへ変換する
//   AI が前後によけいな文章を付けてしまった場合にも耐えられるようにしています。
// ------------------------------------------------------------
function parseAiJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    const start = text.indexOf('{');
    const end = text.lastIndexOf('}');
    if (start !== -1 && end > start) {
      try {
        return JSON.parse(text.slice(start, end + 1));
      } catch {
        /* 下の fallback にまわす */
      }
    }
  }
  // どうしても JSON として読めなかったときは、本文をそのまま説明として見せる
  return { formula: '', explanation: text, parts: [], notes: '' };
}

// ------------------------------------------------------------
// Claude API を呼ぶ
// ------------------------------------------------------------
async function askClaude({ mode, target, text }) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    const err = new Error(
      'APIキーが設定されていません。.env.example を .env にコピーして、ANTHROPIC_API_KEY を書いてください。'
    );
    err.status = 503;
    throw err;
  }

  const userMessage =
    mode === 'explain'
      ? `次の数式を、初心者にも分かるように解説してください。\n\n${text}`
      : `次のやりたいことを実現する数式を作ってください。\n\n${text}`;

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: 2000,
      system: buildSystemPrompt(mode, target),
      messages: [
        { role: 'user', content: userMessage },
        // ↓ AI の返事を「{」から始めさせることで、JSON で返ってきやすくする小技です
        { role: 'assistant', content: '{' },
      ],
    }),
  });

  if (!response.ok) {
    const detail = await response.text();
    const err = new Error(`AIの呼び出しに失敗しました（${response.status}）: ${detail.slice(0, 300)}`);
    err.status = 502;
    throw err;
  }

  const data = await response.json();
  const body = (data.content || [])
    .filter((block) => block.type === 'text')
    .map((block) => block.text)
    .join('');

  // 上の小技で「{」を先に書かせているので、その分を戻してから読み取ります
  return parseAiJson('{' + body);
}

// ------------------------------------------------------------
// サーバー本体
// ------------------------------------------------------------
const server = http.createServer(async (req, res) => {
  if (req.method === 'POST' && req.url === '/api/generate') {
    try {
      const { mode = 'generate', target = 'excel', text = '' } = await readBody(req);

      if (typeof text !== 'string' || !text.trim()) {
        sendJson(res, 400, { error: 'やりたいことを入力してください。' });
        return;
      }
      if (mode !== 'generate' && mode !== 'explain') {
        sendJson(res, 400, { error: 'モードの指定が正しくありません。' });
        return;
      }

      const result = await askClaude({ mode, target, text: text.trim() });
      sendJson(res, 200, result);
    } catch (error) {
      console.error(error);
      sendJson(res, error.status || 500, { error: error.message });
    }
    return;
  }

  if (req.method === 'GET') {
    serveStatic(req, res);
    return;
  }

  res.writeHead(405, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('このリクエストには対応していません');
});

server.listen(PORT, () => {
  console.log('');
  console.log('  関数ボット（日本語版）が起動しました 🎉');
  console.log(`  ブラウザで http://localhost:${PORT} を開いてください`);
  console.log('');
  if (!process.env.ANTHROPIC_API_KEY) {
    console.log('  ⚠ ANTHROPIC_API_KEY がまだ設定されていません。');
    console.log('    .env.example を .env にコピーして、キーを書き込んでください。');
    console.log('    （キーが無くても画面と使い方サンプルは確認できます）');
    console.log('');
  }
});
