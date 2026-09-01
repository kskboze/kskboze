/* ============================================================
   カード画像の組み立て。並べ替えは print.js と同じ規則なので
   問題用紙・解答用紙・カードで記号がすべて一致する
   ============================================================ */
(function () {
  'use strict';

  var BANK = window.GOLF_QUIZ_QUESTIONS;
  var CATS = window.GOLF_QUIZ_CATEGORIES;
  var PENS = window.GOLF_QUIZ_PENALTIES;
  var FIGS = window.GOLF_FIGURES;

  var KEYS = ['ア', 'イ', 'ウ', 'エ'];

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function seedOf(id) {
    var h = 2166136261;
    for (var i = 0; i < id.length; i++) { h ^= id.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    return h;
  }
  function mix(s) {
    s = (s + 0x6D2B79F5) >>> 0;
    var t = Math.imul(s ^ (s >>> 15), s | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return { r: (t ^ (t >>> 14)) >>> 0, s: s };
  }
  function ordered(q) {
    var idx = [0, 1, 2, 3], s = seedOf(q.id);
    for (var i = idx.length - 1; i > 0; i--) {
      var m = mix(s); s = m.s;
      var j = Math.floor((m.r / 4294967296) * (i + 1));
      var t = idx[i]; idx[i] = idx[j]; idx[j] = t;
    }
    return idx;
  }

  function catName(id) {
    for (var i = 0; i < CATS.length; i++) if (CATS[i].id === id) return CATS[i].name;
    return id;
  }

  function card(q, opt) {
    var box = el('article', 'card');
    box.dataset.id = q.id;

    var head = el('div', 'card__head');
    head.appendChild(el('span', 'card__cat', catName(q.cat)));
    head.appendChild(el('span', 'card__rule', q.rule));
    head.appendChild(el('span', 'card__lv', '★'.repeat(q.level)));
    box.appendChild(head);

    box.appendChild(el('p', 'card__q', q.q));

    var ul = el('ul', 'card__c');
    ordered(q).forEach(function (ci, k) {
      var li = el('li');
      if (opt.answer && ci === 0) li.dataset.ok = '1';
      li.appendChild(el('span', 'card__k', KEYS[k]));
      li.appendChild(el('span', null, q.choices[ci]));
      ul.appendChild(li);
    });
    box.appendChild(ul);

    if (opt.fig && q.fig && FIGS.has(q.fig)) {
      var fig = FIGS.render(q.fig);
      if (!opt.answer) {                                 /* 説明文は答えを含むことがある */
        var cap = fig.querySelector('.fig__cap');
        if (cap) { var t = cap.querySelector('b'); cap.textContent = ''; if (t) cap.appendChild(t); }
      }
      box.appendChild(fig);
    }

    if (opt.answer) {
      var a = el('p', 'card__ans');
      a.appendChild(el('b', null, '答 ' + KEYS[ordered(q).indexOf(0)] + '　'));
      a.appendChild(document.createTextNode(q.why));
      box.appendChild(a);
    }

    var foot = el('div', 'card__foot');
    var p = PENS[q.pen] || PENS.info;
    foot.appendChild(el('span', 'pen pen--' + p.tone, p.label));
    foot.appendChild(el('span', null, 'ゴルフ規則2023年版'));
    box.appendChild(foot);

    return box;
  }

  /* ?ids=x001,x002 / ?cats=bunker / ?must=1 / ?levels=1,2 / ?limit=20 / ?answer=1 / ?fig=0 */
  function pick() {
    var qs = new URLSearchParams(location.search);
    var ids = qs.get('ids');
    if (ids) {
      var want = ids.split(',');
      return BANK.filter(function (q) { return want.indexOf(q.id) !== -1; });
    }
    var cats = qs.get('cats') ? qs.get('cats').split(',') : null;
    var levels = qs.get('levels') ? qs.get('levels').split(',').map(Number) : null;
    var must = qs.get('must') === '1';
    var out = BANK.filter(function (q) {
      return (!cats || cats.indexOf(q.cat) !== -1)
        && (!levels || levels.indexOf(q.level) !== -1)
        && (!must || q.must);
    });
    var lim = Number(qs.get('limit') || 24);
    if (lim > 0 && out.length > lim) {
      var step = out.length / lim, picked = [];
      for (var i = 0; i < lim; i++) picked.push(out[Math.floor(i * step)]);
      out = picked;
    }
    return out;
  }

  var qs = new URLSearchParams(location.search);
  var opt = { answer: qs.get('answer') === '1', fig: qs.get('fig') !== '0' };
  var list = pick();
  var grid = document.getElementById('cards');
  list.forEach(function (q) { grid.appendChild(card(q, opt)); });
  document.getElementById('cd-count').textContent = list.length + '枚';
})();
