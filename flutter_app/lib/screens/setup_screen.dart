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

  @override
  void initState() {
    super.initState();
    _loadDefaults();
  }

  Future<void> _loadDefaults() async {
    final prefs = await SharedPreferences.getInstance();
    final defaultBet = prefs.getInt('default_bet') ?? 100;
    setState(() {
      _betCtrl.text = defaultBet.toString();
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

    final bet = int.tryParse(_betCtrl.text) ?? 100;
    final game = Game(
      teamAName: _teamANameCtrl.text.trim(),
      teamBName: _teamBNameCtrl.text.trim(),
      player1Name: _p1Ctrl.text.trim(),
      player2Name: _p2Ctrl.text.trim(),
      player3Name: _p3Ctrl.text.trim(),
      player4Name: _p4Ctrl.text.trim(),
      betPerPoint: bet,
      birdieFlipEnabled: _birdieFlip,
      totalHoles: _totalHoles,
      createdAt: DateTime.now(),
    );

    final id = await DatabaseHelper.instance.insertGame(game);
    final savedGame = await DatabaseHelper.instance.getGame(id);
    if (!mounted || savedGame == null) return;

    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => ScoreScreen(game: savedGame)),
    );
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
            const SizedBox(height: 12),
            _sectionCard(
              title: 'ゲーム設定',
              color: AppTheme.primaryColor,
              children: [
                // ホール数
                Row(
                  children: [
                    const Icon(Icons.flag, color: AppTheme.primaryColor, size: 20),
                    const SizedBox(width: 8),
                    const Text('ホール数', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w500)),
                    const Spacer(),
                    SegmentedButton<int>(
                      segments: const [
                        ButtonSegment(value: 9, label: Text('9H')),
                        ButtonSegment(value: 18, label: Text('18H')),
                      ],
                      selected: {_totalHoles},
                      onSelectionChanged: (s) => setState(() => _totalHoles = s.first),
                      style: SegmentedButton.styleFrom(
                        selectedBackgroundColor: AppTheme.primaryColor,
                        selectedForegroundColor: Colors.white,
                      ),
                    ),
                  ],
                ),
                const Divider(height: 24),
                // 賭け金
                TextFormField(
                  controller: _betCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: '1ポイントあたりの賭け金（円）',
                    prefixIcon: Icon(Icons.attach_money),
                  ),
                  validator: (v) {
                    if (v == null || v.isEmpty) return '賭け金を入力してください';
                    if (int.tryParse(v) == null || int.parse(v) < 0) return '正しい金額を入力してください';
                    return null;
                  },
                ),
                const Divider(height: 24),
                // バーディーフリップ
                Row(
                  children: [
                    const Icon(Icons.flip, color: AppTheme.primaryColor, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('バーディーフリップ', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w500)),
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
                textStyle: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
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
                Text(title, style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: color)),
              ],
            ),
            const SizedBox(height: 16),
            ...children,
          ],
        ),
      ),
    );
  }

  Widget _textField(TextEditingController ctrl, String label, IconData icon) {
    return TextFormField(
      controller: ctrl,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
      ),
      validator: (v) => (v == null || v.trim().isEmpty) ? '$labelを入力してください' : null,
    );
  }
}
