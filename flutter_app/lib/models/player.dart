enum Team { a, b }

class Player {
  int? id;
  String name;
  Team team;

  Player({
    this.id,
    required this.name,
    required this.team,
  });

  Map<String, dynamic> toMap() {
    return {
      if (id != null) 'id': id,
      'name': name,
      'team': team.name,
    };
  }

  factory Player.fromMap(Map<String, dynamic> map) {
    return Player(
      id: map['id'] as int?,
      name: map['name'] as String,
      team: Team.values.firstWhere(
        (t) => t.name == map['team'],
        orElse: () => Team.a,
      ),
    );
  }

  Player copyWith({int? id, String? name, Team? team}) {
    return Player(
      id: id ?? this.id,
      name: name ?? this.name,
      team: team ?? this.team,
    );
  }
}
