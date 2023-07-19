# mov2summary

このプロジェクトは、指定されたビデオ（特にYouTubeのビデオ）の要約を生成する CLI です。オープン AI のモデル `gpt-3.5-turbo` を使用して、ビデオの音声トランスクリプトを生成し、その後要約を作成します。

## 機能

- YouTube のビデオのダウンロード
- ローカルのビデオファイルの読み込み
- ビデオからの音声の抽出
- 音声のトランスクリプト化
- トランスクリプトの要約

## 必要なPythonライブラリ

このプロジェクトを実行するためには、以下の外部 Python ライブラリが必要です。
これらのライブラリは `pip` を使用してインストールできます。以下にインストールコマンドを示します。

```bash
pip install -r requirements.txt
```

## 使い方

`.env` ファイルを作成し、OpenAI の API キーを記述します。
このファイルは、プロジェクトのルートディレクトリに保存してください。以下に例を示します。

```
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
```

ここで、`YOUR_OPENAI_API_KEY`はあなたの OpenAI API キーのことです。

次に、以下のようにしてスクリプトを実行します。

```bash
python main.py YOUTUBE_VIDEO_URL
```

`YOUTUBE_VIDEO_URL`は要約したい YouTube のビデオの URL です。

オプションで、`--clean` フラグを指定することで、一時ファイルを削除することができます。一時ファイルは、ダウンロードしたビデオファイルや音声ファイルなどです。 `tmp` ディレクトリに保存されます。

```bash
python main.py YOUTUBE_VIDEO_URL --clean
```

YOUTUBE_VIDEO_URL を指定せずにスクリプトを実行すると、 GUI が起動します。GUI では、ローカルのビデオファイルを読み込むことができます。

```bash
python main.py
```

## 出力

ビデオの要約は Markdown 形式で出力され、ユーザーが選択した場所に保存されます。要約は次のようなセクションに分割されます。
1. タイトル: 要約全体のタイトル
2. 要約：トランスクリプトを要約したもの。このセクションはさらに複数の段階（depth）になっており、深い段階がより短い要約になります。
3. トランスクリプト：ビデオの音声をテキストに変換したもの。

## 注意事項
- OpenAI の API キーは、個々のユーザーにとって機密情報であり、安全に管理してください。
- YouTube の動画のダウンロードと変換には時間がかかる場合があります。
- 音声トランスクリプトの要約には、OpenAI の API を使用しています。そのため、動画の長さによっては、要約の生成に時間がかかる場合があります。
- 一部のビデオでは、音声のトランスクリプト化や要約がうまく行かない可能性があります。そのような場合、トランスクリプトや要約は生成されません。
- このスクリプトは、動画の要約を生成するために OpenAI の API を使用します。このため、適切な API キーを提供する必要があります。また、 **OpenAI の API は使用料金が発生しますので、その点をご了承ください。** 詳しくは、[OpenAI のサイト](https://openai.com/)をご覧ください。
- 動作確認してあるのは、Mac OS 13.3.1、Python のバージョンは 3.10.11 です。他の環境では動作しない可能性があります。
