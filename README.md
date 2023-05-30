# mov2summary

この Python プログラムは、与えられた動画の要約を作成するCLIツールです。
動画の音声トラックをトランスクリプトに変換し、それを OpenAI の GPT-3.5 モデルを使用して要約します。
ローカルの動画ファイルと YouTube の動画 URL の両方を対象にすることができます。

## 必要なライブラリ

- argparse
- hashlib
- os
- re
- shutil
- tkinter
- concurrent.futures
- pytube
- ffmpeg-python
- openai

上記のライブラリが必要です。`pip install` コマンドを使ってインストールできます。
ffmeg を別途インストールする必要があります。

## 使い方

1. コマンドライン引数として OpenAI の API キーを指定します。
2. YouTube の動画の URL 、 未指定の場合はローカルの動画ファイルを選択できます。

### 使い方

YouTube 動画の要約:

```bash
python ./package/main.py YOUR_OPENAI_API_KEY https://www.youtube.com/watch?v=abc123xyz
```

ローカルの動画の要約:

```bash
python ./package/main.py YOUR_OPENAI_API_KEY
```

ローカルの動画ファイルを要約する場合、ファイルを選択するダイアログが表示されます。

## 注意点

- OpenAI の API キーは、個々のユーザーにとって機密情報であり、安全に管理してください。
- YouTube の動画のダウンロードと変換には時間がかかる場合があります。
- 音声トランスクリプトの要約には、OpenAI の API を使用しています。そのため、動画の長さによっては、要約の生成に時間がかかる場合があります。
