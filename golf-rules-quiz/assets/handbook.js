(function () {
  'use strict';

  var BANK = window.GOLF_QUIZ_QUESTIONS;
  var CATS = window.GOLF_QUIZ_CATEGORIES;
  var BANDS = window.GOLF_QUIZ_BANDS;
  var PENS = window.GOLF_QUIZ_PENALTIES;
  var FIGS = window.GOLF_FIGURES;

  var KEYS = ['A', 'B', 'C', 'D'];
  var STORE_KEY = 'golfRulesHandbook.v1';

  var $ = function (id) { return document.getElementById(id); };

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function penTag(code) {
    var p = PENS[code] || PENS.info;
    return el('span', 'pen pen--' + p.tone, p.label);
  }

  /* 表示設定は端末ごとの好みなので localStorage に置く */
  function loadPrefs() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (raw) {
        var d = JSON.parse(raw);
        return { answers: d.answers === 'hide' ? 'hide' : 'show', pen: d.pen || 'all' };
      }
    } catch (e) { /* 読めなければ既定値 */ }
    return { answers: 'show', pen: 'all' };
  }
  function savePrefs() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(prefs)); } catch (e) { /* 保存できなくても動作は継続 */ }
  }

  var prefs = loadPrefs();
  var query = '';

  /* ── 図解を該当箇所に差し込む ──────────────────── */

  function mountFigures() {
    Object.keys(FIGS.all).forEach(function (id) {
      var slot = $('fig-' + id);
      if (slot) slot.appendChild(FIGS.render(id));
    });
  }

  /* ── 目次 ──────────────────────────────────────── */

  function buildToc() {
    var toc = el('div', 'toc');

    var top = el('div', 'toc__band');
    top.appendChild(el('div', 'toc__bandname', 'まとめ'));
    [['sec-penalties', '罰の体系'], ['sec-relief', '救済の型']].forEach(function (pair) {
      var a = el('a', 'toc__link');
      a.href = '#' + pair[0];
      a.appendChild(el('span', null, pair[1]));
      top.appendChild(a);
    });
    toc.appendChild(top);

    BANDS.forEach(function (band) {
      var inBand = CATS.filter(function (c) { return c.band === band.id; });
      if (!inBand.length) return;
      var sec = el('div', 'toc__band');
      sec.appendChild(el('div', 'toc__bandname', band.name));
      inBand.forEach(function (c) {
        var n = BANK.filter(function (q) { return q.cat === c.id; }).length;
        var a = el('a', 'toc__link');
        a.href = '#chap-' + c.id;
        a.dataset.cat = c.id;
        a.appendChild(el('span', null, c.name));
        a.appendChild(el('span', 'toc__n', n));
        sec.appendChild(a);
      });
      toc.appendChild(sec);
    });

    $('hb-toc').textContent = '';
    $('hb-toc').appendChild(toc);
  }

  /* ── 絞り込みチップ ────────────────────────────── */

  function buildFilters() {
    var box = $('hb-penfilter');
    box.textContent = '';

    var opts = [{ id: 'all', label: 'すべて' }];
    Object.keys(PENS).forEach(function (k) { opts.push({ id: k, label: PENS[k].label }); });

    opts.forEach(function (o) {
      var n = o.id === 'all' ? BANK.length : BANK.filter(function (q) { return q.pen === o.id; }).length;
      if (n === 0) return;
      var b = el('button', 'chip chip--sm');
      b.type = 'button';
      b.setAttribute('aria-pressed', String(prefs.pen === o.id));
      b.appendChild(el('span', null, o.label));
      b.appendChild(el('span', 'chip__n', n));
      b.addEventListener('click', function () {
        prefs.pen = o.id; savePrefs(); buildFilters(); applyFilter();
      });
      box.appendChild(b);
    });

    var am = $('hb-answermode');
    am.textContent = '';
    [{ id: 'show', label: '解答と解説を表示' }, { id: 'hide', label: '隠して問題だけ' }].forEach(function (o) {
      var b = el('button', 'chip chip--sm');
      b.type = 'button';
      b.setAttribute('aria-pressed', String(prefs.answers === o.id));
      b.textContent = o.label;
      b.addEventListener('click', function () {
        prefs.answers = o.id; savePrefs(); buildFilters(); applyAnswerMode();
      });
      am.appendChild(b);
    });
  }

  /* ── 1問のカード ───────────────────────────────── */

  function buildQuestion(q, index) {
    var card = el('article', 'qa');
    card.id = 'q-' + q.id;
    card.dataset.pen = q.pen;
    card.dataset.text = [
      q.q, q.rule, q.why, q.note || '', (q.next || []).join(' '), q.choices.join(' ')
    ].join(' ');

    var head = el('div', 'qa__head');
    head.appendChild(el('span', 'qa__no', String(index).padStart(3, '0')));
    head.appendChild(el('span', null, q.rule));
    head.appendChild(penTag(q.pen));
    var lv = el('span', 'qa__level');
    lv.setAttribute('aria-label', '難易度 ' + q.level + ' / 3');
    for (var i = 1; i <= 3; i++) {
      lv.appendChild(el('span', 'level__pip' + (i <= q.level ? ' level__pip--on' : '')));
    }
    head.appendChild(lv);
    card.appendChild(head);

    var body = el('div', 'qa__body');
    body.appendChild(el('h3', 'qa__q', q.q));

    // 問題集では選択肢の順を固定する(紙の問題集と同じように読めるように)
    var ol = el('ul', 'opts');
    q.choices.forEach(function (c, i) {
      var li = el('li', i === 0 ? 'is-correct' : null);
      li.appendChild(el('span', 'opts__key', KEYS[i]));
      li.appendChild(el('span', null, c));
      ol.appendChild(li);
    });
    body.appendChild(ol);

    var reveal = el('button', 'qa__reveal', '解答と解説を見る');
    reveal.type = 'button';
    reveal.addEventListener('click', function () { card.dataset.answers = 'show'; });
    body.appendChild(reveal);

    var ans = el('div', 'qa__answer');
    var corr = el('p', 'qa__correct');
    corr.appendChild(el('b', null, '正解'));
    corr.appendChild(el('span', null, 'A — ' + q.choices[0]));
    ans.appendChild(corr);

    var pinfo = PENS[q.pen] || PENS.info;
    var penLine = el('p', 'qa__correct');
    penLine.appendChild(el('b', null, '罰'));
    var pw = el('span', null, '');
    pw.style.color = 'inherit';
    pw.style.fontWeight = '400';
    pw.textContent = pinfo.label + ' — ' + pinfo.note;
    penLine.appendChild(pw);
    ans.appendChild(penLine);

    ans.appendChild(buildExplanation(q));
    body.appendChild(ans);

    card.appendChild(body);
    card.dataset.answers = prefs.answers;
    return card;
  }

  function buildExplanation(q) {
    var box = el('div', 'expl');

    var why = el('div', 'expl__block');
    why.appendChild(el('div', 'expl__label', 'なぜそうなるか'));
    why.appendChild(el('p', 'expl__text', q.why));
    box.appendChild(why);

    if (q.next && q.next.length) {
      var nx = el('div', 'expl__block');
      nx.appendChild(el('div', 'expl__label', 'その後の処置'));
      var ol = el('ol', 'steps');
      q.next.forEach(function (s) { ol.appendChild(el('li', null, s)); });
      nx.appendChild(ol);
      box.appendChild(nx);
    }

    if (q.note) {
      var nt = el('div', 'expl__block');
      nt.appendChild(el('div', 'expl__label', '補足'));
      nt.appendChild(el('p', 'expl__note', q.note));
      box.appendChild(nt);
    }

    if (q.fig && FIGS.has(q.fig)) {
      var fg = el('div', 'expl__block');
      fg.appendChild(el('div', 'expl__label', '図解'));
      fg.appendChild(FIGS.render(q.fig));
      box.appendChild(fg);
    }

    return box;
  }

  /* ── 章の組み立て ──────────────────────────────── */

  function buildBody() {
    var body = $('hb-body');
    body.textContent = '';
    var n = 0;

    BANDS.forEach(function (band) {
      CATS.filter(function (c) { return c.band === band.id; }).forEach(function (cat) {
        var qs = BANK.filter(function (q) { return q.cat === cat.id; });
        if (!qs.length) return;

        var chap = el('section', 'chap');
        chap.id = 'chap-' + cat.id;
        chap.dataset.cat = cat.id;

        var head = el('div', 'chap__head');
        head.appendChild(el('span', 'chap__band', band.name));
        head.appendChild(el('h2', 'chap__name', cat.name));
        head.appendChild(el('span', 'chap__rules', cat.rules));
        head.appendChild(el('span', 'chap__n', qs.length + '問'));
        chap.appendChild(head);

        qs.forEach(function (q) { n++; chap.appendChild(buildQuestion(q, n)); });
        body.appendChild(chap);
      });
    });

    body.appendChild(el('div', 'hb__empty', '該当する問題がありません。検索語や絞り込みを変えてみてください。')).hidden = true;
  }

  /* ── 絞り込みと検索 ────────────────────────────── */

  function applyFilter() {
    var q = query.trim().toLowerCase();
    var hits = 0;

    document.querySelectorAll('.qa').forEach(function (card) {
      var okPen = prefs.pen === 'all' || card.dataset.pen === prefs.pen;
      var okText = !q || card.dataset.text.toLowerCase().indexOf(q) !== -1;
      var on = okPen && okText;
      card.hidden = !on;
      if (on) hits++;
    });

    document.querySelectorAll('.chap').forEach(function (chap) {
      var any = chap.querySelector('.qa:not([hidden])');
      chap.hidden = !any;
    });

    document.querySelectorAll('.toc__link[data-cat]').forEach(function (a) {
      var chap = document.getElementById('chap-' + a.dataset.cat);
      a.style.opacity = (chap && !chap.hidden) ? '' : '.35';
    });

    var empty = document.querySelector('.hb__empty');
    if (empty) empty.hidden = hits > 0;

    $('hb-hits').textContent = (q || prefs.pen !== 'all')
      ? hits + ' / ' + BANK.length + ' 問'
      : BANK.length + ' 問';
  }

  function applyAnswerMode() {
    document.querySelectorAll('.qa').forEach(function (card) { card.dataset.answers = prefs.answers; });
  }

  /* ── 目次の現在地 ──────────────────────────────── */

  function watchScroll() {
    var links = Array.prototype.slice.call(document.querySelectorAll('.toc__link[data-cat]'));
    if (!links.length || !('IntersectionObserver' in window)) return;

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        var id = e.target.dataset.cat;
        links.forEach(function (a) {
          a.setAttribute('aria-current', String(a.dataset.cat === id));
        });
      });
    }, { rootMargin: '-10% 0px -80% 0px' });

    document.querySelectorAll('.chap').forEach(function (c) { io.observe(c); });
  }

  /* ── 起動 ──────────────────────────────────────── */

  $('hb-total').textContent = BANK.length;
  mountFigures();
  buildToc();
  buildFilters();
  buildBody();
  applyFilter();
  watchScroll();

  var searchTimer = null;
  $('hb-search').addEventListener('input', function (e) {
    query = e.target.value;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(applyFilter, 120);
  });

  var top = $('hb-top');
  top.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });
  window.addEventListener('scroll', function () {
    top.classList.toggle('is-on', window.scrollY > 600);
  }, { passive: true });
})();
