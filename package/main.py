# -*- coding: utf-8 -*-

import argparse
import glob
import os
import re
import shutil
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from tkinter import filedialog
import time

import ffmpeg
import openai
from pytube import YouTube

# spinner.py から Spinner クラスをインポート
from spinner import Spinner

MODEL = "gpt-3.5-turbo"
TMP_PATH = f"{os.getcwd()}/tmp"
TOKEN_LIMIT = 2000

# 一時ファイル命名用のユニックスタイムスタンプ
TIMESTAMP = str(int(time.time()))


# 入力されたURLが有効なYouTubeのURLかどうかを確認
def validate_youtube_url(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )

    youtube_pattern = re.compile(youtube_regex)

    return bool(youtube_pattern.match(url))


# YouTubeのビデオをダウンロード
def download_youtube_video(url, output_path):
    yt = YouTube(url)

    yt.streams.filter(progressive=True, file_extension='mp4').order_by(
        'resolution').asc().first().download(output_path, f"{TIMESTAMP}.mp4")


# 音声ファイルを指定された長さで分割
def split_audio(input_file, duration, output_format, title="output"):

    shutil.rmtree(f"{TMP_PATH}/{title}.split.*.mp3", ignore_errors=True)

    (
        ffmpeg
        .input(input_file)
        .output(os.path.join(TMP_PATH, f"{title}.split.%03d{output_format}"), **{'c': 'copy', 'map': '0', 'segment_time': duration, 'f': 'segment', 'reset_timestamps': '1'})
        .run()
    )

    output_files = sorted(glob.glob(os.path.join(TMP_PATH, f"{title}.split.*{output_format}")))

    return output_files


# 音声ファイルをテキストに変換（トランスクリプト化）
def transcribe_audio(audio_path):
    audio_file = open(audio_path, "rb")
    try:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript.text
    except openai.error.APIError as e:
        print(f"An API error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# 指定された文字数でテキストを分割
def split_text(text):
    text_list = []
    while len(text) > TOKEN_LIMIT:
        text_list.append(text[:TOKEN_LIMIT])
        text = text[TOKEN_LIMIT:]
    text_list.append(text)
    return text_list


# 指定されたテキストを要約
def summarize_text(text, prompt):
    prompt = f"{prompt}\n\n{text}"
    try:
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        result = response["choices"][0]["message"]["content"]
        return result
    except openai.error.APIError as e:
        print(f"An API error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# テキストリストの各要素を並行して要約
def parallel_summarize_text(text_list, prompt):
    summary_text = ""
    with ThreadPoolExecutor() as executor:
        results = executor.map(summarize_text, text_list, [prompt] * len(text_list))
        for result in results:
            summary_text += result
    return summary_text

generated_text = []

# テキストを指定された文字数で分割しながら要約
def parallel_iterative_summary(text, prompt):
    depth = 0
    summary = ""

    while True:
        text_list = split_text(text)
        summary = parallel_summarize_text(text_list, prompt)
        generated_text.append(f"## 要約 {depth}\n{summary}")
        if len(summary) <= TOKEN_LIMIT:
            break
        text = summary
        depth += 1

    return summary


# ローカルのビデオファイルを選択
def get_local_video_file():
    root = tk.Tk()
    root.withdraw()
    video_path = filedialog.askopenfilename()
    return video_path

# テキストリストをファイルに保存
def save_text_list(text_list):
    # 並びを逆順にする
    text_list.reverse()

    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.asksaveasfilename(
        initialdir=TMP_PATH,
        initialfile=TIMESTAMP,
        defaultextension=".md",
        filetypes=[("Markdown", ".md")]
    )
    with open(file_path, "w") as f:
        f.write("\n\n".join(text_list))

# ビデオファイルを処理
def process_video(video_path):

    stream = ffmpeg.input(video_path)
    audio_path = os.path.join(TMP_PATH, TIMESTAMP + ".mp3")
    stream = ffmpeg.output(stream, audio_path)
    ffmpeg.run(stream)

    splits = split_audio(audio_path, 1200, ".mp3", TIMESTAMP)

    transcript_text_sum = ""
    with ThreadPoolExecutor() as executor:
        results = executor.map(transcribe_audio, splits)
        for index, result in enumerate(results):
            generated_text.append(f"## トランスクリプト {index}\n{result}")
            transcript_text_sum += result

    summary = parallel_iterative_summary(transcript_text_sum, "Please summarize the following sentences in Japanese, separating them into paragraphs and line breaks. Adjust the text to be natural. Please sort out redundant wording.:\n\n")

    response = summarize_text(
        summary, "Please create a heading for the following text in Japanese:")

    return response


# YouTubeのビデオURLからビデオをダウンロードし、その要約を作成
def summarize_video_from_youtube(video_url):
    if not validate_youtube_url(video_url):
        raise ValueError(f"'{video_url}' is not a valid YouTube URL.")

    download_youtube_video(video_url, TMP_PATH)
    video_path = os.path.join(TMP_PATH, f"{TIMESTAMP}.mp4")

    return process_video(video_path)


# ローカルのビデオファイルの要約を作成
def summarize_video(video_path):
    return process_video(video_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Summarize a video.')
    parser.add_argument('api_key', type=str, help='OpenAI API Key')
    parser.add_argument('video_url', type=str, nargs='?', default=None, help='Path to the video file')
    parser.add_argument('--clean', action='store_true', help='Clean up temporary files')
    args = parser.parse_args()

    spinner = Spinner('Processing video...')
    spinner.start()

    # 一時ファイルを削除
    if args.clean:
        shutil.rmtree(TMP_PATH)

    # 一時ファイルディレクトリがなかったら作成
    if not os.path.exists(TMP_PATH):
        os.mkdir(TMP_PATH)

    # api_keyを設定
    openai.api_key = args.api_key

    if args.video_url is None:
        video_path = get_local_video_file()
        if video_path is None:
            raise ValueError("No video file was selected.")
        summary_title = summarize_video(video_path)
    else:
        summary_title = summarize_video_from_youtube(args.video_url)

    # 生成に失敗したら代替えのタイトルを設定
    if summary_title is None:
        summary_title = "タイトルが生成できませんでした。"

    generated_text.append(f"# {summary_title}")

    save_text_list(generated_text)

    spinner.stop()
