import 'package:flutter/foundation.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../models/game.dart';
import '../models/hole_score.dart';

class DatabaseHelper {
  static final DatabaseHelper instance = DatabaseHelper._internal();
  static Database? _database;

  // Web in-memory storage
  static final List<Map<String, dynamic>> _webGames = [];
  static final List<Map<String, dynamic>> _webHoleScores = [];
  static int _webGameId = 1;
  static int _webHoleScoreId = 1;

  DatabaseHelper._internal();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  Future<Database> _initDatabase() async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, 'golf_las_vegas.db');
    return await openDatabase(
      path,
      version: 2,
      onCreate: _onCreate,
      onUpgrade: _onUpgrade,
    );
  }

  Future<void> _onUpgrade(Database db, int oldVersion, int newVersion) async {
    if (oldVersion < 2) {
      await db.execute(
        "ALTER TABLE games ADD COLUMN team_formation_mode TEXT NOT NULL DEFAULT 'fixed'",
      );
    }
  }

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_a_name TEXT NOT NULL,
        team_b_name TEXT NOT NULL,
        player1_name TEXT NOT NULL,
        player2_name TEXT NOT NULL,
        player3_name TEXT NOT NULL,
        player4_name TEXT NOT NULL,
        bet_per_point INTEGER NOT NULL DEFAULT 100,
        birdie_flip_enabled INTEGER NOT NULL DEFAULT 1,
        total_holes INTEGER NOT NULL DEFAULT 18,
        team_formation_mode TEXT NOT NULL DEFAULT 'fixed',
        created_at TEXT NOT NULL
      )
    ''');

    await db.execute('''
      CREATE TABLE hole_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER NOT NULL,
        hole_number INTEGER NOT NULL,
        score_a1 INTEGER,
        score_a2 INTEGER,
        score_b1 INTEGER,
        score_b2 INTEGER,
        par_score INTEGER,
        flip_a INTEGER NOT NULL DEFAULT 0,
        flip_b INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
      )
    ''');
  }

  // ── ゲームの挿入 ──────────────────────────────────────────
  Future<int> insertGame(Game game) async {
    if (kIsWeb) {
      final id = _webGameId++;
      final map = Map<String, dynamic>.from(game.toMap());
      map['id'] = id;
      _webGames.add(map);

      for (int i = 1; i <= game.totalHoles; i++) {
        final hole = HoleScore(gameId: id, holeNumber: i, parScore: 4);
        final holeMap = Map<String, dynamic>.from(hole.toMap());
        holeMap['id'] = _webHoleScoreId++;
        _webHoleScores.add(holeMap);
      }
      return id;
    }

    final db = await database;
    final id = await db.insert('games', game.toMap());
    for (int i = 1; i <= game.totalHoles; i++) {
      final holeScore = HoleScore(gameId: id, holeNumber: i, parScore: 4);
      await db.insert('hole_scores', holeScore.toMap());
    }
    return id;
  }

  // ── 全ゲームを取得（最新順） ──────────────────────────────
  Future<List<Game>> getAllGames() async {
    if (kIsWeb) {
      final sorted = List<Map<String, dynamic>>.from(_webGames)
        ..sort((a, b) => (b['created_at'] as String)
            .compareTo(a['created_at'] as String));
      return sorted.map((m) => Game.fromMap(m)).toList();
    }

    final db = await database;
    final maps = await db.query('games', orderBy: 'created_at DESC');
    return maps.map((m) => Game.fromMap(m)).toList();
  }

  // ── ゲームIDでゲームを取得（ホールスコア含む） ─────────────
  Future<Game?> getGame(int id) async {
    if (kIsWeb) {
      final maps = _webGames.where((m) => m['id'] == id).toList();
      if (maps.isEmpty) return null;
      final game = Game.fromMap(maps.first);
      final holeScores = await getHoleScores(id);
      return game.copyWith(holeScores: holeScores);
    }

    final db = await database;
    final maps = await db.query('games', where: 'id = ?', whereArgs: [id]);
    if (maps.isEmpty) return null;
    final game = Game.fromMap(maps.first);
    final holeScores = await getHoleScores(id);
    return game.copyWith(holeScores: holeScores);
  }

  // ── ホールスコアを取得 ────────────────────────────────────
  Future<List<HoleScore>> getHoleScores(int gameId) async {
    if (kIsWeb) {
      final maps = _webHoleScores
          .where((m) => m['game_id'] == gameId)
          .toList()
        ..sort((a, b) =>
            (a['hole_number'] as int).compareTo(b['hole_number'] as int));
      return maps.map((m) => HoleScore.fromMap(m)).toList();
    }

    final db = await database;
    final maps = await db.query(
      'hole_scores',
      where: 'game_id = ?',
      whereArgs: [gameId],
      orderBy: 'hole_number ASC',
    );
    return maps.map((m) => HoleScore.fromMap(m)).toList();
  }

  // ── ホールスコアの更新 ────────────────────────────────────
  Future<int> updateHoleScore(HoleScore holeScore) async {
    if (kIsWeb) {
      final idx = _webHoleScores.indexWhere((m) =>
          m['game_id'] == holeScore.gameId &&
          m['hole_number'] == holeScore.holeNumber);
      if (idx >= 0) {
        final updated = Map<String, dynamic>.from(holeScore.toMap());
        updated['id'] = _webHoleScores[idx]['id'];
        _webHoleScores[idx] = updated;
      }
      return 1;
    }

    final db = await database;
    if (holeScore.id != null) {
      return await db.update(
        'hole_scores',
        holeScore.toMap(),
        where: 'id = ?',
        whereArgs: [holeScore.id],
      );
    } else {
      final existing = await db.query(
        'hole_scores',
        where: 'game_id = ? AND hole_number = ?',
        whereArgs: [holeScore.gameId, holeScore.holeNumber],
      );
      if (existing.isNotEmpty) {
        return await db.update(
          'hole_scores',
          holeScore.toMap(),
          where: 'game_id = ? AND hole_number = ?',
          whereArgs: [holeScore.gameId, holeScore.holeNumber],
        );
      } else {
        await db.insert('hole_scores', holeScore.toMap());
        return 1;
      }
    }
  }

  // ── ゲームの削除 ──────────────────────────────────────────
  Future<int> deleteGame(int id) async {
    if (kIsWeb) {
      _webHoleScores.removeWhere((m) => m['game_id'] == id);
      final removed = _webGames.where((m) => m['id'] == id).length;
      _webGames.removeWhere((m) => m['id'] == id);
      return removed;
    }

    final db = await database;
    await db.delete('hole_scores', where: 'game_id = ?', whereArgs: [id]);
    return await db.delete('games', where: 'id = ?', whereArgs: [id]);
  }

  // ── ゲーム情報の更新（スコアを除く） ─────────────────────
  Future<int> updateGame(Game game) async {
    if (kIsWeb) {
      final idx = _webGames.indexWhere((m) => m['id'] == game.id);
      if (idx >= 0) {
        final updated = Map<String, dynamic>.from(game.toMap());
        updated['id'] = game.id;
        _webGames[idx] = updated;
      }
      return 1;
    }

    final db = await database;
    return await db.update(
      'games',
      game.toMap(),
      where: 'id = ?',
      whereArgs: [game.id],
    );
  }
}
