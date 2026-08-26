/* カテゴリー定義
 * 規則の構成に沿って20章に分け、6つの部にまとめる。
 * 問題データ側の cat はここの id を参照する。
 */

window.GOLF_QUIZ_BANDS = [
  { id: 'updates',    name: '2023年の改訂',     note: 'いただいた2つの資料から' },
  { id: 'foundation', name: '基本と用具',       note: '規則1〜6' },
  { id: 'playing',    name: '球のプレー',       note: '規則7〜11' },
  { id: 'course',     name: '特別なコースエリア', note: '規則12〜13' },
  { id: 'relief',     name: '救済',             note: '規則14〜19' },
  { id: 'admin',      name: '競技の運営',       note: '規則20〜25' }
];

window.GOLF_QUIZ_CATEGORIES = [
  { id: 'changes2023',    band: 'updates',    name: '2023年の主な変更点',   short: '変更点', rules: '5つの重要な変更' },
  { id: 'clarifications', band: 'updates',    name: '追加の詳説',           short: '詳説',   rules: '2023年10月5日更新' },

  { id: 'basics',         band: 'foundation', name: 'ゲームと競技の基本',   short: '基本',   rules: '規則1〜3' },
  { id: 'equipment',      band: 'foundation', name: 'クラブと球',           short: '用具',   rules: '規則4' },
  { id: 'round',          band: 'foundation', name: 'ラウンドとホールのプレー', short: 'ラウンド', rules: '規則5〜6' },

  { id: 'search',         band: 'playing',    name: '球の捜索と特定',       short: '捜索',   rules: '規則7' },
  { id: 'improve',        band: 'playing',    name: 'コースはあるがまま',   short: '改善',   rules: '規則8' },
  { id: 'ballmoved',      band: 'playing',    name: '球が動かされたとき',   short: '球が動く', rules: '規則9' },
  { id: 'stroke',         band: 'playing',    name: 'ストローク・アドバイス・キャディー', short: '援助', rules: '規則10' },
  { id: 'inmotion',       band: 'playing',    name: '動いている球',         short: '動球',   rules: '規則11' },

  { id: 'bunker',         band: 'course',     name: 'バンカー',             short: 'バンカー', rules: '規則12' },
  { id: 'green',          band: 'course',     name: 'パッティンググリーン', short: 'グリーン', rules: '規則13' },

  { id: 'procedure',      band: 'relief',     name: '救済の手続き',         short: '手続き', rules: '規則14' },
  { id: 'freerelief',     band: 'relief',     name: '罰なしの救済',         short: '無罰救済', rules: '規則15〜16' },
  { id: 'penaltyarea',    band: 'relief',     name: 'ペナルティーエリア',   short: 'PA',     rules: '規則17' },
  { id: 'lostob',         band: 'relief',     name: '紛失球・OB・暫定球',   short: '紛失OB', rules: '規則18' },
  { id: 'unplayable',     band: 'relief',     name: 'アンプレヤブル',       short: 'アンプレ', rules: '規則19' },

  { id: 'disputes',       band: 'admin',      name: '規則問題の解決',       short: '裁定',   rules: '規則20' },
  { id: 'formats',        band: 'admin',      name: '他の競技形式',         short: '形式',   rules: '規則21〜24' },
  { id: 'disability',     band: 'admin',      name: '障がいを持つプレーヤー', short: '規則25', rules: '規則25' }
];

/* 罰の区分。解説の見出しと色分けに使う */
window.GOLF_QUIZ_PENALTIES = {
  none:    { label: '罰なし',   tone: 'good',  note: 'スコアに打数は加わらない' },
  one:     { label: '1打の罰',  tone: 'warn',  note: 'スコアに1打を加える' },
  general: { label: '一般の罰', tone: 'bad',   note: 'ストロークプレーでは2打／マッチプレーではそのホールの負け' },
  dq:      { label: '失格',     tone: 'bad',   note: '競技から除外される' },
  varies:  { label: '場合による', tone: 'warn', note: '状況によって罰の重さが変わる' },
  info:    { label: '罰の問題ではない', tone: 'neutral', note: '知識を問う設問' }
};

window.GOLF_QUIZ_QUESTIONS = [];
