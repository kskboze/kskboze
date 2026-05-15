import 'package:flutter/material.dart';
import '../models/game.dart';
import '../models/hole_score.dart';
import '../utils/app_theme.dart';

class ScoreSummary extends StatelessWidget {
  final Game game;
  final List<HoleScore> holeScores;
  final int totalDelta;
  final int settlement;
  final int completedHoles;

  const ScoreSummary({
    super.key,
    required this.game,
    required this.holeScores,
    required this.totalDelta,
    required this.settlement,
    required this.completedHoles,
  });

  @override
  Widget build(BuildContext context) {
    String leadText;
    if (totalDelta > 0) {
      leadText = '${game.teamAName} リード +$totalDelta';
    } else if (totalDelta < 0) {
      leadText = '${game.teamBName} リード +${totalDelta.abs()}';
    } else {
      leadText = '同点';
    }

    return Container(
      margin: const EdgeInsets.fromLTRB(8, 8, 8, 0),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppTheme.primaryDarkColor, AppTheme.primaryColor],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: AppTheme.primaryColor.withAlpha(76),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  leadText,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '$completedHoles / ${game.totalHoles} ホール完了',
                  style: const TextStyle(color: Colors.white70, fontSize: 12),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              const Text('精算額', style: TextStyle(color: Colors.white70, fontSize: 11)),
              Text(
                '¥${_fmt(settlement)}',
                style: const TextStyle(
                  color: AppTheme.accentColor,
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _fmt(int n) {
    final s = n.toString();
    final buf = StringBuffer();
    for (int i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) buf.write(',');
      buf.write(s[i]);
    }
    return buf.toString();
  }
}
