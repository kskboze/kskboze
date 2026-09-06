// ============================================================
// app.js — ブラウザ側の動きを担当するファイル
//   ① 画面の部品を取得する
//   ② ボタンが押されたらサーバー（/api/generate）に質問を送る
//   ③ 返ってきた答えを画面に表示する
// ============================================================

// ------------------------------------------------------------
// ① 画面の部品を取得
// ------------------------------------------------------------
const form = document.getElementById('form');
const input = document.getElementById('input');
const inputLabel = document.getElementById('input-label');
const submit = document.getElementById('submit');
const submitText = submit.querySelector('.submit-text');
const statusBox = document.getElementById('status');
const resultBox = document.getElementById('result');
const formulaBox = document.getElementById('formula');
const explanationBox = document.getElementById('explanation');
const partsWrap = document.getElementById('parts-wrap');
const partsList = document.getElementById('parts');
const notesWrap = document.getElementById('notes-wrap');
const notesBox = document.getElementById('notes');
const copyButton = document.getElementById('copy');
const examplesBox = document.getElementById('examples');

let mode = 'generate'; // "generate"（数式をつくる）か "explain"（解説する）

// ------------------------------------------------------------
// モードごとの表示文言と入力例
// ------------------------------------------------------------
const MODE_TEXTS = {
  generate: {
    label: 'やりたいことを日本語で書いてください',
    placeholder: '例：B列の売上を合計して、消費税10%込みの金額を円未満切り捨てで出したい',
    button: '数式をつくる',
    examples: [
      'A1の日付を「令和7年4月1日」の形で表示したい',
      'A1の日付が何年度か知りたい（4月始まり）',
      'B列の税抜金額に消費税10%を足して、円未満は切り捨てたい',
      '氏名（姓と名がスペース区切り）から姓だけを取り出したい',
      '商品コードで別シートの単価表を検索したい',
      'A1の日付から5営業日後の日付を出したい',
    ],
  },
  explain: {
    label: '解説してほしい数式を貼り付けてください',
    placeholder: '例：=IFERROR(VLOOKUP(A2,商品マスタ!A:C,3,FALSE),"該当なし")',
    button: '解説してもらう',
    examples: [
      '=TEXT(A1,"ggge年m月d日")',
      '=YEAR(EDATE(A1,-3))',
      '=IFERROR(VLOOKUP(A2,商品マスタ!A:C,3,FALSE),"該当なし")',
      '=SUMIFS(C:C,A:A,">="&E1,A:A,"<="&E2)',
    ],
  },
};

// ------------------------------------------------------------
// 入力例のボタンを並べ直す
// ------------------------------------------------------------
function renderExamples() {
  // ラベル（「例をクリック:」）だけ残して、いったん中身を消す
  examplesBox.querySelectorAll('.chip').forEach((chip) => chip.remove());

  for (const example of MODE_TEXTS[mode].examples) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'chip';
    chip.textContent = example.length > 26 ? example.slice(0, 25) + '…' : example;
    chip.title = example;
    chip.addEventListener('click', () => {
      input.value = example;
      input.focus();
    });
    examplesBox.appendChild(chip);
  }
}

// ------------------------------------------------------------
// モード切り替え
// ------------------------------------------------------------
document.querySelectorAll('.mode').forEach((button) => {
  button.addEventListener('click', () => {
    mode = button.dataset.mode;

    document.querySelectorAll('.mode').forEach((other) => {
      const active = other === button;
      other.classList.toggle('is-active', active);
      other.setAttribute('aria-selected', String(active));
    });

    const texts = MODE_TEXTS[mode];
    inputLabel.textContent = texts.label;
    input.placeholder = texts.placeholder;
    submitText.textContent = texts.button;

    input.value = '';
    resultBox.hidden = true;
    statusBox.hidden = true;
    renderExamples();
  });
});

// ------------------------------------------------------------
// 状態メッセージの表示
// ------------------------------------------------------------
function showStatus(message, isError = false) {
  statusBox.textContent = message;
  statusBox.classList.toggle('is-error', isError);
  statusBox.hidden = false;
}

// ------------------------------------------------------------
// ② 送信 → ③ 表示
// ------------------------------------------------------------
form.addEventListener('submit', async (event) => {
  event.preventDefault();

  const text = input.value.trim();
  if (!text) {
    showStatus('まずは入力欄に書いてみてください。', true);
    return;
  }

  const target = form.querySelector('input[name="target"]:checked').value;

  submit.disabled = true;
  resultBox.hidden = true;
  showStatus('考えています… 少しお待ちください。');

  try {
    const response = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, target, text }),
    });

    const data = await response.json();

    if (!response.ok) {
      showStatus(data.error || 'うまくいきませんでした。もう一度おためしください。', true);
      return;
    }

    statusBox.hidden = true;
    render(data);
  } catch {
    showStatus('通信に失敗しました。サーバーが起動しているか確認してください。', true);
  } finally {
    submit.disabled = false;
  }
});

// Ctrl / ⌘ + Enter でも送信できるようにする
input.addEventListener('keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
    form.requestSubmit();
  }
});

// ------------------------------------------------------------
// 結果を画面に描く
// ------------------------------------------------------------
function render(data) {
  formulaBox.textContent = data.formula || '（数式は生成されませんでした）';
  explanationBox.textContent = data.explanation || '';

  // 部品ごとの説明
  partsList.textContent = '';
  const parts = Array.isArray(data.parts) ? data.parts : [];

  for (const part of parts) {
    const row = document.createElement('div');
    const dt = document.createElement('dt');
    const dd = document.createElement('dd');
    dt.textContent = part.code || '';
    dd.textContent = part.meaning || '';
    row.append(dt, dd);
    partsList.appendChild(row);
  }
  partsWrap.hidden = parts.length === 0;

  // 注意点
  const notes = (data.notes || '').trim();
  notesBox.textContent = notes;
  notesWrap.hidden = notes === '';

  resultBox.hidden = false;
  resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ------------------------------------------------------------
// コピーボタン
// ------------------------------------------------------------
copyButton.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(formulaBox.textContent);
    copyButton.textContent = 'コピーしました';
  } catch {
    copyButton.textContent = 'コピーできませんでした';
  }
  setTimeout(() => { copyButton.textContent = 'コピー'; }, 1600);
});

// ------------------------------------------------------------
// ④ 早見表（AIを使わずに動く部分）
// ------------------------------------------------------------
const RECIPES = [
  {
    title: '和暦で表示する',
    code: '=TEXT(A1,"ggge年m月d日")',
    note: '「令和7年4月1日」の形になります。"ge" なら「R7」。',
  },
  {
    title: '年度を出す（4月始まり）',
    code: '=YEAR(EDATE(A1,-3))',
    note: '日付を3か月戻してから年を取ることで、日本の会計年度になります。',
  },
  {
    title: '曜日を出す',
    code: '=TEXT(A1,"aaa")',
    note: '「月」のように1文字で。"aaaa" なら「月曜日」。',
  },
  {
    title: '消費税10%込み（円未満切り捨て）',
    code: '=ROUNDDOWN(A1*1.1,0)',
    note: '軽減税率8%なら 1.08。端数処理は社内ルールに合わせてください。',
  },
  {
    title: '税込から税抜に戻す',
    code: '=ROUNDDOWN(A1/1.1,0)',
    note: '割り戻しは1円ずれやすいので、端数処理の指定が大切です。',
  },
  {
    title: '全角を半角にそろえる',
    code: '=ASC(TRIM(A1))',
    note: '住所や電話番号の名寄せ前に。逆に全角化は JIS 関数です。',
  },
  {
    title: '姓だけを取り出す',
    code: '=LEFT(A1,FIND(" ",ASC(A1))-1)',
    note: 'ASC を挟むと、全角スペース区切りでも取り出せます。',
  },
  {
    title: '郵便番号にハイフンを入れる',
    code: '=LEFT(A1,3)&"-"&RIGHT(A1,4)',
    note: '7桁の数字が文字列として入っている前提です。',
  },
  {
    title: '5営業日後の日付',
    code: '=WORKDAY(A1,5,祝日一覧)',
    note: '日本の祝日は自動判定されません。祝日一覧の範囲を用意してください。',
  },
  {
    title: '見つからない時に空欄にする',
    code: '=IFERROR(VLOOKUP(A2,マスタ!A:C,3,FALSE),"")',
    note: 'IFERROR で包むと #N/A が表に出ません。',
  },
];

const cheatsheet = document.getElementById('cheatsheet');

for (const recipe of RECIPES) {
  const card = document.createElement('div');
  card.className = 'recipe';

  const heading = document.createElement('h3');
  heading.textContent = recipe.title;

  const code = document.createElement('code');
  code.textContent = recipe.code;

  const note = document.createElement('p');
  note.textContent = recipe.note;

  card.append(heading, code, note);
  cheatsheet.appendChild(card);
}

// 起動時に入力例を並べる
renderExamples();
