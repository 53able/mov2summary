# -*- coding: utf-8 -*-

import argparse
import glob
import hashlib
import os
import re
import shutil
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from tkinter import filedialog

import ffmpeg
import openai
from pytube import YouTube

MODEL = "gpt-3.5-turbo"
TMP_PATH = "tmp"


# 一時的なディレクトリを作成
# 既に存在する場合は削除してから新しく作成
def make_tmp_dir():
    if os.path.exists(TMP_PATH):
        shutil.rmtree(TMP_PATH)
    os.mkdir(TMP_PATH)


# 入力されたURLが有効なYouTubeのURLかどうかを確認
def validate_youtube_url(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )

    youtube_pattern = re.compile(youtube_regex)

    return bool(youtube_pattern.match(url))


# 指定されたURLのYouTubeのビデオをダウンロード
# ビデオのタイトルをSHA256でハッシュ化してファイル名に使用
def download_youtube_video(url, output_path):
    yt = YouTube(url)

    hash_object = hashlib.sha256(yt.title.encode())
    hashed_title = hash_object.hexdigest()

    yt.streams.filter(progressive=True, file_extension='mp4').order_by(
        'resolution').asc().first().download(output_path, f"{hashed_title}.mp4")
    return hashed_title


# 入力ファイルの音声を分割
# 分割後のファイルはTMP_PATHに保存
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


# テキストを指定された文字数で分割
# 戻り地はテキストのリスト
def split_text(text, limit=2000):
    text_list = []
    while len(text) > limit:
        text_list.append(text[:limit])
        text = text[limit:]
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
        results = executor.map(summarize_text, text_list, [prompt] * len(text_list), [MODEL] * len(text_list))
        for result in results:
            summary_text += result
    return summary_text


# テキストを反復的に要約
# 各イテレーションでテキストを分割し、並行して要約を実行
def parallel_iterative_summary(text, prompt, token_limit=2000):
    depth = 0
    summary = ""

    while True:
        text_list = split_text(text, token_limit)

        summary = parallel_summarize_text(text_list, prompt)

        print(f"\n\n【要約 {depth}】:\n{summary}")

        if len(summary) <= token_limit:
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


# ビデオファイルを処理し、その要約を作成
# ビデオから音声を抽出し、音声をテキストに変換（トランスクリプト化）し、テキストを要約
def process_video(video_path):

    hash_object = hashlib.sha256(video_path.encode())
    video_title = hash_object.hexdigest()

    stream = ffmpeg.input(video_path)
    audio_path = os.path.join(TMP_PATH, video_title + ".mp3")
    stream = ffmpeg.output(stream, audio_path)
    ffmpeg.run(stream)

    splits = split_audio(audio_path, 1200, ".mp3", video_title)

    transcript_text_sum = ""
    with ThreadPoolExecutor() as executor:
        results = executor.map(transcribe_audio, splits)
        for index, result in enumerate(results):
            print(f"Transcript {index}:\n{result}")
            transcript_text_sum += result

    summary = parallel_iterative_summary(transcript_text_sum, "Please summarize the following sentences in Japanese, separating them into paragraphs and line breaks. Adjust the text to be natural. Please sort out redundant wording.:\n\n")

    response = summarize_text(
        summary, "Please create a heading for the following text in Japanese:")
    return response


# YouTubeのビデオURLからビデオをダウンロードし、その要約を作成
def summarize_video_from_youtube(video_url):
    if not validate_youtube_url(video_url):
        raise ValueError(f"'{video_url}' is not a valid YouTube URL.")

    video_title = download_youtube_video(video_url, TMP_PATH)
    video_path = os.path.join(TMP_PATH, f"{video_title}.mp4")

    return process_video(video_path)


# ローカルのビデオファイルの要約を作成
def summarize_video(video_path):
    return process_video(video_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Summarize a video.')
    parser.add_argument('api_key', type=str, help='OpenAI API Key')
    parser.add_argument('video_url', type=str, nargs='?', default=None, help='Path to the video file')
    args = parser.parse_args()

    # api_keyを設定
    openai.api_key = args.api_key

    make_tmp_dir()

    if args.video_url is None:
        video_path = get_local_video_file()
        if video_path is None:
            raise ValueError("No video file was selected.")
        summary = summarize_video(video_path)
    else:
        summary = summarize_video_from_youtube(args.video_url)

    print(f"\n\n【要約タイトル】:\n{summary}")
