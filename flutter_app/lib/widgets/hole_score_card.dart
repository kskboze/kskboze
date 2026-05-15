import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/game.dart';
import '../models/hole_score.dart';
import '../utils/app_theme.dart';
import '../utils/las_vegas_calculator.dart';

class HoleScoreCard extends StatefulWidget {
  final Game game;
  final HoleScore holeScore;
  final int cumulativeDelta;
  final bool birdieFlipEnabled;
  final ValueChanged<HoleScore> onChanged;

  const HoleScoreCard({
    super.key,
    required this.game,
    required this.holeScore,
    required this.cumulativeDelta,
    required this.birdieFlipEnabled,
    required this.onChanged,
  });

  @override
  State<HoleScoreCard> createState() => _HoleScoreCardState();
}

class _HoleScoreCardState extends State<HoleScoreCard> {
  late TextEditingController _a1Ctrl, _a2Ctrl, _b1Ctrl, _b2Ctrl, _parCtrl;
  late HoleScore _hole;

  @override
  void initState() {
    super.initState();
    _hole = widget.holeScore;
    _a1Ctrl = TextEditingController(text: _hole.scoreA1?.toString() ?? '');
    _a2Ctrl = TextEditingController(text: _hole.scoreA2?.toString() ?? '');
    _b1Ctrl = TextEditingController(text: _hole.scoreB1?.toString() ?? '');
    _b2Ctrl = TextEditingController(text: _hole.scoreB2?.toString() ?? '');
    _parCtrl = TextEditingController(text: _hole.parScore?.toString() ?? '4');
  }

  @override
  void dispose() {
    _a1Ctrl.dispose();
    _a2Ctrl.dispose();
    _b1Ctrl.dispose();
    _b2Ctrl.dispose();
    _parCtrl.dispose();
    super.dispose();
  }

  void _notify() {
    widget.onChanged(_hole);
  }

  void _updateScore(String field, String value) {
    final v = int.tryParse(value);
    setState(() {
      switch (field) {
        case 'a1':
          _hole = _hole.copyWith(scoreA1: v);
          break;
        case 'a2':
          _hole = _hole.copyWith(scoreA2: v);
          break;
        case 'b1':
          _hole = _hole.copyWith(scoreB1: v);
          break;
        case 'b2':
          _hole = _hole.copyWith(scoreB2: v);
          break;
        case 'par':
          _hole = _hole.copyWith(parScore: v ?? 4);
          // フリップ権利が無くなったらフリップを解除
          if (!LasVegasCalculator.canFlipA(_hole)) {
            _hole = _hole.copyWith(flipA: false);
          }
          if (!LasVegasCalculator.canFlipB(_hole)) {
            _hole = _hole.copyWith(flipB: false);
          }
          break;
      }
    });
    _notify();
  }

  void _toggleFlipA() {
    if (!LasVegasCalculator.canFlipA(_hole)) return;
    setState(() => _hole = _hole.copyWith(flipA: !_hole.flipA));
    _notify();
  }

  void _toggleFlipB() {
    if (!LasVegasCalculator.canFlipB(_hole)) return;
    setState(() => _hole = _hole.copyWith(flipB: !_hole.flipB));
    _notify();
  }

  @override
  Widget build(BuildContext context) {
    final comboA = LasVegasCalculator.getComboA(_hole);
    final comboB = LasVegasCalculator.getComboB(_hole);
    final delta = LasVegasCalculator.getHoleDelta(_hole);
    final canFlipA = widget.birdieFlipEnabled && LasVegasCalculator.canFlipA(_hole);
    final canFlipB = widget.birdieFlipEnabled && LasVegasCalculator.canFlipB(_hole);

    Color deltaColor = AppTheme.neutralColor;
    String deltaText = '-';
    if (delta != null) {
      if (delta > 0) {
        deltaColor = AppTheme.teamAColor;
        deltaText = '+$delta';
      } else if (delta < 0) {
        deltaColor = AppTheme.teamBColor;
        deltaText = '$delta';
      } else {
        deltaText = '0';
      }
    }

    Color cumulColor = AppTheme.neutralColor;
    String cumulText = '';
    final c = widget.cumulativeDelta;
    if (c > 0) {
      cumulColor = AppTheme.teamAColor;
      cumulText = '+$c';
    } else if (c < 0) {
      cumulColor = AppTheme.teamBColor;
      cumulText = '$c';
    } else {
      cumulText = '0';
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            // ホールヘッダー
            Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: AppTheme.primaryColor,
                    shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Text(
                      '${_hole.holeNumber}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 15,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                const Text('Par', style: TextStyle(fontSize: 13, color: Colors.grey)),
                const SizedBox(width: 4),
                SizedBox(
                  width: 48,
                  child: _scoreInput(_parCtrl, 'Par', (v) => _updateScore('par', v), maxVal: 5, minVal: 3),
                ),
                const Spacer(),
                // デルタ・累計
                if (delta != null) ...[
                  Text(
                    deltaText,
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: deltaColor),
                  ),
                  const SizedBox(width: 12),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: cumulColor.withAlpha(30),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: cumulColor.withAlpha(100)),
                    ),
                    child: Text(
                      '累計 $cumulText',
                      style: TextStyle(fontSize: 12, color: cumulColor, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 10),
            // チームA
            _teamRow(
              teamName: widget.game.teamAName,
              p1Name: widget.game.player1Name,
              p2Name: widget.game.player2Name,
              ctrl1: _a1Ctrl,
              ctrl2: _a2Ctrl,
              combo: comboA,
              canFlip: canFlipA,
              isFlipped: _hole.flipA,
              onFlip: _toggleFlipA,
              color: AppTheme.teamAColor,
              onScore1: (v) => _updateScore('a1', v),
              onScore2: (v) => _updateScore('a2', v),
            ),
            const SizedBox(height: 6),
            // チームB
            _teamRow(
              teamName: widget.game.teamBName,
              p1Name: widget.game.player3Name,
              p2Name: widget.game.player4Name,
              ctrl1: _b1Ctrl,
              ctrl2: _b2Ctrl,
              combo: comboB,
              canFlip: canFlipB,
              isFlipped: _hole.flipB,
              onFlip: _toggleFlipB,
              color: AppTheme.teamBColor,
              onScore1: (v) => _updateScore('b1', v),
              onScore2: (v) => _updateScore('b2', v),
            ),
          ],
        ),
      ),
    );
  }

  Widget _teamRow({
    required String teamName,
    required String p1Name,
    required String p2Name,
    required TextEditingController ctrl1,
    required TextEditingController ctrl2,
    required int? combo,
    required bool canFlip,
    required bool isFlipped,
    required VoidCallback onFlip,
    required Color color,
    required ValueChanged<String> onScore1,
    required ValueChanged<String> onScore2,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: color.withAlpha(15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withAlpha(60)),
      ),
      child: Row(
        children: [
          Container(
            width: 3,
            height: 36,
            decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(2)),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Row(
              children: [
                Expanded(child: _labeledInput(ctrl1, p1Name, onScore1)),
                const SizedBox(width: 6),
                Expanded(child: _labeledInput(ctrl2, p2Name, onScore2)),
              ],
            ),
          ),
          const SizedBox(width: 8),
          // コンボ表示
          SizedBox(
            width: 44,
            child: Text(
              combo != null ? '$combo' : '-',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
          ),
          // フリップボタン
          if (canFlip || isFlipped)
            GestureDetector(
              onTap: canFlip ? onFlip : null,
              child: Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  color: isFlipped ? color : Colors.transparent,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: canFlip ? color : Colors.grey),
                ),
                child: Icon(
                  Icons.swap_horiz,
                  size: 18,
                  color: isFlipped ? Colors.white : (canFlip ? color : Colors.grey),
                ),
              ),
            )
          else
            const SizedBox(width: 26),
        ],
      ),
    );
  }

  Widget _labeledInput(TextEditingController ctrl, String label, ValueChanged<String> onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 10, color: Colors.grey)),
        const SizedBox(height: 2),
        TextField(
          controller: ctrl,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
          decoration: const InputDecoration(
            isDense: true,
            contentPadding: EdgeInsets.symmetric(horizontal: 4, vertical: 6),
          ),
          onChanged: onChanged,
        ),
      ],
    );
  }

  Widget _scoreInput(
    TextEditingController ctrl,
    String label,
    ValueChanged<String> onChanged, {
    int minVal = 1,
    int maxVal = 20,
  }) {
    return TextField(
      controller: ctrl,
      keyboardType: TextInputType.number,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      textAlign: TextAlign.center,
      style: const TextStyle(fontSize: 14),
      decoration: const InputDecoration(
        isDense: true,
        contentPadding: EdgeInsets.symmetric(horizontal: 4, vertical: 6),
      ),
      onChanged: onChanged,
    );
  }
}
