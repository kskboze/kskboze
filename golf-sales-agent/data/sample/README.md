# サンプルCSVの作り方

このフォルダは、取り込みテスト用のCSVを置く場所です。

動作確認用のデータは、次のコマンドで自動生成できます（このフォルダには保存されず、
データベースに直接入ります）。

```
python3 scripts/generate_sample_data.py
```

実データのCSVを試したい場合は、ここに置いてから次のコマンドで取り込めます。

```
python3 -m app.cli import visits data/sample/来場実績.csv
```
