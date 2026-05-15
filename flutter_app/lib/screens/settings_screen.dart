import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../utils/app_theme.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _betCtrl = TextEditingController();
  bool _defaultBirdieFlip = true;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _betCtrl.text = (prefs.getInt('default_bet') ?? 100).toString();
      _defaultBirdieFlip = prefs.getBool('default_birdie_flip') ?? true;
      _loading = false;
    });
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    final bet = int.tryParse(_betCtrl.text) ?? 100;
    await prefs.setInt('default_bet', bet);
    await prefs.setBool('default_birdie_flip', _defaultBirdieFlip);

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('設定を保存しました'),
        backgroundColor: AppTheme.primaryColor,
      ),
    );
  }

  @override
  void dispose() {
    _betCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('設定'),
        actions: [
          TextButton(
            onPressed: _saveSettings,
            child: const Text(
              '保存',
              style: TextStyle(
                  color: Colors.white, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // デフォルト設定
                Card(
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
                                color: AppTheme.primaryColor,
                                borderRadius: BorderRadius.circular(2),
                              ),
                            ),
                            const SizedBox(width: 8),
                            const Text(
                              'デフォルト設定',
                              style: TextStyle(
                                  fontSize: 17, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),

                        // 賭け金
                        TextFormField(
                          controller: _betCtrl,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: '1ポイントあたりの賭け金（円）',
                            prefixIcon: Icon(Icons.attach_money),
                            helperText: 'ゲーム設定画面のデフォルト値として使用されます',
                          ),
                        ),

                        const Divider(height: 24),

                        // バーディーフリップ
                        Row(
                          children: [
                            const Icon(Icons.flip,
                                color: AppTheme.primaryColor, size: 20),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    'バーディーフリップ（デフォルト）',
                                    style: TextStyle(
                                        fontSize: 15,
                                        fontWeight: FontWeight.w500),
                                  ),
                                  Text(
                                    '新しいゲームでのデフォルト値',
                                    style: TextStyle(
                                        fontSize: 12, color: Colors.grey[600]),
                                  ),
                                ],
                              ),
                            ),
                            Switch(
                              value: _defaultBirdieFlip,
                              onChanged: (v) =>
                                  setState(() => _defaultBirdieFlip = v),
                              activeColor: AppTheme.primaryColor,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 12),

                // ルール説明
                Card(
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
                                color: AppTheme.accentColor,
                                borderRadius: BorderRadius.circular(2),
                              ),
                            ),
                            const SizedBox(width: 8),
                            const Text(
                              'ラスベガスルール',
                              style: TextStyle(
                                  fontSize: 17, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        _RuleItem(
                          icon: Icons.people,
                          title: 'チーム編成',
                          description: '4人を2チームに分ける（A/B各2人）',
                        ),
                        _RuleItem(
                          icon: Icons.calculate,
                          title: '2桁数字',
                          description:
                              '各ホールでチームの2人のスコアを並べ、\n小さい方を十の位に置いた2桁数字を作る\n例：4と6 → 46',
                        ),
                        _RuleItem(
                          icon: Icons.compare_arrows,
                          title: '差が点数',
                          description:
                              '2チームの2桁数字の差がそのホールの点数\n例：A=46, B=57 → Aチームが11点獲得',
                        ),
                        _RuleItem(
                          icon: Icons.flip,
                          title: 'フリップルール',
                          description:
                              'バーディー以下が出た場合、そのチームは\n2桁数字を逆にできる\n例：46 → 64',
                        ),
                        _RuleItem(
                          icon: Icons.attach_money,
                          title: '精算',
                          description:
                              '全ホール終了後、累計点数の差 × 賭け金が\n精算金額となる',
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 24),

                ElevatedButton(
                  onPressed: _saveSettings,
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  child: const Text('設定を保存'),
                ),

                const SizedBox(height: 16),
              ],
            ),
    );
  }
}

class _RuleItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final String description;

  const _RuleItem({
    required this.icon,
    required this.title,
    required this.description,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: AppTheme.accentDarkColor),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  description,
                  style: TextStyle(fontSize: 13, color: Colors.grey[600]),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
