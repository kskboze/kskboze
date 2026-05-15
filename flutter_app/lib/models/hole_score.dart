class HoleScore {
  int? id;
  int gameId;
  int holeNumber;
  int? scoreA1; // TeamA Player1
  int? scoreA2; // TeamA Player2
  int? scoreB1; // TeamB Player1
  int? scoreB2; // TeamB Player2
  int? parScore; // パー（3〜5）
  bool flipA; // Aチームがフリップを使用
  bool flipB; // Bチームがフリップを使用

  HoleScore({
    this.id,
    required this.gameId,
    required this.holeNumber,
    this.scoreA1,
    this.scoreA2,
    this.scoreB1,
    this.scoreB2,
    this.parScore,
    this.flipA = false,
    this.flipB = false,
  });

  Map<String, dynamic> toMap() {
    return {
      if (id != null) 'id': id,
      'game_id': gameId,
      'hole_number': holeNumber,
      'score_a1': scoreA1,
      'score_a2': scoreA2,
      'score_b1': scoreB1,
      'score_b2': scoreB2,
      'par_score': parScore,
      'flip_a': flipA ? 1 : 0,
      'flip_b': flipB ? 1 : 0,
    };
  }

  factory HoleScore.fromMap(Map<String, dynamic> map) {
    return HoleScore(
      id: map['id'] as int?,
      gameId: map['game_id'] as int,
      holeNumber: map['hole_number'] as int,
      scoreA1: map['score_a1'] as int?,
      scoreA2: map['score_a2'] as int?,
      scoreB1: map['score_b1'] as int?,
      scoreB2: map['score_b2'] as int?,
      parScore: map['par_score'] as int?,
      flipA: (map['flip_a'] as int?) == 1,
      flipB: (map['flip_b'] as int?) == 1,
    );
  }

  HoleScore copyWith({
    int? id,
    int? gameId,
    int? holeNumber,
    int? scoreA1,
    int? scoreA2,
    int? scoreB1,
    int? scoreB2,
    int? parScore,
    bool? flipA,
    bool? flipB,
  }) {
    return HoleScore(
      id: id ?? this.id,
      gameId: gameId ?? this.gameId,
      holeNumber: holeNumber ?? this.holeNumber,
      scoreA1: scoreA1 ?? this.scoreA1,
      scoreA2: scoreA2 ?? this.scoreA2,
      scoreB1: scoreB1 ?? this.scoreB1,
      scoreB2: scoreB2 ?? this.scoreB2,
      parScore: parScore ?? this.parScore,
      flipA: flipA ?? this.flipA,
      flipB: flipB ?? this.flipB,
    );
  }

  bool get isComplete =>
      scoreA1 != null && scoreA2 != null && scoreB1 != null && scoreB2 != null;
}
