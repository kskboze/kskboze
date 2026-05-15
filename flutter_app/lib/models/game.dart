import 'hole_score.dart';

enum TeamFormationMode {
  fixed,      // 固定チーム
  rotation,   // ローテーション（1ホールごと）
  oneAndFour, // 1&4 vs 2&3 固定
}

extension TeamFormationModeX on TeamFormationMode {
  String get displayName {
    switch (this) {
      case TeamFormationMode.fixed:      return '固定チーム';
      case TeamFormationMode.rotation:   return 'ローテーション';
      case TeamFormationMode.oneAndFour: return '1&4 vs 2&3';
    }
  }

  String get description {
    switch (this) {
      case TeamFormationMode.fixed:      return 'ユーザーが自由に2チームに振り分け';
      case TeamFormationMode.rotation:   return '1ホールごとにパートナーが変わる';
      case TeamFormationMode.oneAndFour: return '1番目＆4番目 vs 2番目＆3番目';
    }
  }

  String get dbValue {
    switch (this) {
      case TeamFormationMode.fixed:      return 'fixed';
      case TeamFormationMode.rotation:   return 'rotation';
      case TeamFormationMode.oneAndFour: return 'oneAndFour';
    }
  }
}

TeamFormationMode teamFormationModeFromDb(String? v) {
  switch (v) {
    case 'rotation':   return TeamFormationMode.rotation;
    case 'oneAndFour': return TeamFormationMode.oneAndFour;
    default:           return TeamFormationMode.fixed;
  }
}

class Game {
  int? id;
  String teamAName;
  String teamBName;
  String player1Name; // TeamA P1
  String player2Name; // TeamA P2
  String player3Name; // TeamB P1
  String player4Name; // TeamB P2
  int betPerPoint;
  bool birdieFlipEnabled;
  int totalHoles; // 9 or 18
  TeamFormationMode teamFormationMode;
  DateTime createdAt;
  List<HoleScore> holeScores;

  Game({
    this.id,
    required this.teamAName,
    required this.teamBName,
    required this.player1Name,
    required this.player2Name,
    required this.player3Name,
    required this.player4Name,
    required this.betPerPoint,
    required this.birdieFlipEnabled,
    required this.totalHoles,
    this.teamFormationMode = TeamFormationMode.fixed,
    required this.createdAt,
    this.holeScores = const [],
  });

  Map<String, dynamic> toMap() {
    return {
      if (id != null) 'id': id,
      'team_a_name': teamAName,
      'team_b_name': teamBName,
      'player1_name': player1Name,
      'player2_name': player2Name,
      'player3_name': player3Name,
      'player4_name': player4Name,
      'bet_per_point': betPerPoint,
      'birdie_flip_enabled': birdieFlipEnabled ? 1 : 0,
      'total_holes': totalHoles,
      'team_formation_mode': teamFormationMode.dbValue,
      'created_at': createdAt.toIso8601String(),
    };
  }

  factory Game.fromMap(Map<String, dynamic> map) {
    return Game(
      id: map['id'] as int?,
      teamAName: map['team_a_name'] as String? ?? 'チームA',
      teamBName: map['team_b_name'] as String? ?? 'チームB',
      player1Name: map['player1_name'] as String? ?? 'P1',
      player2Name: map['player2_name'] as String? ?? 'P2',
      player3Name: map['player3_name'] as String? ?? 'P3',
      player4Name: map['player4_name'] as String? ?? 'P4',
      betPerPoint: map['bet_per_point'] as int? ?? 100,
      birdieFlipEnabled: (map['birdie_flip_enabled'] as int?) == 1,
      totalHoles: map['total_holes'] as int? ?? 18,
      teamFormationMode: teamFormationModeFromDb(map['team_formation_mode'] as String?),
      createdAt: DateTime.parse(map['created_at'] as String),
    );
  }

  Game copyWith({
    int? id,
    String? teamAName,
    String? teamBName,
    String? player1Name,
    String? player2Name,
    String? player3Name,
    String? player4Name,
    int? betPerPoint,
    bool? birdieFlipEnabled,
    int? totalHoles,
    TeamFormationMode? teamFormationMode,
    DateTime? createdAt,
    List<HoleScore>? holeScores,
  }) {
    return Game(
      id: id ?? this.id,
      teamAName: teamAName ?? this.teamAName,
      teamBName: teamBName ?? this.teamBName,
      player1Name: player1Name ?? this.player1Name,
      player2Name: player2Name ?? this.player2Name,
      player3Name: player3Name ?? this.player3Name,
      player4Name: player4Name ?? this.player4Name,
      betPerPoint: betPerPoint ?? this.betPerPoint,
      birdieFlipEnabled: birdieFlipEnabled ?? this.birdieFlipEnabled,
      totalHoles: totalHoles ?? this.totalHoles,
      teamFormationMode: teamFormationMode ?? this.teamFormationMode,
      createdAt: createdAt ?? this.createdAt,
      holeScores: holeScores ?? this.holeScores,
    );
  }
}
