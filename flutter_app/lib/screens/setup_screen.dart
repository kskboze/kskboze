import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../db/database_helper.dart';
import '../models/game.dart';
import '../utils/app_theme.dart';
import 'score_screen.dart';

class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  final _formKey = GlobalKey<FormState>();

  final _teamANameCtrl = TextEditingController(text: 'チームA');
  final _teamBNameCtrl = TextEditingController(text: 'チームB');
  final _p1Ctrl = TextEditingController(text: 'プレイヤー1');
  final _p2Ctrl = TextEditingController(text: 'プレイヤー2');
  final _p3Ctrl = TextEditingController(text: 'プレイヤー3');
  final _p4Ctrl = TextEditingController(text: 'プレイヤー4');
  final _betCtrl = TextEditingController(text: '100');

  int _totalHoles = 18;
  bool _birdieFlip = true;
  TeamFormationMode _teamMode = TeamFormationMode.fixed;

  @override
  void initState() {
    super.initState();
    _loadDefaults();
  }

  Future<void> _loadDefaults() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _betCtrl.text = (prefs.getInt('default_bet') ?? 100).toString();
    });
  }

  @override
  void dispose() {
    _teamANameCtrl.dispose();
    _teamBNameCtrl.dispose();
    _p1Ctrl.dispose();
    _p2Ctrl.dispose();
    _p3Ctrl.dispose();
    _p4Ctrl.dispose();
    _betCtrl.dispose();
    super.dispose();
  }

  Future<void> _startGame() async {
    if (!_formKey.currentState!.validate()) return;

    final p1 = _p1Ctrl.text.trim();
    final p2 = _p2Ctrl.text.trim();
    final p3 = _p3Ctrl.text.trim();
    final p4 = _p4Ctrl.text.trim();

    String teamAName, teamBName;
    switch (_teamMode) {
      case TeamFormationMode.fixed:
        teamAName = _teamANameCtrl.text.trim();
        teamBName = _teamBNameCtrl.text.trim();
        break;
      case TeamFormationMode.rotation:
        teamAName = 'Aサイド';
        teamBName = 'Bサイド';
        break;
      case TeamFormationMode.oneAndFour:
        teamAName = '$p1 & $p4';
        teamBName = '$p2 & $p3';
        break;
    }

    final bet = int.tryParse(_betCtrl.text) ?? 100;
    final game = Game(
      teamAName: teamAName,
      teamBName: teamBName,
      player1Name: p1,
      player2Name: p2,
      player3Name: p3,
      player4Name: p4,
      betPerPoint: bet,
      birdieFlipEnabled: _birdieFlip,
      totalHoles: _totalHoles,
      teamFormationMode: _teamMode,
      createdAt: DateTime.now(),
    );

    try {
      final id = await DatabaseHelper.instance.insertGame(game);
      final savedGame = await DatabaseHelper.instance.getGame(id);
      if (!mounted || savedGame == null) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => ScoreScreen(game: savedGame)),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('エラーが発生しました: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('ゲーム設定')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // ─── チーム編成モード ───
            _sectionCard(
              title: 'チーム編成モード',
              color: AppTheme.primaryColor,
              children: [
                _modeOption(
                  mode: TeamFormationMode.fixed,
                  icon: Icons.group,
                  preview: null,
                ),
                const Divider(height: 8),
                _modeOption(
                  mode: TeamFormationMode.rotation,
                  icon: Icons.sync,
                  preview: _rotationPreview(),
                ),
                const Divider(height: 8),
                _modeOption(
                  mode: TeamFormationMode.oneAndFour,
                  icon: Icons.swap_horiz,
                  preview: _oneAndFourPreview(),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // ─── プレイヤー入力 ───
            if (_teamMode == TeamFormationMode.fixed) ...[
              _sectionCard(
                title: 'チームA',
                color: AppTheme.teamAColor,
                children: [
                  _textField(_teamANameCtrl, 'チーム名', Icons.group),
                  const SizedBox(height: 12),
                  _textField(_p1Ctrl, 'プレイヤー1', Icons.person),
                  const SizedBox(height: 12),
                  _textField(_p2Ctrl, 'プレイヤー2', Icons.person),
                ],
              ),
              const SizedBox(height: 12),
              _sectionCard(
                title: 'チームB',
                color: AppTheme.teamBColor,
                children: [
                  _textField(_teamBNameCtrl, 'チーム名', Icons.group),
                  const SizedBox(height: 12),
                  _textField(_p3Ctrl, 'プレイヤー3', Icons.person),
                  const SizedBox(height: 12),
                  _textField(_p4Ctrl, 'プレイヤー4', Icons.person),
                ],
              ),
            ] else
              _sectionCard(
                title: 'プレイヤー',
                color: AppTheme.primaryColor,
                children: [
                  Row(
                    children: [
                      Expanded(child: _numberedPlayer(_p1Ctrl, '①', AppTheme.teamAColor)),
                      const SizedBox(width: 10),
                      Expanded(child: _numberedPlayer(_p2Ctrl, '②', AppTheme.teamBColor)),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(child: _numberedPlayer(_p3Ctrl, '③', AppTheme.teamBColor)),
                      const SizedBox(width: 10),
                      Expanded(child: _numberedPlayer(_p4Ctrl, '④', AppTheme.teamAColor)),
                    ],
                  ),
                  if (_teamMode == TeamFormationMode.oneAndFour) ...[
                    const SizedBox(height: 12),
                    _teamPreviewChips(),
                  ],
                ],
              ),
            const SizedBox(height: 12),

            // ─── ゲーム設定 ───
            _sectionCard(
              title: 'ゲーム設定',
              color: AppTheme.primaryColor,
              children: [
                Row(
                  children: [
                    const Icon(Icons.flag, color: AppTheme.primaryColor, size: 20),
                    const SizedBox(width: 8),
                    const Text('ホール数',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.w500)),
                    const Spacer(),
                    SegmentedButton<int>(
                      segments: const [
                        ButtonSegment(value: 9, label: Text('9H')),
                        ButtonSegment(value: 18, label: Text('18H')),
                      ],
                      selected: {_totalHoles},
                      onSelectionChanged: (s) =>
                          setState(() => _totalHoles = s.first),
                      style: SegmentedButton.styleFrom(
                        selectedBackgroundColor: AppTheme.primaryColor,
                        selectedForegroundColor: Colors.white,
                      ),
                    ),
                  ],
                ),
                const Divider(height: 24),
                TextFormField(
                  controller: _betCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: '1ポイントあたりの賭け金（円）',
                    prefixIcon: Icon(Icons.attach_money),
                  ),
                  validator: (v) {
                    if (v == null || v.isEmpty) return '賭け金を入力してください';
                    if (int.tryParse(v) == null || int.parse(v) < 0) {
                      return '正しい金額を入力してください';
                    }
                    return null;
                  },
                ),
                const Divider(height: 24),
                Row(
                  children: [
                    const Icon(Icons.flip, color: AppTheme.primaryColor, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('バーディーフリップ',
                              style: TextStyle(
                                  fontSize: 15, fontWeight: FontWeight.w500)),
                          Text(
                            'バーディー以下で数字を逆にできる',
                            style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                          ),
                        ],
                      ),
                    ),
                    Switch(
                      value: _birdieFlip,
                      onChanged: (v) => setState(() => _birdieFlip = v),
                      activeColor: AppTheme.primaryColor,
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _startGame,
              icon: const Icon(Icons.sports_golf),
              label: const Text('ゲーム開始'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                textStyle:
                    const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  // ── チーム編成モード選択行 ──
  Widget _modeOption({
    required TeamFormationMode mode,
    required IconData icon,
    required Widget? preview,
  }) {
    final selected = _teamMode == mode;
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: () => setState(() => _teamMode = mode),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Radio<TeamFormationMode>(
              value: mode,
              groupValue: _teamMode,
              onChanged: (v) => setState(() => _teamMode = v!),
              activeColor: AppTheme.primaryColor,
              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            const SizedBox(width: 4),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Icon(icon,
                          size: 16,
                          color: selected
                              ? AppTheme.primaryColor
                              : Colors.grey[600]),
                      const SizedBox(width: 6),
                      Text(
                        mode.displayName,
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          color: selected ? AppTheme.primaryColor : Colors.black87,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    mode.description,
                    style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                  ),
                  if (selected && preview != null) ...[
                    const SizedBox(height: 8),
                    preview,
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ローテーション説明プレビュー
  Widget _rotationPreview() {
    final p1 = _p1Ctrl.text.isEmpty ? '①' : _p1Ctrl.text;
    final p2 = _p2Ctrl.text.isEmpty ? '②' : _p2Ctrl.text;
    final p3 = _p3Ctrl.text.isEmpty ? '③' : _p3Ctrl.text;
    final p4 = _p4Ctrl.text.isEmpty ? '④' : _p4Ctrl.text;

    final rows = [
      ('H1, H4, H7...', '$p1&$p2 vs $p3&$p4'),
      ('H2, H5, H8...', '$p1&$p3 vs $p2&$p4'),
      ('H3, H6, H9...', '$p1&$p4 vs $p2&$p3'),
    ];

    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.primaryColor.withAlpha(15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.primaryColor.withAlpha(50)),
      ),
      child: Column(
        children: rows
            .map((r) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 80,
                        child: Text(r.$1,
                            style: TextStyle(
                                fontSize: 11, color: Colors.grey[600])),
                      ),
                      Text(r.$2,
                          style: const TextStyle(
                              fontSize: 12, fontWeight: FontWeight.w500)),
                    ],
                  ),
                ))
            .toList(),
      ),
    );
  }

  // 1&4 vs 2&3 説明プレビュー
  Widget _oneAndFourPreview() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: AppTheme.primaryColor.withAlpha(15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.primaryColor.withAlpha(50)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _chip('① & ④', AppTheme.teamAColor),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 8),
            child: Text('vs', style: TextStyle(color: Colors.grey)),
          ),
          _chip('② & ③', AppTheme.teamBColor),
        ],
      ),
    );
  }

  Widget _teamPreviewChips() {
    final p1 = _p1Ctrl.text.isEmpty ? '①' : _p1Ctrl.text;
    final p2 = _p2Ctrl.text.isEmpty ? '②' : _p2Ctrl.text;
    final p3 = _p3Ctrl.text.isEmpty ? '③' : _p3Ctrl.text;
    final p4 = _p4Ctrl.text.isEmpty ? '④' : _p4Ctrl.text;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _chip('$p1 & $p4', AppTheme.teamAColor),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 8),
          child: Text('vs', style: TextStyle(color: Colors.grey)),
        ),
        _chip('$p2 & $p3', AppTheme.teamBColor),
      ],
    );
  }

  Widget _chip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withAlpha(20),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withAlpha(80)),
      ),
      child: Text(label,
          style: TextStyle(
              fontSize: 12, color: color, fontWeight: FontWeight.w600)),
    );
  }

  Widget _numberedPlayer(
      TextEditingController ctrl, String number, Color color) {
    return TextFormField(
      controller: ctrl,
      decoration: InputDecoration(
        labelText: 'プレイヤー$number',
        prefixIcon: CircleAvatar(
          radius: 12,
          backgroundColor: color.withAlpha(30),
          child: Text(number,
              style:
                  TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.bold)),
        ),
      ),
      validator: (v) =>
          (v == null || v.trim().isEmpty) ? 'プレイヤー名を入力してください' : null,
    );
  }

  Widget _sectionCard({
    required String title,
    required Color color,
    required List<Widget> children,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 4,
                  height: 20,
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 8),
                Text(title,
                    style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                        color: color)),
              ],
            ),
            const SizedBox(height: 16),
            ...children,
          ],
        ),
      ),
    );
  }

  Widget _textField(
      TextEditingController ctrl, String label, IconData icon) {
    return TextFormField(
      controller: ctrl,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
      ),
      validator: (v) =>
          (v == null || v.trim().isEmpty) ? '$labelを入力してください' : null,
    );
  }
}
