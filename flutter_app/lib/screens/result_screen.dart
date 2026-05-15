import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/game.dart';
import '../models/hole_score.dart';
import '../utils/app_theme.dart';
import '../utils/las_vegas_calculator.dart';

class ResultScreen extends StatelessWidget {
  final Game game;
  final bool isNewGame;

  const ResultScreen({super.key, required this.game, this.isNewGame = false});

  @override
  Widget build(BuildContext context) {
    final holeScores = game.holeScores;
    final totalDelta = LasVegasCalculator.getTotalDelta(holeScores);
    final settlement = LasVegasCalculator.calculateSettlement(
        holeScores, game.betPerPoint);
    final cumulativeDeltas =
        LasVegasCalculator.getCumulativeDeltas(holeScores);

    final aWins = totalDelta > 0;
    final isDraw = totalDelta == 0;
    final winnerTeam = isDraw ? '引き分け' : (aWins ? game.teamAName : game.teamBName);
    final loserTeam = aWins ? game.teamBName : game.teamAName;
    final winnerColor = aWins ? AppTheme.teamAColor : AppTheme.teamBColor;

    final fmt = NumberFormat('#,###');
    final dateFmt = DateFormat('yyyy年M月d日 HH:mm');

    return Scaffold(
      appBar: AppBar(
        title: const Text('ゲーム結果'),
        leading: isNewGame
            ? IconButton(
                icon: const Icon(Icons.home),
                onPressed: () {
                  Navigator.of(context).popUntil((route) => route.isFirst);
                },
              )
            : null,
      ),
      body: ListView(
        children: [
          // 勝者バナー
          Container(
            width: double.infinity,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: isDraw
                    ? [AppTheme.neutralColor, AppTheme.neutralColor]
                    : [winnerColor.withOpacity(0.8), winnerColor],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                Icon(
                  isDraw ? Icons.handshake : Icons.emoji_events,
                  size: 56,
                  color: Colors.white,
                ),
                const SizedBox(height: 8),
                Text(
                  isDraw ? '引き分け!' : '🏆 $winnerTeam 勝利!',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                if (!isDraw) ...[
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      '$loserTeam → $winnerTeam  ¥${fmt.format(settlement)}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 4),
                Text(
                  dateFmt.format(game.createdAt),
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.7),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),

          // スコア概要
          Padding(
            padding: const EdgeInsets.all(16),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'スコア概要',
                      style: TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _StatItem(
                          label: game.teamAName,
                          value: totalDelta > 0
                              ? '+$totalDelta pt'
                              : (totalDelta == 0 ? '0 pt' : '${totalDelta} pt'),
                          color: AppTheme.teamAColor,
                        ),
                        Container(
                          width: 1,
                          height: 40,
                          color: Colors.grey[300],
                        ),
                        _StatItem(
                          label: game.teamBName,
                          value: totalDelta < 0
                              ? '+${totalDelta.abs()} pt'
                              : (totalDelta == 0
                                  ? '0 pt'
                                  : '${-totalDelta} pt'),
                          color: AppTheme.teamBColor,
                        ),
                        Container(
                          width: 1,
                          height: 40,
                          color: Colors.grey[300],
                        ),
                        _StatItem(
                          label: '精算金額',
                          value: '¥${fmt.format(settlement)}',
                          color: AppTheme.accentDarkColor,
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        Text(
                          '${game.player1Name} / ${game.player2Name}',
                          style:
                              TextStyle(fontSize: 12, color: Colors.grey[600]),
                        ),
                        Text(
                          '${game.player3Name} / ${game.player4Name}',
                          style:
                              TextStyle(fontSize: 12, color: Colors.grey[600]),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),

          // ホール別スコアテーブル
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Padding(
                    padding: EdgeInsets.all(16),
                    child: Text(
                      'ホール別スコア',
                      style: TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                  ),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      headingRowColor: WidgetStateProperty.all(
                        AppTheme.primaryColor.withOpacity(0.1),
                      ),
                      columns: [
                        const DataColumn(label: Text('H')),
                        DataColumn(
                            label: Text(
                          game.teamAName,
                          style: const TextStyle(color: AppTheme.teamAColor),
                        )),
                        DataColumn(
                            label: Text(
                          game.teamBName,
                          style: const TextStyle(color: AppTheme.teamBColor),
                        )),
                        const DataColumn(label: Text('差')),
                        const DataColumn(label: Text('累計')),
                      ],
                      rows: _buildRows(holeScores, cumulativeDeltas),
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // ホームへ戻るボタン
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: ElevatedButton.icon(
              onPressed: () {
                Navigator.of(context).popUntil((route) => route.isFirst);
              },
              icon: const Icon(Icons.home),
              label: const Text('ホームへ戻る'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),

          const SizedBox(height: 24),
        ],
      ),
    );
  }

  List<DataRow> _buildRows(
      List<HoleScore> holeScores, List<int> cumulativeDeltas) {
    return holeScores.asMap().entries.map((entry) {
      final i = entry.key;
      final hole = entry.value;
      final comboA = LasVegasCalculator.getComboA(hole);
      final comboB = LasVegasCalculator.getComboB(hole);
      final delta = LasVegasCalculator.getHoleDelta(hole);
      final cumulative = i < cumulativeDeltas.length ? cumulativeDeltas[i] : 0;

      Color deltaColor = Colors.grey;
      if (delta != null) {
        if (delta > 0) deltaColor = AppTheme.teamAColor;
        if (delta < 0) deltaColor = AppTheme.teamBColor;
      }

      return DataRow(cells: [
        DataCell(Text(
          '${hole.holeNumber}',
          style: const TextStyle(fontWeight: FontWeight.bold),
        )),
        DataCell(Text(
          comboA != null ? '$comboA' : '-',
          style: const TextStyle(color: AppTheme.teamAColor),
        )),
        DataCell(Text(
          comboB != null ? '$comboB' : '-',
          style: const TextStyle(color: AppTheme.teamBColor),
        )),
        DataCell(Text(
          delta != null
              ? (delta > 0 ? '+$delta' : '$delta')
              : '-',
          style: TextStyle(
            color: deltaColor,
            fontWeight: FontWeight.bold,
          ),
        )),
        DataCell(Text(
          cumulative > 0
              ? '+$cumulative'
              : '$cumulative',
          style: TextStyle(
            color: cumulative > 0
                ? AppTheme.teamAColor
                : (cumulative < 0 ? AppTheme.teamBColor : Colors.grey),
          ),
        )),
      ]);
    }).toList();
  }
}

class _StatItem extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _StatItem({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          label,
          style: TextStyle(fontSize: 12, color: Colors.grey[600]),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
      ],
    );
  }
}
