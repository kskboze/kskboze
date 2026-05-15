import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../models/game.dart';
import '../models/hole_score.dart';

class DatabaseHelper {
  static final DatabaseHelper instance = DatabaseHelper._internal();
  static Database? _database;

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
      version: 1,
      onCreate: _onCreate,
    );
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

  // ゲームの挿入
  Future<int> insertGame(Game game) async {
    final db = await database;
    final id = await db.insert('games', game.toMap());

    // ホールスコアの初期レコードを作成
    for (int i = 1; i <= game.totalHoles; i++) {
      final holeScore = HoleScore(
        gameId: id,
        holeNumber: i,
        parScore: 4,
      );
      await db.insert('hole_scores', holeScore.toMap());
    }

    return id;
  }

  // 全ゲームを取得（最新順）
  Future<List<Game>> getAllGames() async {
    final db = await database;
    final maps = await db.query(
      'games',
      orderBy: 'created_at DESC',
    );
    return maps.map((m) => Game.fromMap(m)).toList();
  }

  // ゲームIDでゲームを取得（ホールスコア含む）
  Future<Game?> getGame(int id) async {
    final db = await database;
    final maps = await db.query(
      'games',
      where: 'id = ?',
      whereArgs: [id],
    );
    if (maps.isEmpty) return null;

    final game = Game.fromMap(maps.first);
    final holeScores = await getHoleScores(id);
    return game.copyWith(holeScores: holeScores);
  }

  // ゲームのホールスコアを取得
  Future<List<HoleScore>> getHoleScores(int gameId) async {
    final db = await database;
    final maps = await db.query(
      'hole_scores',
      where: 'game_id = ?',
      whereArgs: [gameId],
      orderBy: 'hole_number ASC',
    );
    return maps.map((m) => HoleScore.fromMap(m)).toList();
  }

  // ホールスコアの更新
  Future<int> updateHoleScore(HoleScore holeScore) async {
    final db = await database;
    if (holeScore.id != null) {
      return await db.update(
        'hole_scores',
        holeScore.toMap(),
        where: 'id = ?',
        whereArgs: [holeScore.id],
      );
    } else {
      // IDがない場合はgame_idとhole_numberで検索して更新
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

  // ゲームの削除
  Future<int> deleteGame(int id) async {
    final db = await database;
    await db.delete(
      'hole_scores',
      where: 'game_id = ?',
      whereArgs: [id],
    );
    return await db.delete(
      'games',
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  // ゲーム情報の更新（スコアを除く）
  Future<int> updateGame(Game game) async {
    final db = await database;
    return await db.update(
      'games',
      game.toMap(),
      where: 'id = ?',
      whereArgs: [game.id],
    );
  }
}
