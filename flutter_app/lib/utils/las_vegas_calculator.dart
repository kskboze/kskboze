import 'dart:math';
import '../models/game.dart';
import '../models/hole_score.dart';

/// ホールごとのチーム割り当て情報
class TeamAssignment {
  final String teamALabel;
  final String teamBLabel;
  final String p1Name; // Team A player 1
  final String p2Name; // Team A player 2
  final String p3Name; // Team B player 1
  final String p4Name; // Team B player 2
  /// ローテーションのラウンド番号（1〜3）。固定モードは0。
  final int rotationRound;

  const TeamAssignment({
    required this.teamALabel,
    required this.teamBLabel,
    required this.p1Name,
    required this.p2Name,
    required this.p3Name,
    required this.p4Name,
    this.rotationRound = 0,
  });
}

class LasVegasCalculator {
  /// ホールごとのチーム割り当てを返す
  static TeamAssignment getAssignmentForHole(int holeNumber, Game game) {
    switch (game.teamFormationMode) {
      case TeamFormationMode.fixed:
        return TeamAssignment(
          teamALabel: game.teamAName,
          teamBLabel: game.teamBName,
          p1Name: game.player1Name,
          p2Name: game.player2Name,
          p3Name: game.player3Name,
          p4Name: game.player4Name,
        );

      case TeamFormationMode.rotation:
        final round = (holeNumber - 1) % 3 + 1; // 1, 2, 3
        switch (round) {
          case 1: // P1&P2 vs P3&P4
            return TeamAssignment(
              teamALabel: '${game.player1Name} & ${game.player2Name}',
              teamBLabel: '${game.player3Name} & ${game.player4Name}',
              p1Name: game.player1Name,
              p2Name: game.player2Name,
              p3Name: game.player3Name,
              p4Name: game.player4Name,
              rotationRound: round,
            );
          case 2: // P1&P3 vs P2&P4
            return TeamAssignment(
              teamALabel: '${game.player1Name} & ${game.player3Name}',
              teamBLabel: '${game.player2Name} & ${game.player4Name}',
              p1Name: game.player1Name,
              p2Name: game.player3Name,
              p3Name: game.player2Name,
              p4Name: game.player4Name,
              rotationRound: round,
            );
          default: // P1&P4 vs P2&P3
            return TeamAssignment(
              teamALabel: '${game.player1Name} & ${game.player4Name}',
              teamBLabel: '${game.player2Name} & ${game.player3Name}',
              p1Name: game.player1Name,
              p2Name: game.player4Name,
              p3Name: game.player2Name,
              p4Name: game.player3Name,
              rotationRound: round,
            );
        }

      case TeamFormationMode.oneAndFour: // P1&P4 vs P2&P3（固定）
        return TeamAssignment(
          teamALabel: '${game.player1Name} & ${game.player4Name}',
          teamBLabel: '${game.player2Name} & ${game.player3Name}',
          p1Name: game.player1Name,
          p2Name: game.player4Name,
          p3Name: game.player2Name,
          p4Name: game.player3Name,
        );
    }
  }

  /// 2つのスコアから2桁数字を作る（低い方が十の位）
  static int makeCombo(int s1, int s2) {
    int lo = min(s1, s2);
    int hi = max(s1, s2);
    return lo * 10 + hi;
  }

  /// フリップ（数字を逆にする）
  static int flipCombo(int combo) {
    int tens = combo ~/ 10;
    int ones = combo % 10;
    return ones * 10 + tens;
  }

  /// バーディー以下かどうかチェック（フリップ権利があるか）
  static bool hasBirdieOrBetter(int score1, int score2, int par) {
    return score1 < par || score2 < par;
  }

  /// ホールのデルタ計算
  /// 正 = Aチームが獲得, 負 = Bチームが獲得
  static int calculateHoleDelta(int comboA, int comboB) {
    return comboB - comboA;
  }

  /// ホールスコアからAチームのコンボを計算
  static int? getComboA(HoleScore hole) {
    if (hole.scoreA1 == null || hole.scoreA2 == null) return null;
    int combo = makeCombo(hole.scoreA1!, hole.scoreA2!);
    if (hole.flipA) {
      combo = flipCombo(combo);
    }
    return combo;
  }

  /// ホールスコアからBチームのコンボを計算
  static int? getComboB(HoleScore hole) {
    if (hole.scoreB1 == null || hole.scoreB2 == null) return null;
    int combo = makeCombo(hole.scoreB1!, hole.scoreB2!);
    if (hole.flipB) {
      combo = flipCombo(combo);
    }
    return combo;
  }

  /// ホールのデルタ（両チームのコンボが揃っていれば）
  static int? getHoleDelta(HoleScore hole) {
    final comboA = getComboA(hole);
    final comboB = getComboB(hole);
    if (comboA == null || comboB == null) return null;
    return calculateHoleDelta(comboA, comboB);
  }

  /// ホール一覧から累計デルタリスト（各インデックスまでの累計）を計算
  static List<int> getCumulativeDeltas(List<HoleScore> holes) {
    int running = 0;
    List<int> result = [];
    for (final hole in holes) {
      final delta = getHoleDelta(hole);
      running += delta ?? 0;
      result.add(running);
    }
    return result;
  }

  /// 全ホールの累計デルタ
  static int getTotalDelta(List<HoleScore> holes) {
    int total = 0;
    for (final hole in holes) {
      total += getHoleDelta(hole) ?? 0;
    }
    return total;
  }

  /// 精算金額（賭け金 × |累計デルタ|）
  static int calculateSettlement(List<HoleScore> holes, int betPerPoint) {
    return getTotalDelta(holes).abs() * betPerPoint;
  }

  /// Aチームのフリップ権利があるかどうか（バーディー以下）
  static bool canFlipA(HoleScore hole) {
    if (hole.scoreA1 == null || hole.scoreA2 == null || hole.parScore == null) {
      return false;
    }
    return hasBirdieOrBetter(hole.scoreA1!, hole.scoreA2!, hole.parScore!);
  }

  /// Bチームのフリップ権利があるかどうか（バーディー以下）
  static bool canFlipB(HoleScore hole) {
    if (hole.scoreB1 == null || hole.scoreB2 == null || hole.parScore == null) {
      return false;
    }
    return hasBirdieOrBetter(hole.scoreB1!, hole.scoreB2!, hole.parScore!);
  }

  /// スコアの文字列表記（パーとの関係）
  static String getScoreLabel(int score, int par) {
    final diff = score - par;
    if (diff <= -2) return 'イーグル以下';
    if (diff == -1) return 'バーディー';
    if (diff == 0) return 'パー';
    if (diff == 1) return 'ボギー';
    if (diff == 2) return 'ダブルボギー';
    return '+$diff';
  }

  /// デルタの勝敗テキスト
  static String getDeltaDescription(int delta, String teamAName, String teamBName) {
    if (delta > 0) return '$teamAName +$delta';
    if (delta < 0) return '$teamBName +${delta.abs()}';
    return '引き分け';
  }
}
