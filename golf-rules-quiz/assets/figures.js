/* 図解ライブラリ
 * 救済の手続きは本質的に空間的なので、手順を図で示す。
 * 色は CSS カスタムプロパティ経由で受け取り、線と文字は currentColor に任せる
 * (ライト/ダークどちらのテーマでも読める)。
 * marker の id は図ごとに接尾辞を付けて衝突を避ける。
 */

window.GOLF_FIGURES = (function () {

  function arrowDefs(id, color) {
    return '<defs><marker id="ar-' + id + '" viewBox="0 0 10 10" refX="9" refY="5" ' +
      'markerWidth="6" markerHeight="6" orient="auto-start-reverse">' +
      '<path d="M0 0 L10 5 L0 10 z" fill="' + (color || 'currentColor') + '"/></marker></defs>';
  }

  // 旗つきのホール
  function hole(x, y) {
    return '<g class="fig-hole">' +
      '<line x1="' + x + '" y1="' + y + '" x2="' + x + '" y2="' + (y - 46) + '" stroke="currentColor" stroke-width="1.5"/>' +
      '<path d="M' + x + ' ' + (y - 46) + ' L' + (x + 26) + ' ' + (y - 38) + ' L' + x + ' ' + (y - 30) + ' z" fill="var(--fig-flag)"/>' +
      '<ellipse cx="' + x + '" cy="' + y + '" rx="7" ry="3.5" fill="var(--fig-holecup)" stroke="currentColor" stroke-width="1.2"/>' +
      '</g>';
  }

  function ball(x, y, label, dy) {
    var t = label ? '<text x="' + x + '" y="' + (y + (dy || -12)) + '" text-anchor="middle" class="fig-t">' + label + '</text>' : '';
    return '<circle cx="' + x + '" cy="' + y + '" r="6" fill="var(--fig-ball)" stroke="currentColor" stroke-width="1.6"/>' + t;
  }

  function figures() {
    return {

      /* ── コースの5つのエリア ─────────────────────── */
      'course-areas': {
        title: 'コースの5つのエリア',
        caption: 'コースは5つのエリアでできている。どのエリアに球があるかで、できることと救済の方法が変わる。',
        alt: 'ティーイングエリア、ジェネラルエリア、バンカー、ペナルティーエリア、パッティンググリーンの位置関係を示した1ホールの平面図',
        w: 640, h: 320,
        svg:
          arrowDefs('ca') +
          // ジェネラルエリア(地の面)
          '<rect x="8" y="8" width="624" height="304" rx="6" fill="var(--fig-general)" stroke="var(--fig-line)" stroke-width="1"/>' +
          '<text x="330" y="300" text-anchor="middle" class="fig-t fig-t--dim">ジェネラルエリア(上の4つ以外のすべて)</text>' +

          // OB杭(左上の境界)
          '<line x1="8" y1="34" x2="632" y2="34" stroke="var(--fig-line)" stroke-width="1" stroke-dasharray="2 6"/>' +
          '<circle cx="120" cy="34" r="3.5" fill="var(--fig-ob)"/><circle cx="300" cy="34" r="3.5" fill="var(--fig-ob)"/>' +
          '<circle cx="480" cy="34" r="3.5" fill="var(--fig-ob)"/>' +
          '<text x="600" y="26" text-anchor="end" class="fig-t fig-t--dim">白杭の外側はアウトオブバウンズ(コース外)</text>' +

          // ティーイングエリア
          '<rect x="26" y="132" width="74" height="56" rx="3" fill="var(--fig-tee)" stroke="currentColor" stroke-width="1.4"/>' +
          '<text x="63" y="208" text-anchor="middle" class="fig-t">ティーイングエリア</text>' +
          '<text x="63" y="222" text-anchor="middle" class="fig-t fig-t--dim">そのホールの出発点</text>' +

          // ペナルティーエリア(池)
          '<path d="M232 78 q46 -22 92 4 q34 20 22 62 q-14 48 -66 46 q-58 -2 -66 -46 q-8 -44 18 -66 z" ' +
          'fill="var(--fig-water)" stroke="var(--fig-penalty-r)" stroke-width="2"/>' +
          '<text x="288" y="152" text-anchor="middle" class="fig-t">ペナルティーエリア</text>' +
          '<text x="288" y="166" text-anchor="middle" class="fig-t fig-t--dim">黄 または 赤</text>' +

          // バンカー
          '<path d="M404 206 q40 -26 84 -6 q30 14 20 40 q-12 30 -56 28 q-48 -2 -56 -26 q-8 -22 8 -36 z" ' +
          'fill="var(--fig-sand)" stroke="currentColor" stroke-width="1.4"/>' +
          '<text x="452" y="290" text-anchor="middle" class="fig-t">バンカー</text>' +

          // パッティンググリーン
          '<ellipse cx="536" cy="140" rx="76" ry="60" fill="var(--fig-green)" stroke="currentColor" stroke-width="1.4"/>' +
          '<text x="536" y="222" text-anchor="middle" class="fig-t">パッティンググリーン</text>' +
          hole(536, 140)
      },

      /* ── 完全な救済のニヤレストポイント ──────────── */
      'nearest-point': {
        title: '罰なしの救済 — 救済エリアの決め方',
        caption: '動かせない障害物などからの罰なしの救済。① 完全な救済のニヤレストポイントを基点に決め、② そこから1クラブレングスの救済エリアにドロップする。ホールに近い側は救済エリアに入らない。',
        alt: 'カート道路上の球から、完全な救済のニヤレストポイントと1クラブレングスの救済エリアを求める手順の平面図',
        w: 700, h: 360,
        svg:
          arrowDefs('np') +
          '<rect x="8" y="8" width="684" height="344" rx="6" fill="var(--fig-general)" stroke="var(--fig-line)" stroke-width="1"/>' +

          // カート道路(動かせない障害物)
          '<rect x="300" y="8" width="70" height="344" fill="var(--fig-path)" stroke="currentColor" stroke-width="1.3"/>' +
          '<text x="335" y="30" text-anchor="middle" class="fig-t">カート道路</text>' +
          '<text x="335" y="44" text-anchor="middle" class="fig-t fig-t--dim">動かせない障害物</text>' +

          // 救済エリア = 基点から1クラブレングス、ホールに近づかない側(左半円)
          '<path d="M295 102 a88 88 0 0 0 0 176 z" fill="var(--fig-relief)" stroke="var(--fig-relief-line)" ' +
          'stroke-width="1.6" stroke-dasharray="5 4"/>' +
          '<text x="245" y="244" text-anchor="middle" class="fig-t">救済エリア</text>' +

          // ホールに近づかない限界線
          '<line x1="295" y1="100" x2="295" y2="282" stroke="var(--fig-accent)" stroke-width="1.6" stroke-dasharray="4 4"/>' +
          '<text x="288" y="92" text-anchor="end" class="fig-t" fill="var(--fig-accent)">この線よりホール側は使えない</text>' +

          // 1クラブレングスの計測
          '<line x1="295" y1="190" x2="207" y2="190" stroke="currentColor" stroke-width="1.2" marker-start="url(#ar-np)" marker-end="url(#ar-np)"/>' +
          '<text x="251" y="181" text-anchor="middle" class="fig-t">1クラブレングス</text>' +

          // ① 道路上の球 → ② 基点
          '<text x="335" y="162" text-anchor="middle" class="fig-t">① 球(道路上)</text>' +
          ball(335, 190, '') +
          '<line x1="329" y1="190" x2="303" y2="190" stroke="currentColor" stroke-width="1.4" marker-end="url(#ar-np)"/>' +
          '<circle cx="295" cy="190" r="4.5" fill="var(--fig-accent)" stroke="currentColor" stroke-width="1.2"/>' +
          '<path d="M290 292 L295 198" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="3 3"/>' +
          '<text x="290" y="306" text-anchor="end" class="fig-t">② 完全な救済のニヤレストポイント(基点)</text>' +

          hole(612, 190) +
          '<text x="612" y="222" text-anchor="middle" class="fig-t fig-t--dim">ホール</text>'
      },
      'back-on-line': {
        title: '後方線上の救済(2023年から)',
        caption: 'ホールと基点を結んで後方に伸ばした線上に、そのままドロップする。基点をあらかじめ決める必要はなく、球はどの方向にも1クラブレングスまで転がってよい。線から横にずらしてドロップした球は、どこに止まっても誤所。',
        alt: 'ホールから球を通って後方に伸びる線と、線上のドロップ地点を中心とした1クラブレングスの救済エリアを示した図',
        w: 640, h: 330,
        svg:
          arrowDefs('bl') +
          '<rect x="8" y="8" width="624" height="314" rx="6" fill="var(--fig-general)" stroke="var(--fig-line)" stroke-width="1"/>' +

          // 後方線
          '<line x1="556" y1="72" x2="96" y2="288" stroke="var(--fig-accent)" stroke-width="2" stroke-dasharray="7 5"/>' +
          '<text x="470" y="86" text-anchor="middle" class="fig-t" fill="var(--fig-accent)">ホールと基点を結んで後方に伸ばした線</text>' +

          // ドロップ地点の救済エリア(線上の点を中心とした円)
          '<circle cx="264" cy="209" r="62" fill="var(--fig-relief)" stroke="var(--fig-relief-line)" stroke-width="1.6" stroke-dasharray="5 4"/>' +
          '<line x1="264" y1="209" x2="326" y2="209" stroke="currentColor" stroke-width="1.2" marker-end="url(#ar-bl)"/>' +
          '<text x="300" y="201" text-anchor="middle" class="fig-t">1クラブレングス</text>' +
          '<text x="264" y="292" text-anchor="middle" class="fig-t">どの方向に転がってもよい範囲</text>' +

          ball(264, 209, '') +
          '<text x="222" y="196" text-anchor="end" class="fig-t">線上にドロップ</text>' +

          // 基点(元の球の位置 / 縁を最後に横切った地点)
          '<circle cx="416" cy="141" r="4.5" fill="var(--fig-accent)" stroke="currentColor" stroke-width="1.2"/>' +
          '<text x="416" y="128" text-anchor="middle" class="fig-t">基点</text>' +
          '<text x="416" y="114" text-anchor="middle" class="fig-t fig-t--dim">元の球の箇所 / 縁を最後に横切った地点</text>' +

          // 誤りの例 — 線から横にずらしてドロップ
          '<line x1="264" y1="209" x2="212" y2="150" stroke="var(--fig-bad)" stroke-width="1.4" stroke-dasharray="3 3" marker-end="url(#ar-bl)"/>' +
          '<circle cx="206" cy="144" r="7" fill="none" stroke="var(--fig-bad)" stroke-width="1.8"/>' +
          '<path d="M201 139 l10 10 M211 139 l-10 10" stroke="var(--fig-bad)" stroke-width="1.8"/>' +
          '<text x="196" y="130" text-anchor="end" class="fig-t" fill="var(--fig-bad)">線から外してドロップ → 誤所</text>' +

          hole(556, 72)
      },

      /* ── ペナルティーエリアの救済 ────────────────── */
      'penalty-area': {
        title: 'ペナルティーエリアの救済 — 黄と赤の違い',
        caption: 'いずれも1打の罰。黄は ①② の2つ、赤はそれに加えて ③ のラテラル救済が使える。赤で増えるのはこの1つだけで、③ はホールに近づかない範囲に限られる。',
        alt: 'ペナルティーエリアからの3つの救済方法(ストロークと距離、後方線上、ラテラル)を示した平面図。ラテラル救済は赤のペナルティーエリアだけで使える',
        w: 700, h: 380,
        svg:
          arrowDefs('pa') +
          '<rect x="8" y="8" width="684" height="364" rx="6" fill="var(--fig-general)" stroke="var(--fig-line)" stroke-width="1"/>' +

          // ペナルティーエリア
          '<ellipse cx="360" cy="145" rx="100" ry="76" fill="var(--fig-water)" stroke="var(--fig-penalty-r)" stroke-width="2.2"/>' +
          '<text x="350" y="118" text-anchor="middle" class="fig-t">ペナルティーエリア</text>' +
          ball(392, 145, '') +
          '<text x="410" y="150" class="fig-t">球</text>' +

          // 縁を最後に横切った地点(基点)
          '<circle cx="360" cy="221" r="5" fill="var(--fig-accent)" stroke="currentColor" stroke-width="1.2"/>' +
          '<text x="380" y="240" class="fig-t">縁を最後に横切った地点</text>' +

          // ① ストロークと距離
          '<line x1="330" y1="258" x2="104" y2="278" stroke="currentColor" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#ar-pa)"/>' +
          '<rect x="56" y="270" width="38" height="28" rx="3" fill="var(--fig-tee)" stroke="currentColor" stroke-width="1.3"/>' +
          '<text x="75" y="320" text-anchor="middle" class="fig-t">① ストロークと距離</text>' +
          '<text x="75" y="334" text-anchor="middle" class="fig-t fig-t--dim">直前の箇所から打ち直す</text>' +

          // ② 後方線上
          '<line x1="612" y1="66" x2="190" y2="326" stroke="var(--fig-accent)" stroke-width="1.8" stroke-dasharray="6 5"/>' +
          '<circle cx="224" cy="305" r="30" fill="var(--fig-relief)" stroke="var(--fig-relief-line)" stroke-width="1.5" stroke-dasharray="4 3"/>' +
          '<text x="224" y="354" text-anchor="middle" class="fig-t">② 後方線上</text>' +

          // ③ ラテラル(レッドのみ) — 弧の中点に向けて半径を引く
          '<path d="M280 221 a80 80 0 0 0 80 80" fill="none" stroke="var(--fig-penalty-r)" stroke-width="1.8" stroke-dasharray="5 4"/>' +
          '<line x1="360" y1="221" x2="303" y2="278" stroke="var(--fig-penalty-r)" stroke-width="1.2" marker-end="url(#ar-pa)"/>' +
          '<text x="376" y="292" class="fig-t" fill="var(--fig-penalty-r)">2クラブレングス</text>' +
          '<text x="250" y="200" text-anchor="end" class="fig-t" fill="var(--fig-penalty-r)">③ ラテラル(レッドのみ)</text>' +

          hole(612, 66)
      },
      'unplayable': {
        title: 'アンプレヤブルの3つの選択肢',
        caption: 'ペナルティーエリア以外ならどこでも宣言できる。3つとも1打の罰で、どれを選ぶかはプレーヤーが決める。罰なしの選択肢はない。',
        alt: 'アンプレヤブルの救済3種(ストロークと距離、後方線上、球の箇所から2クラブレングスのラテラル)を示した平面図',
        w: 640, h: 340,
        svg:
          arrowDefs('up') +
          '<rect x="8" y="8" width="624" height="324" rx="6" fill="var(--fig-general)" stroke="var(--fig-line)" stroke-width="1"/>' +

          // 茂み
          '<circle cx="330" cy="164" r="40" fill="var(--fig-bush)" stroke="currentColor" stroke-width="1.3"/>' +
          '<text x="330" y="118" text-anchor="middle" class="fig-t">木や茂みの中</text>' +
          ball(330, 164, '') +

          // ① ストロークと距離
          '<line x1="308" y1="180" x2="126" y2="256" stroke="currentColor" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#ar-up)"/>' +
          '<rect x="88" y="252" width="34" height="26" rx="3" fill="var(--fig-tee)" stroke="currentColor" stroke-width="1.3"/>' +
          '<text x="105" y="296" text-anchor="middle" class="fig-t">① ストロークと距離</text>' +
          '<text x="105" y="310" text-anchor="middle" class="fig-t fig-t--dim">直前の箇所から打ち直す</text>' +

          // ② 後方線上
          '<line x1="552" y1="76" x2="168" y2="318" stroke="var(--fig-accent)" stroke-width="1.6" stroke-dasharray="6 5"/>' +
          '<circle cx="252" cy="255" r="34" fill="var(--fig-relief)" stroke="var(--fig-relief-line)" stroke-width="1.4" stroke-dasharray="4 3"/>' +
          '<text x="252" y="304" text-anchor="middle" class="fig-t">② 後方線上</text>' +

          // ③ ラテラル 2クラブレングス
          '<path d="M254 100 a94 94 0 0 1 116 -22" fill="none" stroke="var(--fig-relief-line)" stroke-width="1.6" stroke-dasharray="4 3"/>' +
          '<line x1="330" y1="164" x2="262" y2="106" stroke="currentColor" stroke-width="1.2" marker-end="url(#ar-up)"/>' +
          '<text x="238" y="80" text-anchor="middle" class="fig-t">③ 球の箇所から</text>' +
          '<text x="238" y="66" text-anchor="middle" class="fig-t">2クラブレングス</text>' +

          hole(552, 76)
      },

      /* ── バンカー内のアンプレヤブル ──────────────── */
      'bunker-unplayable': {
        title: 'バンカー内のアンプレヤブル — 出るには2打罰',
        caption: '1打の罰の3つの選択肢は、いずれも球をバンカーの中に戻すことになる。バンカーの外に出せるのは、2打の罰を加えて後方線上の救済を受けるときだけ。',
        alt: 'バンカー内のアンプレヤブルで、1打罰の救済はバンカー内に留まり、2打罰の後方線上の救済だけがバンカー外に出られることを示した図',
        w: 640, h: 320,
        svg:
          arrowDefs('bu') +
          '<rect x="8" y="8" width="624" height="304" rx="6" fill="var(--fig-general)" stroke="var(--fig-line)" stroke-width="1"/>' +

          // バンカー
          '<path d="M188 108 q76 -40 156 -12 q56 20 44 70 q-14 56 -104 54 q-96 -2 -108 -50 q-10 -40 12 -62 z" ' +
          'fill="var(--fig-sand)" stroke="currentColor" stroke-width="1.6"/>' +
          '<text x="268" y="94" text-anchor="middle" class="fig-t">バンカー</text>' +
          ball(292, 160, '') +

          // 1打罰の救済エリア(バンカー内)
          '<path d="M214 148 a74 74 0 0 1 74 -34" fill="none" stroke="var(--fig-relief-line)" stroke-width="1.6" stroke-dasharray="4 3"/>' +
          '<text x="246" y="196" text-anchor="middle" class="fig-t">1打の罰 → バンカー内に留まる</text>' +

          // 2打罰の後方線上(バンカー外)
          '<line x1="556" y1="66" x2="92" y2="290" stroke="var(--fig-accent)" stroke-width="1.8" stroke-dasharray="6 5"/>' +
          '<circle cx="150" cy="266" r="36" fill="var(--fig-relief)" stroke="var(--fig-relief-line)" stroke-width="1.5" stroke-dasharray="4 3"/>' +
          '<text x="150" y="314" text-anchor="middle" class="fig-t" fill="var(--fig-accent)">2打の罰 → バンカーの外へ</text>' +

          hole(556, 66)
      },

      /* ── 目玉の球 ─────────────────────────────── */
      'embedded': {
        title: '目玉の球(自らのピッチマークに食い込んだ球)',
        caption: 'ジェネラルエリアなら罰なしで救済を受けられる。基点は球の直後の箇所で、そこから1クラブレングス、ホールに近づかない範囲にドロップする。バンカーとペナルティーエリアにはこの救済はない。',
        alt: '自らのピッチマークに食い込んだ球の断面と、球の直後の箇所を基点とした1クラブレングスの救済エリアを示した図',
        w: 640, h: 300,
        svg:
          arrowDefs('em') +
          // 断面図(左)
          '<rect x="20" y="30" width="250" height="112" rx="4" fill="var(--fig-general)" stroke="var(--fig-line)" stroke-width="1"/>' +
          '<path d="M20 100 L120 100 q12 -2 20 12 a22 22 0 0 0 40 0 q8 -14 20 -12 L270 100" fill="none" stroke="currentColor" stroke-width="1.8"/>' +
          '<path d="M20 100 L120 100 q12 -2 20 12 a22 22 0 0 0 40 0 q8 -14 20 -12 L270 100 L270 142 L20 142 z" fill="var(--fig-soil)"/>' +
          '<circle cx="160" cy="106" r="17" fill="var(--fig-ball)" stroke="currentColor" stroke-width="1.8"/>' +
          '<text x="145" y="56" text-anchor="middle" class="fig-t">自らのピッチマークに食い込んでいる</text>' +
          '<text x="145" y="164" text-anchor="middle" class="fig-t fig-t--dim">断面 — 球の一部が地面より下にある</text>' +

          // 平面図(右)
          '<rect x="300" y="30" width="332" height="230" rx="4" fill="var(--fig-general)" stroke="var(--fig-line)" stroke-width="1"/>' +
          // 救済エリア = 基点から1CL、ホールに近づかない(左半円)
          '<path d="M404 88 a76 76 0 0 0 0 152 z" fill="var(--fig-relief)" stroke="var(--fig-relief-line)" stroke-width="1.6" stroke-dasharray="5 4"/>' +
          '<text x="352" y="168" text-anchor="middle" class="fig-t">救済エリア</text>' +
          '<line x1="404" y1="76" x2="404" y2="252" stroke="var(--fig-accent)" stroke-width="1.5" stroke-dasharray="4 4"/>' +
          '<text x="410" y="70" class="fig-t" fill="var(--fig-accent)">ホールに近づかない</text>' +
          '<line x1="404" y1="164" x2="330" y2="164" stroke="currentColor" stroke-width="1.2" marker-start="url(#ar-em)" marker-end="url(#ar-em)"/>' +
          '<text x="367" y="156" text-anchor="middle" class="fig-t">1クラブレングス</text>' +
          '<circle cx="404" cy="164" r="4.5" fill="var(--fig-accent)" stroke="currentColor" stroke-width="1.2"/>' +
          '<text x="404" y="272" text-anchor="middle" class="fig-t">基点 = 球の直後の箇所</text>' +
          ball(428, 164, '') +
          '<text x="446" y="150" class="fig-t">球</text>' +
          hole(590, 164)
      },

      /* ── ドロップの手順 ───────────────────────── */
      'drop-flow': {
        title: 'ドロップの手順とやり直し',
        caption: '膝の高さからドロップし、救済エリアに止まればプレーする。エリアの外に出たら2回目のドロップ。2回目も出たときは、その2回目に球が最初に地面に触れた箇所にプレースする。',
        alt: 'ドロップから、救済エリアに止まった場合とエリア外に出た場合の分岐、2回目のドロップ、最終的なプレースまでの手順の流れ図',
        w: 640, h: 300,
        svg:
          arrowDefs('df') +
          // 1
          '<rect x="16" y="112" width="140" height="62" rx="4" fill="var(--fig-box)" stroke="currentColor" stroke-width="1.4"/>' +
          '<text x="86" y="136" text-anchor="middle" class="fig-t">① 膝の高さから</text>' +
          '<text x="86" y="152" text-anchor="middle" class="fig-t">ドロップ</text>' +
          '<text x="86" y="192" text-anchor="middle" class="fig-t fig-t--dim">まっすぐ立ったときの</text>' +
          '<text x="86" y="206" text-anchor="middle" class="fig-t fig-t--dim">地面から膝までの高さ</text>' +

          '<line x1="156" y1="143" x2="212" y2="143" stroke="currentColor" stroke-width="1.4" marker-end="url(#ar-df)"/>' +

          // 分岐
          '<path d="M212 143 L272 100 M212 143 L272 200" fill="none" stroke="currentColor" stroke-width="1.4"/>' +
          '<line x1="266" y1="104" x2="284" y2="91" stroke="currentColor" stroke-width="1.4" marker-end="url(#ar-df)"/>' +
          '<line x1="266" y1="196" x2="284" y2="209" stroke="currentColor" stroke-width="1.4" marker-end="url(#ar-df)"/>' +
          '<text x="238" y="96" text-anchor="middle" class="fig-t">エリア内</text>' +
          '<text x="238" y="216" text-anchor="middle" class="fig-t">エリア外</text>' +

          // 上: プレー
          '<rect x="292" y="62" width="128" height="52" rx="4" fill="var(--fig-relief)" stroke="var(--fig-relief-line)" stroke-width="1.6"/>' +
          '<text x="356" y="94" text-anchor="middle" class="fig-t">そのままプレー</text>' +

          // 下: 2回目
          '<rect x="292" y="186" width="128" height="52" rx="4" fill="var(--fig-box)" stroke="currentColor" stroke-width="1.4"/>' +
          '<text x="356" y="210" text-anchor="middle" class="fig-t">② 2回目の</text>' +
          '<text x="356" y="226" text-anchor="middle" class="fig-t">ドロップ</text>' +

          '<line x1="420" y1="212" x2="464" y2="212" stroke="currentColor" stroke-width="1.4" marker-end="url(#ar-df)"/>' +
          '<path d="M356 186 L356 140 L420 140" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3"/>' +
          '<line x1="414" y1="140" x2="426" y2="140" stroke="currentColor" stroke-width="1.2"/>' +
          '<path d="M420 140 L420 114" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3" marker-end="url(#ar-df)"/>' +
          '<text x="432" y="132" class="fig-t fig-t--dim">エリア内なら</text>' +

          // 最終: プレース
          '<rect x="472" y="176" width="152" height="72" rx="4" fill="var(--fig-relief)" stroke="var(--fig-relief-line)" stroke-width="1.6"/>' +
          '<text x="548" y="200" text-anchor="middle" class="fig-t">③ 2回目のドロップで</text>' +
          '<text x="548" y="216" text-anchor="middle" class="fig-t">球が最初に地面に</text>' +
          '<text x="548" y="232" text-anchor="middle" class="fig-t">触れた箇所にプレース</text>' +
          '<text x="548" y="266" text-anchor="middle" class="fig-t fig-t--dim">そこでも止まらなければ</text>' +
          '<text x="548" y="280" text-anchor="middle" class="fig-t fig-t--dim">止まる最も近い箇所にプレース</text>'
      },

      /* ── ストロークと距離の打数 ─────────────────── */
      'stroke-count': {
        title: 'ストロークと距離 — 打数の数え方',
        caption: '打った1打はそのまま残り、そこに1打の罰が加わる。だからティーショットがOBなら、打ち直しは3打目になる。',
        alt: 'ティーショットがOBになった場合に、1打目と1罰打を数えて打ち直しが3打目になることを示した時系列の図',
        w: 640, h: 210,
        svg:
          arrowDefs('sc') +
          '<line x1="40" y1="118" x2="600" y2="118" stroke="var(--fig-line)" stroke-width="1.5"/>' +

          // 1打目
          '<circle cx="110" cy="118" r="16" fill="var(--fig-box)" stroke="currentColor" stroke-width="1.6"/>' +
          '<text x="110" y="123" text-anchor="middle" class="fig-t">1</text>' +
          '<text x="110" y="90" text-anchor="middle" class="fig-t">ティーショット</text>' +
          '<text x="110" y="152" text-anchor="middle" class="fig-t fig-t--dim">打った1打は消えない</text>' +

          // OB
          '<line x1="132" y1="118" x2="242" y2="118" stroke="currentColor" stroke-width="1.4" stroke-dasharray="5 4" marker-end="url(#ar-sc)"/>' +
          '<text x="187" y="108" text-anchor="middle" class="fig-t fig-t--dim">アウトオブバウンズ</text>' +
          '<circle cx="266" cy="118" r="7" fill="none" stroke="var(--fig-bad)" stroke-width="1.8"/>' +
          '<path d="M261 113 l10 10 M271 113 l-10 10" stroke="var(--fig-bad)" stroke-width="1.8"/>' +

          // 罰打
          '<circle cx="360" cy="118" r="16" fill="var(--fig-penalty-fill)" stroke="var(--fig-accent)" stroke-width="1.8"/>' +
          '<text x="360" y="123" text-anchor="middle" class="fig-t">+1</text>' +
          '<text x="360" y="90" text-anchor="middle" class="fig-t" fill="var(--fig-accent)">1打の罰</text>' +
          '<text x="360" y="152" text-anchor="middle" class="fig-t fig-t--dim">ストロークと距離</text>' +
          '<line x1="290" y1="118" x2="338" y2="118" stroke="currentColor" stroke-width="1.4" marker-end="url(#ar-sc)"/>' +

          // 3打目
          '<line x1="382" y1="118" x2="472" y2="118" stroke="currentColor" stroke-width="1.4" marker-end="url(#ar-sc)"/>' +
          '<circle cx="500" cy="118" r="20" fill="var(--fig-relief)" stroke="var(--fig-relief-line)" stroke-width="2"/>' +
          '<text x="500" y="124" text-anchor="middle" class="fig-t">3</text>' +
          '<text x="500" y="86" text-anchor="middle" class="fig-t">打ち直し</text>' +
          '<text x="500" y="158" text-anchor="middle" class="fig-t fig-t--dim">直前のストロークを行った</text>' +
          '<text x="500" y="172" text-anchor="middle" class="fig-t fig-t--dim">箇所から3打目</text>'
      },

      /* ── 暫定球 ───────────────────────────────── */
      'provisional': {
        title: '暫定球を打てる場合・打てない場合',
        caption: '暫定球はペナルティーエリアの外で紛失かもしれないとき、またはOBかもしれないときだけ打てる。ペナルティーエリアの中で紛失したかもしれない場合には打てない。',
        alt: '球の行方に応じて暫定球が打てるかどうか、また元の球が見つかった場合に暫定球がどうなるかを示した判断の流れ図',
        w: 640, h: 320,
        svg:
          arrowDefs('pv') +
          '<rect x="16" y="20" width="176" height="56" rx="4" fill="var(--fig-box)" stroke="currentColor" stroke-width="1.4"/>' +
          '<text x="104" y="44" text-anchor="middle" class="fig-t">球の行方が分からない</text>' +
          '<text x="104" y="62" text-anchor="middle" class="fig-t">/ OBかもしれない</text>' +

          '<line x1="104" y1="76" x2="104" y2="112" stroke="currentColor" stroke-width="1.4" marker-end="url(#ar-pv)"/>' +

          // 分岐
          '<rect x="16" y="118" width="176" height="70" rx="4" fill="var(--fig-relief)" stroke="var(--fig-relief-line)" stroke-width="1.6"/>' +
          '<text x="104" y="142" text-anchor="middle" class="fig-t">ペナルティーエリアの外</text>' +
          '<text x="104" y="160" text-anchor="middle" class="fig-t">で紛失 / OB かも</text>' +
          '<text x="104" y="180" text-anchor="middle" class="fig-t" fill="var(--fig-relief-line)">→ 暫定球を打てる</text>' +

          '<rect x="16" y="206" width="176" height="70" rx="4" fill="var(--fig-bad-fill)" stroke="var(--fig-bad)" stroke-width="1.6"/>' +
          '<text x="104" y="230" text-anchor="middle" class="fig-t">ペナルティーエリアの</text>' +
          '<text x="104" y="248" text-anchor="middle" class="fig-t">中で紛失かも</text>' +
          '<text x="104" y="268" text-anchor="middle" class="fig-t" fill="var(--fig-bad)">→ 暫定球は打てない</text>' +

          // 暫定球を打った後
          '<line x1="192" y1="153" x2="244" y2="153" stroke="currentColor" stroke-width="1.4" marker-end="url(#ar-pv)"/>' +
          '<rect x="250" y="118" width="152" height="70" rx="4" fill="var(--fig-box)" stroke="currentColor" stroke-width="1.4"/>' +
          '<text x="326" y="142" text-anchor="middle" class="fig-t">打つ前に「暫定球を</text>' +
          '<text x="326" y="160" text-anchor="middle" class="fig-t">プレーする」と</text>' +
          '<text x="326" y="178" text-anchor="middle" class="fig-t">告げる(必須)</text>' +

          '<path d="M402 153 L440 153 L440 74" fill="none" stroke="currentColor" stroke-width="1.4"/>' +
          '<line x1="440" y1="90" x2="440" y2="72" stroke="currentColor" stroke-width="1.4" marker-end="url(#ar-pv)"/>' +
          '<path d="M402 153 L440 153 L440 236" fill="none" stroke="currentColor" stroke-width="1.4"/>' +
          '<line x1="440" y1="220" x2="440" y2="238" stroke="currentColor" stroke-width="1.4" marker-end="url(#ar-pv)"/>' +

          '<rect x="452" y="26" width="172" height="72" rx="4" fill="var(--fig-relief)" stroke="var(--fig-relief-line)" stroke-width="1.6"/>' +
          '<text x="538" y="50" text-anchor="middle" class="fig-t">3分以内に元の球が</text>' +
          '<text x="538" y="68" text-anchor="middle" class="fig-t">コース上で見つかった</text>' +
          '<text x="538" y="88" text-anchor="middle" class="fig-t" fill="var(--fig-relief-line)">→ 元の球でプレー続行</text>' +

          '<rect x="452" y="242" width="172" height="60" rx="4" fill="var(--fig-penalty-fill)" stroke="var(--fig-accent)" stroke-width="1.6"/>' +
          '<text x="538" y="266" text-anchor="middle" class="fig-t">紛失 または OB</text>' +
          '<text x="538" y="288" text-anchor="middle" class="fig-t" fill="var(--fig-accent)">→ 暫定球が インプレー</text>' +
          '<text x="538" y="196" text-anchor="middle" class="fig-t fig-t--dim">暫定球は 1打の罰の</text>' +
          '<text x="538" y="212" text-anchor="middle" class="fig-t fig-t--dim">ストロークと距離になる</text>'
      }

    };
  }

  var F = figures();

  /** 図解1つを <figure> として組み立てて返す */
  function render(id) {
    var f = F[id];
    if (!f) return null;
    var fig = document.createElement('figure');
    fig.className = 'fig';
    fig.innerHTML =
      '<svg viewBox="0 0 ' + f.w + ' ' + f.h + '" role="img" aria-label="' + f.alt + '" class="fig__svg">' + f.svg + '</svg>' +
      '<figcaption class="fig__cap"><b>' + f.title + '</b>' + f.caption + '</figcaption>';
    return fig;
  }

  return { all: F, render: render, has: function (id) { return !!F[id]; } };
})();
