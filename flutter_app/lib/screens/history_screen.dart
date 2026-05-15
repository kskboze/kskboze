import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../db/database_helper.dart';
import '../models/game.dart';
import '../utils/app_theme.dart';
import '../utils/las_vegas_calculator.dart';
import 'result_screen.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<Game> _games = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadGames();
  }

  Future<void> _loadGames() async {
    setState(() => _loading = true);
    final games = await DatabaseHelper.instance.getAllGames();
    // 各ゲームのホールスコアを読み込む
    final gamesWithScores = <Game>[];
    for (final g in games) {
      if (g.id != null) {
        final full = await DatabaseHelper.instance.getGame(g.id!);
        if (full != null) gamesWithScores.add(full);
      }
    }
    setState(() {
      _games = gamesWithScores;
      _loading = false;
    });
  }

  Future<void> _deleteGame(Game game) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('ゲームを削除'),
        content: const Text('このゲームの記録を削除しますか？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('キャンセル'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('削除', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirmed == true && game.id != null) {
      await DatabaseHelper.instance.deleteGame(game.id!);
      await _loadGames();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('ゲーム履歴'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadGames,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _games.isEmpty
              ? _buildEmptyState()
              : RefreshIndicator(
                  onRefresh: _loadGames,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(8),
                    itemCount: _games.length,
                    itemBuilder: (context, index) =>
                        _buildGameTile(_games[index]),
                  ),
                ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.history, size: 72, color: Colors.grey[300]),
          const SizedBox(height: 16),
          Text(
            'まだゲームが保存されていません',
            style: TextStyle(fontSize: 16, color: Colors.grey[500]),
          ),
          const SizedBox(height: 8),
          Text(
            'ゲームを完了すると履歴が表示されます',
            style: TextStyle(fontSize: 13, color: Colors.grey[400]),
          ),
        ],
      ),
    );
  }

  Widget _buildGameTile(Game game) {
    final dateFmt = DateFormat('yyyy/M/d HH:mm');
    final numFmt = NumberFormat('#,###');
    final totalDelta =
        LasVegasCalculator.getTotalDelta(game.holeScores);
    final settlement = LasVegasCalculator.calculateSettlement(
        game.holeScores, game.betPerPoint);
    final completedHoles = game.holeScores.where((h) => h.isComplete).length;

    final aWins = totalDelta > 0;
    final isDraw = totalDelta == 0;
    final winnerTeam =
        isDraw ? '引き分け' : (aWins ? game.teamAName : game.teamBName);
    final winnerColor = isDraw
        ? AppTheme.neutralColor
        : (aWins ? AppTheme.teamAColor : AppTheme.teamBColor);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => ResultScreen(game: game),
            ),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              // チームカラーインジケーター
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: winnerColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(Icons.sports_golf, color: winnerColor, size: 26),
              ),
              const SizedBox(width: 12),

              // ゲーム情報
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${game.teamAName} vs ${game.teamBName}',
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '${game.player1Name}・${game.player2Name}  /  '
                      '${game.player3Name}・${game.player4Name}',
                      style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(Icons.schedule, size: 12, color: Colors.grey[400]),
                        const SizedBox(width: 2),
                        Text(
                          dateFmt.format(game.createdAt),
                          style:
                              TextStyle(fontSize: 11, color: Colors.grey[500]),
                        ),
                        const SizedBox(width: 8),
                        Icon(Icons.flag, size: 12, color: Colors.grey[400]),
                        const SizedBox(width: 2),
                        Text(
                          '$completedHoles/${game.totalHoles}H',
                          style:
                              TextStyle(fontSize: 11, color: Colors.grey[500]),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              // 結果
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    winnerTeam,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: winnerColor,
                    ),
                  ),
                  if (!isDraw) ...[
                    const SizedBox(height: 2),
                    Text(
                      '¥${numFmt.format(settlement)}',
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.accentDarkColor,
                      ),
                    ),
                  ],
                ],
              ),

              // 削除ボタン
              IconButton(
                icon: const Icon(Icons.delete_outline, color: Colors.red),
                iconSize: 20,
                onPressed: () => _deleteGame(game),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
