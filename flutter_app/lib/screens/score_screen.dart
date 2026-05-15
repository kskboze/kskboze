import 'package:flutter/material.dart';
import '../db/database_helper.dart';
import '../models/game.dart';
import '../models/hole_score.dart';
import '../utils/app_theme.dart';
import '../utils/las_vegas_calculator.dart';
import '../widgets/hole_score_card.dart';
import '../widgets/score_summary.dart';
import 'result_screen.dart';

class ScoreScreen extends StatefulWidget {
  final Game game;

  const ScoreScreen({super.key, required this.game});

  @override
  State<ScoreScreen> createState() => _ScoreScreenState();
}

class _ScoreScreenState extends State<ScoreScreen> {
  late List<HoleScore> _holeScores;
  late Game _game;

  @override
  void initState() {
    super.initState();
    _game = widget.game;
    _holeScores = List<HoleScore>.from(_game.holeScores);
  }

  void _onHoleScoreChanged(int index, HoleScore updatedHole) async {
    await DatabaseHelper.instance.updateHoleScore(updatedHole);
    setState(() {
      _holeScores[index] = updatedHole;
    });
  }

  void _goToResult() {
    final updatedGame = _game.copyWith(holeScores: _holeScores);
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ResultScreen(game: updatedGame, isNewGame: true),
      ),
    );
  }

  int get _completedHoles => _holeScores.where((h) => h.isComplete).length;

  @override
  Widget build(BuildContext context) {
    final totalDelta = LasVegasCalculator.getTotalDelta(_holeScores);
    final settlement = LasVegasCalculator.calculateSettlement(
        _holeScores, _game.betPerPoint);

    return Scaffold(
      appBar: AppBar(
        title: Text('${_game.teamAName} vs ${_game.teamBName}'),
        actions: [
          TextButton(
            onPressed: _goToResult,
            child: const Text(
              '結果を見る',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // スコアサマリーバナー
          ScoreSummary(
            game: _game,
            holeScores: _holeScores,
            totalDelta: totalDelta,
            settlement: settlement,
            completedHoles: _completedHoles,
          ),

          // ホール一覧
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.only(bottom: 80),
              itemCount: _holeScores.length,
              itemBuilder: (context, index) {
                final hole = _holeScores[index];
                final cumulativeDeltas =
                    LasVegasCalculator.getCumulativeDeltas(_holeScores);
                final cumulativeDelta =
                    index < cumulativeDeltas.length ? cumulativeDeltas[index] : 0;

                return HoleScoreCard(
                  game: _game,
                  holeScore: hole,
                  cumulativeDelta: cumulativeDelta,
                  birdieFlipEnabled: _game.birdieFlipEnabled,
                  onChanged: (updated) => _onHoleScoreChanged(index, updated),
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _goToResult,
        icon: const Icon(Icons.bar_chart),
        label: const Text('結果を見る'),
        backgroundColor: AppTheme.accentColor,
      ),
    );
  }
}
