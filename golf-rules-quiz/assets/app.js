(function () {
  'use strict';

  var BANK = window.GOLF_QUIZ_QUESTIONS;
  var CATS = window.GOLF_QUIZ_CATEGORIES;
  var BANDS = window.GOLF_QUIZ_BANDS;
  var PENS = window.GOLF_QUIZ_PENALTIES;
  var ROLES = window.GOLF_QUIZ_ROLES;
  var FIGS = window.GOLF_FIGURES;

  var CAT_BY_ID = {};
  CATS.forEach(function (c) { CAT_BY_ID[c.id] = c; });

  var STORE_KEY = 'golfRulesScorecard.v2';
  var PASS_RATE = 0.7;
  var COUNT_OPTIONS = [10, 20, 30, 50, 100, 0];
  var KEYS = ['A', 'B', 'C', 'D'];

  var MODES = [
    { id: 'practice', name: '練習ラウンド', sub: '1問ごとに正解と解説' },
    { id: 'exam',     name: 'テストラウンド', sub: '最後にまとめて採点' }
  ];

  var $ = function (id) { return document.getElementById(id); };

  /* ── 保存された記録 ────────────────────────────── */

  function loadStore() {
    var empty = { rounds: [], wrong: [], seen: [] };
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (!raw) return empty;
      var data = JSON.parse(raw);
      return {
        rounds: Array.isArray(data.rounds) ? data.rounds : [],
        wrong: Array.isArray(data.wrong) ? data.wrong : [],
        seen: Array.isArray(data.seen) ? data.seen : []
      };
    } catch (e) {
      return empty;
    }
  }

  function saveStore(data) {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(data)); } catch (e) { /* 保存できない環境でも動作は継続 */ }
  }

  var store = loadStore();

  /* ── 状態 ──────────────────────────────────────── */

  var setup = { mode: 'practice', cats: CATS.map(function (c) { return c.id; }), count: 20, levels: [1,2,3], must: false };
  var run = null;
  var timerId = null;

  /* ── 小道具 ────────────────────────────────────── */

  function shuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  function pct(n, d) { return d ? Math.round((n / d) * 100) : 0; }

  function clockText(ms) {
    var s = Math.floor(ms / 1000);
    return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
  }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function pool() {
    return BANK.filter(function (q) {
      if (setup.cats.indexOf(q.cat) === -1) return false;
      if (setup.levels.indexOf(q.level) === -1) return false;
      if (setup.must && !q.must) return false;
      return true;
    });
  }

  /* テストの型 — 押すと範囲・難易度・問題数がまとめて決まる */
  var PRESETS = [
    { id: 'must',   name: '必修テスト',   sub: 'これだけは知っておきたい',
      apply: function () { setup.cats = CATS.map(function (c) { return c.id; }); setup.levels = [1,2,3]; setup.must = true;  setup.count = 0;  } },
    { id: 'easy',   name: '初級',         sub: '難易度★ の基本問題',
      apply: function () { setup.cats = CATS.map(function (c) { return c.id; }); setup.levels = [1];     setup.must = false; setup.count = 0;  } },
    { id: 'mid',    name: '中級',         sub: '難易度★★ 実務でよく出会う',
      apply: function () { setup.cats = CATS.map(function (c) { return c.id; }); setup.levels = [2];     setup.must = false; setup.count = 20; } },
    { id: 'hard',   name: '上級',         sub: '難易度★★★ 判断に迷う場面',
      apply: function () { setup.cats = CATS.map(function (c) { return c.id; }); setup.levels = [3];     setup.must = false; setup.count = 20; } },
    { id: 'random', name: 'ランダム',     sub: '全範囲からまんべんなく',
      apply: function () { setup.cats = CATS.map(function (c) { return c.id; }); setup.levels = [1,2,3]; setup.must = false; setup.count = 20; } },
    { id: 'full',   name: '総合テスト',   sub: '全問に挑戦',
      apply: function () { setup.cats = CATS.map(function (c) { return c.id; }); setup.levels = [1,2,3]; setup.must = false; setup.count = 0;  } }
  ];

  function presetMatches(p) {
    var before = JSON.stringify([setup.cats.slice().sort(), setup.levels.slice().sort(), setup.must, setup.count]);
    var snap = { cats: setup.cats.slice(), levels: setup.levels.slice(), must: setup.must, count: setup.count };
    p.apply();
    var after = JSON.stringify([setup.cats.slice().sort(), setup.levels.slice().sort(), setup.must, setup.count]);
    setup.cats = snap.cats; setup.levels = snap.levels; setup.must = snap.must; setup.count = snap.count;
    return before === after;
  }

  function presetCount(p) {
    var snap = { cats: setup.cats.slice(), levels: setup.levels.slice(), must: setup.must, count: setup.count };
    p.apply();
    var n = pool().length;
    setup.cats = snap.cats; setup.levels = snap.levels; setup.must = snap.must; setup.count = snap.count;
    return n;
  }

  function refreshHome() {
    renderPresetChips(); renderRoleChips(); renderCatChips();
    renderLevelChips(); renderCountChips();
  }

  function renderPresetChips() {
    var box = $('preset-chips');
    box.textContent = '';
    PRESETS.forEach(function (p) {
      var b = el('button', 'chip chip--wide');
      b.type = 'button';
      b.setAttribute('aria-pressed', String(presetMatches(p)));
      b.appendChild(el('span', null, p.name));
      b.appendChild(el('span', 'chip__sub', p.sub + ' · ' + presetCount(p) + '問'));
      b.addEventListener('click', function () { p.apply(); refreshHome(); });
      box.appendChild(b);
    });
  }

  function renderLevelChips() {
    var box = $('level-chips');
    box.textContent = '';
    [{ n: 1, label: '★ 初級' }, { n: 2, label: '★★ 中級' }, { n: 3, label: '★★★ 上級' }].forEach(function (L) {
      var n = BANK.filter(function (q) { return q.level === L.n && setup.cats.indexOf(q.cat) !== -1; }).length;
      var b = el('button', 'chip chip--sm');
      b.type = 'button';
      b.setAttribute('aria-pressed', String(setup.levels.indexOf(L.n) !== -1));
      b.appendChild(el('span', null, L.label));
      b.appendChild(el('span', 'chip__n', n));
      b.addEventListener('click', function () {
        var i = setup.levels.indexOf(L.n);
        if (i === -1) setup.levels.push(L.n);
        else if (setup.levels.length > 1) setup.levels.splice(i, 1);
        refreshHome();
      });
      box.appendChild(b);
    });

    var mb = el('button', 'chip chip--sm');
    mb.type = 'button';
    mb.setAttribute('aria-pressed', String(setup.must));
    mb.appendChild(el('span', null, '必修のみ'));
    mb.appendChild(el('span', 'chip__n', BANK.filter(function (q) { return q.must; }).length));
    mb.addEventListener('click', function () { setup.must = !setup.must; refreshHome(); });
    box.appendChild(mb);
  }

  function show(name) {
    ['home', 'quiz', 'result'].forEach(function (s) { $('screen-' + s).hidden = (s !== name); });
    window.scrollTo({ top: 0, behavior: 'auto' });
  }

  function penTag(code) {
    var p = PENS[code] || PENS.info;
    var s = el('span', 'pen pen--' + p.tone);
    s.appendChild(el('span', null, p.label));
    return s;
  }

  /* 解説ブロック(理由 / その後の処置 / 補足 / 図解)を組み立てる */
  function buildExplanation(q, opts) {
    var box = el('div', 'expl');

    var why = el('div', 'expl__block');
    why.appendChild(el('div', 'expl__label', 'なぜそうなるか'));
    why.appendChild(el('p', 'expl__text', q.why));
    box.appendChild(why);

    if (q.next && q.next.length) {
      var nx = el('div', 'expl__block');
      nx.appendChild(el('div', 'expl__label', 'その後の処置'));
      var ol = el('ol', 'steps');
      q.next.forEach(function (step) { ol.appendChild(el('li', null, step)); });
      nx.appendChild(ol);
      box.appendChild(nx);
    }

    if (q.note) {
      var nt = el('div', 'expl__block');
      nt.appendChild(el('div', 'expl__label', '補足'));
      nt.appendChild(el('p', 'expl__note', q.note));
      box.appendChild(nt);
    }

    if (q.fig && FIGS.has(q.fig) && (!opts || opts.figure !== false)) {
      var fg = el('div', 'expl__block');
      fg.appendChild(el('div', 'expl__label', '図解'));
      fg.appendChild(FIGS.render(q.fig));
      box.appendChild(fg);
    }

    return box;
  }

  /* ── ホーム画面の組み立て ──────────────────────── */

  function renderModeChips() {
    var box = $('mode-chips');
    box.textContent = '';
    MODES.forEach(function (m) {
      var b = el('button', 'chip chip--wide');
      b.type = 'button';
      b.setAttribute('aria-pressed', String(setup.mode === m.id));
      b.appendChild(el('span', null, m.name));
      b.appendChild(el('span', 'chip__sub', m.sub));
      b.addEventListener('click', function () { setup.mode = m.id; renderModeChips(); });
      box.appendChild(b);
    });
  }

  function renderRoleChips() {
    var box = $('role-chips');
    box.textContent = '';

    ROLES.forEach(function (r) {
      var n = BANK.filter(function (q) { return r.cats.indexOf(q.cat) !== -1; }).length;
      // 現在の選択がちょうどこの役割の範囲と一致しているか
      var on = r.cats.length === setup.cats.length &&
               r.cats.every(function (c) { return setup.cats.indexOf(c) !== -1; });
      var b = el('button', 'chip chip--wide');
      b.type = 'button';
      b.setAttribute('aria-pressed', String(on));
      b.appendChild(el('span', null, r.name));
      b.appendChild(el('span', 'chip__sub', r.note + ' · ' + n + '問'));
      b.addEventListener('click', function () {
        setup.cats = r.cats.slice();
        refreshHome();
      });
      box.appendChild(b);
    });

    var all = el('button', 'chip chip--wide');
    all.type = 'button';
    all.setAttribute('aria-pressed', String(setup.cats.length === CATS.length));
    all.appendChild(el('span', null, 'すべて'));
    all.appendChild(el('span', 'chip__sub', '規則1〜25の全範囲 · ' + BANK.length + '問'));
    all.addEventListener('click', function () {
      setup.cats = CATS.map(function (c) { return c.id; });
      refreshHome();
    });
    box.appendChild(all);
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
          if (allOn && i !== -1) setup.cats.splice(i, 1);
          if (!allOn && i === -1) setup.cats.push(c.id);
        });
        refreshHome();
      });
      head.appendChild(tog);
      sec.appendChild(head);

      var chips = el('div', 'chips');
      inBand.forEach(function (c) {
        var n = BANK.filter(function (q) { return q.cat === c.id; }).length;
        var b = el('button', 'chip chip--sm');
        b.type = 'button';
        b.setAttribute('aria-pressed', String(setup.cats.indexOf(c.id) !== -1));
        b.appendChild(el('span', null, c.name));
        b.appendChild(el('span', 'chip__n', n));
        b.addEventListener('click', function () {
          var i = setup.cats.indexOf(c.id);
          if (i === -1) setup.cats.push(c.id); else setup.cats.splice(i, 1);
          refreshHome();
        });
        chips.appendChild(b);
      });
      sec.appendChild(chips);
      box.appendChild(sec);
    });
  }

  function renderCountChips() {
    var avail = pool().length;
    var box = $('count-chips');
    box.textContent = '';

    if (COUNT_OPTIONS.indexOf(setup.count) === -1) setup.count = 20;

    COUNT_OPTIONS.forEach(function (n) {
      var usable = n === 0 ? avail > 0 : n <= avail;
      var b = el('button', 'chip chip--num');
      b.type = 'button';
      b.textContent = n === 0 ? 'すべて' : n + '問';
      b.disabled = !usable;
      b.style.opacity = usable ? '' : '.35';
      b.setAttribute('aria-pressed', String(setup.count === n && usable));
      b.addEventListener('click', function () { setup.count = n; renderCountChips(); });
      box.appendChild(b);
    });

    $('pool-hint').textContent = '選択中の範囲に ' + avail + ' 問';
    $('start-btn').disabled = avail === 0;

    if (setup.count !== 0 && setup.count > avail) {
      var fit = COUNT_OPTIONS.filter(function (n) { return n !== 0 && n <= avail; }).pop();
      setup.count = fit || 0;
      renderCountChips();
    }
  }

  function renderRecord() {
    var known = {};
    BANK.forEach(function (q) { known[q.id] = true; });
    store.wrong = store.wrong.filter(function (id) { return known[id]; });
    store.seen = store.seen.filter(function (id) { return known[id]; });

    var wrongN = store.wrong.length;
    $('wrong-count').textContent = wrongN;
    $('wrong-btn').hidden = wrongN === 0;

    var rounds = store.rounds;
    $('record').hidden = rounds.length === 0;
    if (!rounds.length) return;

    var best = rounds.reduce(function (m, r) { return Math.max(m, pct(r.got, r.of)); }, 0);
    var last = rounds[rounds.length - 1];

    $('rec-rounds').textContent = rounds.length;
    $('rec-best').textContent = best + '%';
    $('rec-last').textContent = last.got + '/' + last.of;
    $('rec-seen').textContent = store.seen.length + '/' + BANK.length;
  }

  /* ── ラウンドの準備 ────────────────────────────── */

  function prepare(list, mode, scopeLabel) {
    run = {
      mode: mode,
      scope: scopeLabel,
      items: list.map(function (q) {
        var order = shuffle([0, 1, 2, 3]);
        return {
          q: q,
          order: order,                 // 表示位置 → 元の選択肢index
          correctAt: order.indexOf(0),  // choices[0] が常に正解
          picked: null
        };
      }),
      at: 0,
      startedAt: Date.now(),
      endedAt: null
    };
    show('quiz');
    startTimer();
    renderQuestion();
  }

  function startRound() {
    var list = shuffle(pool());
    var n = setup.count === 0 ? list.length : Math.min(setup.count, list.length);
    var names = setup.must ? '必修'
      : setup.cats.length === CATS.length ? '全範囲'
      : setup.cats.map(function (id) { return CAT_BY_ID[id].short; }).join('・');
    if (setup.levels.length < 3) names += ' / ' + setup.levels.map(function (n) { return '★'.repeat(n); }).join('・');
    prepare(list.slice(0, n), setup.mode, names);
  }

  function startWrongRound() {
    var ids = {};
    store.wrong.forEach(function (id) { ids[id] = true; });
    var list = shuffle(BANK.filter(function (q) { return ids[q.id]; }));
    if (!list.length) return;
    prepare(list, 'practice', '復習');
  }

  /* ── タイマー ──────────────────────────────────── */

  function startTimer() {
    stopTimer();
    timerId = setInterval(function () {
      $('quiz-timer').textContent = clockText(Date.now() - run.startedAt);
    }, 1000);
    $('quiz-timer').textContent = '00:00';
  }

  function stopTimer() {
    if (timerId) { clearInterval(timerId); timerId = null; }
  }

  /* ── スコアカード帯 ────────────────────────────── */

  function markClass(item) {
    if (item.picked === null) return 'mark mark--todo';
    return item.picked === item.correctAt ? 'mark mark--good' : 'mark mark--bad';
  }

  function renderStrip(node, opts) {
    node.textContent = '';
    run.items.forEach(function (item, i) {
      var cell = el('button', 'card-strip__cell');
      cell.type = 'button';
      cell.appendChild(el('span', 'card-strip__n', i + 1));
      // ○=正解 / □=不正解 — スコアカードの記法。形は CSS の枠線で描く
      var m = el('span', markClass(item), item.picked === null ? '·' : '');
      cell.appendChild(m);
      if (opts.current === i) cell.setAttribute('aria-current', 'true');
      cell.setAttribute('aria-label', (i + 1) + '問目');
      if (opts.onPick) cell.addEventListener('click', function () { opts.onPick(i); });
      else cell.disabled = true;
      node.appendChild(cell);
    });
  }

  /* ── 出題 ──────────────────────────────────────── */

  function renderQuestion() {
    var item = run.items[run.at];
    var q = item.q;
    var answered = item.picked !== null;
    var reveal = answered && run.mode === 'practice';

    $('quiz-mode').textContent = run.mode === 'practice' ? '練習ラウンド' : 'テストラウンド';
    $('quiz-scope').textContent = run.scope;
    $('quiz-pos').textContent = run.at + 1;
    $('quiz-total').textContent = run.items.length;

    renderStrip($('quiz-strip'), {
      current: run.at,
      onPick: function (i) { run.at = i; renderQuestion(); }
    });

    $('q-cat').textContent = CAT_BY_ID[q.cat].name;
    $('q-rule').textContent = q.rule;

    var lv = $('q-level');
    lv.textContent = '';
    for (var i = 1; i <= 3; i++) {
      lv.appendChild(el('span', 'level__pip' + (i <= q.level ? ' level__pip--on' : '')));
    }
    lv.setAttribute('aria-label', '難易度 ' + q.level + ' / 3');

    $('q-text').textContent = q.q;

    var box = $('q-choices');
    box.textContent = '';
    item.order.forEach(function (origIdx, pos) {
      var b = el('button', 'choice');
      b.type = 'button';
      b.appendChild(el('span', 'choice__key', KEYS[pos]));
      b.appendChild(el('span', null, q.choices[origIdx]));
      b.setAttribute('aria-pressed', String(item.picked === pos));

      if (reveal) {
        b.disabled = true;
        if (pos === item.correctAt) b.dataset.verdict = 'good';
        else if (pos === item.picked) b.dataset.verdict = 'bad';
      } else {
        b.addEventListener('click', function () { pick(pos); });
      }
      box.appendChild(b);
    });

    var vd = $('q-verdict');
    vd.textContent = '';
    if (reveal) {
      var ok = item.picked === item.correctAt;
      vd.hidden = false;

      var head = el('div', 'verdict__head ' + (ok ? 'verdict__head--good' : 'verdict__head--bad'));
      head.appendChild(el('span', null, ok ? '正解' : '不正解'));
      head.appendChild(penTag(q.pen));
      head.appendChild(el('span', 'verdict__ref', q.rule));
      vd.appendChild(head);

      var pinfo = PENS[q.pen] || PENS.info;
      if (pinfo.note) vd.appendChild(el('p', 'expl__text', pinfo.note));

      vd.appendChild(buildExplanation(q));
    } else {
      vd.hidden = true;
    }

    var next = $('next-btn');
    next.disabled = !answered;
    next.firstChild.textContent = run.at === run.items.length - 1 ? '採点する ' : '次の問題 ';
  }

  function pick(pos) {
    var item = run.items[run.at];
    if (run.mode === 'practice' && item.picked !== null) return;
    item.picked = pos;
    renderQuestion();
  }

  function advance() {
    if (run.items[run.at].picked === null) return;
    if (run.at < run.items.length - 1) {
      run.at++;
      renderQuestion();
    } else {
      finish();
    }
  }

  /* ── 採点 ──────────────────────────────────────── */

  function finish() {
    stopTimer();
    run.endedAt = Date.now();

    var got = 0;
    var wrongSet = {};
    store.wrong.forEach(function (id) { wrongSet[id] = true; });
    var seenSet = {};
    store.seen.forEach(function (id) { seenSet[id] = true; });

    run.items.forEach(function (item) {
      var ok = item.picked === item.correctAt;
      if (ok) { got++; delete wrongSet[item.q.id]; } else { wrongSet[item.q.id] = true; }
      seenSet[item.q.id] = true;
    });

    store.wrong = Object.keys(wrongSet);
    store.seen = Object.keys(seenSet);
    store.rounds.push({
      at: Date.now(), mode: run.mode, got: got, of: run.items.length,
      ms: run.endedAt - run.startedAt
    });
    if (store.rounds.length > 50) store.rounds = store.rounds.slice(-50);
    saveStore(store);

    renderResult(got);
    show('result');
  }

  function renderResult(got) {
    var of = run.items.length;
    var rate = pct(got, of);
    var passed = got / of >= PASS_RATE;

    $('res-got').textContent = got;
    $('res-of').textContent = of;

    var badge = $('res-badge');
    badge.className = 'grade__badge ' + (passed ? 'grade__badge--pass' : 'grade__badge--fail');
    badge.textContent = passed ? '合格' : '不合格';

    $('res-line').textContent = passed
      ? '正答率 ' + rate + '%。規則の勘どころは押さえられています。間違えた問題は、その後の処置まで読み直しておきましょう。'
      : '正答率 ' + rate + '%(合格は70%以上)。下の見直しで、罰の区分とその後の処置を確認しましょう。';

    var meta = $('res-meta');
    meta.textContent = '';
    meta.appendChild(el('div', null, run.mode === 'practice' ? '練習ラウンド' : 'テストラウンド'));
    meta.appendChild(el('div', null, '範囲 ' + run.scope));
    meta.appendChild(el('div', null, '所要 ' + clockText(run.endedAt - run.startedAt)));

    renderStrip($('res-strip'), {
      current: -1,
      onPick: function (i) {
        var card = document.getElementById('rv-' + i);
        if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });

    renderBreakdown();
    renderReview(false);
    $('retry-wrong-btn').hidden = got === of;
  }

  function renderBreakdown() {
    var tally = {};
    run.items.forEach(function (item) {
      var c = item.q.cat;
      if (!tally[c]) tally[c] = { got: 0, of: 0 };
      tally[c].of++;
      if (item.picked === item.correctAt) tally[c].got++;
    });

    var box = $('res-breakdown');
    box.textContent = '';
    CATS.forEach(function (c) {
      var t = tally[c.id];
      if (!t) return;
      var rate = pct(t.got, t.of);
      var row = el('div', 'bd-row');
      row.appendChild(el('span', 'bd-row__name', c.name));
      var track = el('div', 'bd-row__track');
      var fill = el('div', 'bd-row__fill' + (rate < 50 ? ' bd-row__fill--low' : rate < 70 ? ' bd-row__fill--mid' : ''));
      fill.style.width = rate + '%';
      track.appendChild(fill);
      row.appendChild(track);
      row.appendChild(el('span', 'bd-row__num', t.got + '/' + t.of + '  ' + rate + '%'));
      box.appendChild(row);
    });
  }

  function renderReview(onlyWrong) {
    var box = $('res-review');
    box.textContent = '';

    run.items.forEach(function (item, i) {
      var ok = item.picked === item.correctAt;
      if (onlyWrong && ok) return;
      var q = item.q;

      var card = el('article', 'rv' + (ok ? '' : ' rv--bad'));
      card.id = 'rv-' + i;

      var head = el('div', 'rv__head');
      head.appendChild(el('span', null, String(i + 1).padStart(2, '0')));
      head.appendChild(el('span', null, CAT_BY_ID[q.cat].name));
      head.appendChild(el('span', null, q.rule));
      head.appendChild(penTag(q.pen));
      head.appendChild(el('span', ok ? 'mark mark--good' : 'mark mark--bad', ''));
      card.appendChild(head);

      card.appendChild(el('h3', 'rv__q', q.q));

      var lines = el('div', 'rv__lines');
      if (!ok) {
        var mine = el('div', 'rv__line');
        mine.appendChild(el('span', 'rv__tag', 'あなた'));
        mine.appendChild(el('span', 'rv__val--bad', q.choices[item.order[item.picked]]));
        lines.appendChild(mine);
      }
      var right = el('div', 'rv__line');
      right.appendChild(el('span', 'rv__tag', '正解'));
      right.appendChild(el('span', 'rv__val--good', q.choices[0]));
      lines.appendChild(right);
      card.appendChild(lines);

      var why = el('div', 'rv__why');
      // 見直しでは図解を省き、必要なら問題集で確認してもらう
      why.appendChild(buildExplanation(q, { figure: !ok }));
      card.appendChild(why);

      box.appendChild(card);
    });

    if (!box.children.length) {
      box.appendChild(el('p', 'footnote', '全問正解です。表示する間違いはありません。'));
    }
  }

  /* ── 操作 ──────────────────────────────────────── */

  $('start-btn').addEventListener('click', startRound);
  $('wrong-btn').addEventListener('click', startWrongRound);
  $('next-btn').addEventListener('click', advance);

  $('quit-btn').addEventListener('click', function () {
    stopTimer();
    run = null;
    renderRecord();
    show('home');
  });

  $('cat-all').addEventListener('click', function () {
    setup.cats = CATS.map(function (c) { return c.id; });
    refreshHome();
  });

  $('cat-none').addEventListener('click', function () {
    setup.cats = [];
    refreshHome();
  });

  $('rv-all').addEventListener('click', function () { renderReview(false); });
  $('rv-bad').addEventListener('click', function () { renderReview(true); });

  $('again-btn').addEventListener('click', function () {
    var same = run.items.map(function (item) { return item.q; });
    prepare(shuffle(same), run.mode, run.scope);
  });

  $('retry-wrong-btn').addEventListener('click', function () {
    var missed = run.items.filter(function (item) { return item.picked !== item.correctAt; })
                          .map(function (item) { return item.q; });
    if (!missed.length) return;
    prepare(shuffle(missed), 'practice', '復習');
  });

  $('home-btn').addEventListener('click', function () {
    run = null;
    renderRecord();
    show('home');
  });

  $('reset-record').addEventListener('click', function () {
    store = { rounds: [], wrong: [], seen: [] };
    saveStore(store);
    renderRecord();
  });

  document.addEventListener('keydown', function (e) {
    if ($('screen-quiz').hidden) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;

    var n = ['1', '2', '3', '4'].indexOf(e.key);
    if (n !== -1) { e.preventDefault(); pick(n); return; }

    if (e.key === 'Enter') {
      e.preventDefault();
      advance();
    } else if (e.key === 'ArrowLeft' && run.at > 0) {
      e.preventDefault();
      run.at--; renderQuestion();
    } else if (e.key === 'ArrowRight' && run.at < run.items.length - 1) {
      e.preventDefault();
      run.at++; renderQuestion();
    }
  });

  /* ── 起動 ──────────────────────────────────────── */

  $('bank-total').textContent = BANK.length;
  renderModeChips();
  refreshHome();
  renderRecord();
  show('home');
})();
