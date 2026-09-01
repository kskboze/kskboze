/* ============================================================
   印刷用ページ — 問題用紙 / 解答用紙 / 図解シート を組み立てる
   選択肢の並びは id から決めるので、問題用紙と解答用紙で必ず一致する
   ============================================================ */
(function () {
  'use strict';

  var BANK  = window.GOLF_QUIZ_QUESTIONS;
  var CATS  = window.GOLF_QUIZ_CATEGORIES;
  var BANDS = window.GOLF_QUIZ_BANDS;
  var PENS  = window.GOLF_QUIZ_PENALTIES;
  var FIGS  = window.GOLF_FIGURES;

  var KEYS = ['ア', 'イ', 'ウ', 'エ'];

  var $ = function (id) { return document.getElementById(id); };

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  /* ── 設定 ──────────────────────────────────────── */

  var setup = {
    sheet: 'quiz',                                    // quiz / key / figs
    cats: CATS.map(function (c) { return c.id; }),
    levels: [1, 2, 3],
    must: false,
    count: 30,
    cols: 2,
    withFig: true
  };

  /* ── 選択肢の並び ──────────────────────────────
     紙に刷ると答えを後から直せないので、並びは id から決める。
     同じ問題は何度刷っても同じ並びになり、解答用紙とずれない。 */

  /* FNV-1a。Math.imul を使って 32bit の掛け算をそのまま行う */
  function seedOf(id) {
    var h = 2166136261;
    for (var i = 0; i < id.length; i++) {
      h ^= id.charCodeAt(i);
      h = Math.imul(h, 16777619) >>> 0;
    }
    return h;
  }

  /* mulberry32。線形合同法の下位ビットは周期が短く偏るので使わない */
  function mix(s) {
    s = (s + 0x6D2B79F5) >>> 0;
    var t = Math.imul(s ^ (s >>> 15), s | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return { r: (t ^ (t >>> 14)) >>> 0, s: s };
  }

  function ordered(q) {
    var idx = [0, 1, 2, 3];
    var s = seedOf(q.id);
    for (var i = idx.length - 1; i > 0; i--) {
      var m = mix(s); s = m.s;
      var j = Math.floor((m.r / 4294967296) * (i + 1));   // 上位ビットから採る
      var t = idx[i]; idx[i] = idx[j]; idx[j] = t;
    }
    return idx;                                       // 表示順 → choices の添字
  }

  function answerKey(q) {
    var idx = ordered(q);
    return KEYS[idx.indexOf(0)];                      // choices[0] が常に正解
  }

  /* ── 出題範囲 ──────────────────────────────────── */

  function pool() {
    return BANK.filter(function (q) {
      return setup.cats.indexOf(q.cat) !== -1
        && setup.levels.indexOf(q.level) !== -1
        && (!setup.must || q.must);
    });
  }

  /* 章の並び順のまま、必要数だけ均等に間引く。
     ばらばらに抜くより、章ごとにまとまっていたほうが紙では読みやすい */
  function selection() {
    var p = pool();
    var order = {};
    CATS.forEach(function (c, i) { order[c.id] = i; });
    p.sort(function (a, b) {
      return (order[a.cat] - order[b.cat]) || (a.level - b.level) || (a.id < b.id ? -1 : 1);
    });
    if (!setup.count || setup.count >= p.length) return p;
    var out = [], step = p.length / setup.count;
    for (var i = 0; i < setup.count; i++) out.push(p[Math.floor(i * step)]);
    return out;
  }

  function catName(id) {
    for (var i = 0; i < CATS.length; i++) if (CATS[i].id === id) return CATS[i].name;
    return id;
  }

  /* ── 紙面 ──────────────────────────────────────── */

  function sheetHead(title, meta, withName) {
    var h = el('div', 'sheethead');
    h.appendChild(el('h2', 'sheethead__title', title));
    h.appendChild(el('span', 'sheethead__meta', meta));
    if (withName) h.appendChild(el('span', 'sheethead__name', '氏名'));
    return h;
  }

  function buildQuiz(list, body) {
    list.forEach(function (q, n) {
      var box = el('article', 'pq');

      var head = el('div', 'pq__head');
      head.appendChild(el('span', 'pq__no', '問' + (n + 1)));
      head.appendChild(el('span', 'pq__tag',
        catName(q.cat) + ' / ' + '★'.repeat(q.level) + (q.must ? ' / 必修' : '')));
      box.appendChild(head);

      box.appendChild(el('p', 'pq__q', q.q));

      var ul = el('ul', 'pq__c');
      ordered(q).forEach(function (ci, k) {
        var li = el('li');
        li.appendChild(el('span', 'pq__k', KEYS[k]));
        li.appendChild(document.createTextNode(q.choices[ci]));
        ul.appendChild(li);
      });
      box.appendChild(ul);

      /* 図解のキャプションは答えそのものを書いていることがある。
         問題用紙では図と見出しだけ残し、説明文は落とす */
      if (setup.withFig && q.fig && FIGS.has(q.fig)) {
        var fig = FIGS.render(q.fig);
        var cap = fig.querySelector('.fig__cap');
        if (cap) {
          var title = cap.querySelector('b');
          cap.textContent = '';
          if (title) cap.appendChild(title);
        }
        box.appendChild(fig);
      }

      var b = el('div', 'pq__box', '解答');
      b.appendChild(el('i'));
      box.appendChild(b);

      body.appendChild(box);
    });
  }

  function buildKey(list, body) {
    list.forEach(function (q, n) {
      var box = el('article', 'pa');

      var head = el('div', 'pa__head');
      head.appendChild(el('span', 'pa__no', '問' + (n + 1)));
      head.appendChild(el('span', 'pa__ans', answerKey(q)));
      head.appendChild(el('span', 'pa__pen', (PENS[q.pen] || PENS.info).label));
      head.appendChild(el('span', 'pa__rule', q.rule));
      box.appendChild(head);

      box.appendChild(el('p', 'pa__q', q.q));
      box.appendChild(el('p', 'pa__why', q.why));

      if (q.next && q.next.length) {
        var ol = el('ol', 'pa__next');
        q.next.forEach(function (s) { ol.appendChild(el('li', null, s)); });
        box.appendChild(ol);
      }
      if (q.note) box.appendChild(el('p', 'pa__why', q.note));

      body.appendChild(box);
    });
  }

  function buildFigs(body) {
    body.appendChild(el('div', 'figsheet'));
    var wrap = body.lastChild;
    Object.keys(FIGS.all).forEach(function (id) { wrap.appendChild(FIGS.render(id)); });
  }

  function render() {
    var paper = $('paper');
    paper.textContent = '';

    if (setup.sheet === 'figs') {
      paper.appendChild(sheetHead('ゴルフ規則 図解シート',
        Object.keys(FIGS.all).length + '点 / ゴルフ規則2023年版', false));
      var fb = el('div', 'sheetbody');
      fb.dataset.cols = '1';
      buildFigs(fb);
      paper.appendChild(fb);
      $('sel-hint').textContent = '図解 ' + Object.keys(FIGS.all).length + '点';
      return;
    }

    var list = selection();
    var meta = list.length + '問 / ゴルフ規則2023年版' + (setup.must ? ' / 必修' : '');
    paper.appendChild(sheetHead(
      setup.sheet === 'quiz' ? 'ゴルフ規則 確認テスト' : 'ゴルフ規則 確認テスト  解答と解説',
      meta, setup.sheet === 'quiz'));

    var body = el('div', 'sheetbody');
    body.dataset.cols = String(setup.cols);
    if (setup.sheet === 'quiz') buildQuiz(list, body); else buildKey(list, body);
    paper.appendChild(body);

    $('sel-hint').textContent = '該当 ' + pool().length + '問 → 出力 ' + list.length + '問';
  }

  /* ── 設定 UI ───────────────────────────────────── */

  function renderSheetPick() {
    var box = $('sheet-chips');
    box.textContent = '';
    [
      { id: 'quiz', name: '問題用紙', sub: '設問と選択肢だけ。解答欄つき。配って使う' },
      { id: 'key',  name: '解答用紙', sub: '正解・罰の区分・条文・理由・その後の処置' },
      { id: 'figs', name: '図解シート', sub: '図解だけを並べる。掲示や研修資料に' }
    ].forEach(function (s) {
      var b = el('button', 'sheet');
      b.type = 'button';
      b.setAttribute('aria-pressed', String(setup.sheet === s.id));
      b.appendChild(el('span', 'sheet__name', s.name));
      b.appendChild(el('span', 'sheet__sub', s.sub));
      b.addEventListener('click', function () { setup.sheet = s.id; refresh(); });
      box.appendChild(b);
    });
    $('range-fields').hidden = setup.sheet === 'figs';
  }

  function chipRow(box, items, isOn, onPick) {
    box.textContent = '';
    items.forEach(function (it) {
      var b = el('button', 'chip');
      b.type = 'button';
      b.setAttribute('aria-pressed', String(isOn(it)));
      b.appendChild(el('span', null, it.name));
      if (it.sub) b.appendChild(el('span', 'chip__sub', it.sub));
      b.addEventListener('click', function () { onPick(it); refresh(); });
      box.appendChild(b);
    });
  }

  function renderCatChips() {
    var box = $('cat-chips');
    box.textContent = '';
    BANDS.forEach(function (band) {
      var inBand = CATS.filter(function (c) { return c.band === band.id; });
      if (!inBand.length) return;

      var sec = el('div', 'band');
      var head = el('div', 'band__head');
      head.appendChild(el('span', 'band__name', band.name));
      head.appendChild(el('span', 'band__rules', band.note));

      var allOn = inBand.every(function (c) { return setup.cats.indexOf(c.id) !== -1; });
      var tog = el('button', 'band__toggle', allOn ? 'この部を外す' : 'この部を選ぶ');
      tog.type = 'button';
      tog.addEventListener('click', function () {
        inBand.forEach(function (c) {
          var i = setup.cats.indexOf(c.id);
          if (allOn) { if (i !== -1) setup.cats.splice(i, 1); }
          else if (i === -1) setup.cats.push(c.id);
        });
        refresh();
      });
      head.appendChild(tog);
      sec.appendChild(head);

      var row = el('div', 'chips');
      inBand.forEach(function (c) {
        var n = BANK.filter(function (q) { return q.cat === c.id; }).length;
        var b = el('button', 'chip');
        b.type = 'button';
        b.setAttribute('aria-pressed', String(setup.cats.indexOf(c.id) !== -1));
        b.appendChild(el('span', null, c.name));
        b.appendChild(el('span', 'chip__sub', n + '問'));
        b.addEventListener('click', function () {
          var i = setup.cats.indexOf(c.id);
          if (i === -1) setup.cats.push(c.id); else setup.cats.splice(i, 1);
          refresh();
        });
        row.appendChild(b);
      });
      sec.appendChild(row);
      box.appendChild(sec);
    });
  }

  function refresh() {
    renderSheetPick();
    renderCatChips();
    chipRow($('level-chips'),
      [{ id: 1, name: '★' }, { id: 2, name: '★★' }, { id: 3, name: '★★★' }],
      function (it) { return setup.levels.indexOf(it.id) !== -1; },
      function (it) {
        var i = setup.levels.indexOf(it.id);
        if (i === -1) setup.levels.push(it.id);
        else if (setup.levels.length > 1) setup.levels.splice(i, 1);
      });
    chipRow($('must-chips'),
      [{ id: false, name: 'すべて' }, { id: true, name: '必修のみ' }],
      function (it) { return setup.must === it.id; },
      function (it) { setup.must = it.id; });
    chipRow($('count-chips'),
      [{ id: 10, name: '10問' }, { id: 20, name: '20問' }, { id: 30, name: '30問' },
       { id: 50, name: '50問' }, { id: 100, name: '100問' }, { id: 0, name: 'すべて' }],
      function (it) { return setup.count === it.id; },
      function (it) { setup.count = it.id; });
    chipRow($('cols-chips'),
      [{ id: 1, name: '1段組み' }, { id: 2, name: '2段組み' }],
      function (it) { return setup.cols === it.id; },
      function (it) { setup.cols = it.id; });
    chipRow($('fig-chips'),
      [{ id: true, name: '図解を入れる' }, { id: false, name: '図解を省く' }],
      function (it) { return setup.withFig === it.id; },
      function (it) { setup.withFig = it.id; });
    render();
  }

  /* ── URL から設定を読む ────────────────────────
     ?sheet=key&cats=bunker,green&levels=1,2&must=1&count=50&cols=1&fig=0
     PDF の自動生成にも、特定の紙面をブックマークするのにも使う */

  function applyQuery() {
    var qs = new URLSearchParams(location.search);
    if (!qs.toString()) return;

    var known = CATS.map(function (c) { return c.id; });
    var v;

    if ((v = qs.get('sheet')) && ['quiz', 'key', 'figs'].indexOf(v) !== -1) setup.sheet = v;

    if ((v = qs.get('cats'))) {
      var picked = v.split(',').filter(function (c) { return known.indexOf(c) !== -1; });
      if (picked.length) setup.cats = picked;
    }
    if ((v = qs.get('levels'))) {
      var lv = v.split(',').map(Number).filter(function (n) { return n >= 1 && n <= 3; });
      if (lv.length) setup.levels = lv;
    }
    if ((v = qs.get('must')) != null) setup.must = v === '1';
    if ((v = qs.get('count')) != null && /^\d+$/.test(v)) setup.count = Number(v);
    if ((v = qs.get('cols')) != null) setup.cols = v === '1' ? 1 : 2;
    if ((v = qs.get('fig')) != null) setup.withFig = v !== '0';
  }

  $('print-btn').addEventListener('click', function () { window.print(); });

  applyQuery();
  refresh();
})();
