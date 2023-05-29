import argparse
import ffmpeg
import openai
from pytube import YouTube
import os
from concurrent.futures import ThreadPoolExecutor
import hashlib
import re
import tkinter as tk
from tkinter import filedialog
import shutil
import glob

MODEL = "gpt-3.5-turbo"
TMP_PATH = "tmp"

# TMP_PATH ディレクトリを作成しておく
# すでに存在していた場合は削除してから作成する
def make_tmp_dir():
    if os.path.exists(TMP_PATH):
        shutil.rmtree(TMP_PATH)
    os.mkdir(TMP_PATH)


def validate_youtube_url(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )

    youtube_pattern = re.compile(youtube_regex)

    return bool(youtube_pattern.match(url))


def download_youtube_video(url, output_path):
    yt = YouTube(url)

    # ファイル名をハッシュ値化
    hash_object = hashlib.sha256(yt.title.encode())
    hashed_title = hash_object.hexdigest()

    yt.streams.filter(progressive=True, file_extension='mp4').order_by(
        'resolution').asc().first().download(output_path, f"{hashed_title}.mp4")
    return hashed_title


def split_audio(input_file, duration, output_format, title="output"):

    # clear the output directory
    shutil.rmtree(f"{TMP_PATH}/{title}.split.*.mp3", ignore_errors=True)

    # FFmpeg command for splitting audio
    (
        ffmpeg
        .input(input_file)
        .output(os.path.join(TMP_PATH, f"{title}.split.%03d{output_format}"), **{'c': 'copy', 'map': '0', 'segment_time': duration, 'f': 'segment', 'reset_timestamps': '1'})
        .run()
    )

    # Get the list of output file names
    output_files = sorted(glob.glob(os.path.join(TMP_PATH, f"{title}.split.*{output_format}")))

    return output_files


# Transcribe audio to text
def transcribe_audio(audio_path):
    audio_file = open(audio_path, "rb")
    try:
        # Note: Whisper API is currently not supported in the Python OpenAI library
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript.text
    except openai.error.APIError as e:
        print(f"An API error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# 文字数制限を設けて、リスト形式に分割する関数
def split_text(text, limit=2000):
    text_list = []
    while len(text) > limit:
        text_list.append(text[:limit])
        text = text[limit:]
    text_list.append(text)
    return text_list


# リスト全体の文字数をカウントする関数
def count_text(text_list):
    count = 0
    for text in text_list:
        count += len(text)
    return count


# 要約をリクエストする関数
def summarize_text(text, prompt, model):
    # Generate summary using ChatGPT
    prompt = f"{prompt}\n\n{text}"
    try:
        response = openai.ChatCompletion.create(
            model=model,
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


def recursive_summary(text, prompt, model, token_limit=2000, depth=0):
    # 文字列を指定したトークン数で分割
    text_list = split_text(text, token_limit)

    # 各部分に対して要約を生成
    summary_list = [summarize_text(part, prompt, model) for part in text_list]

    # 要約を結合
    summary = "".join(summary_list)

    print(f"要約 {depth}:\n{summary}")

    # 要約のトークン数を計算
    summary_tokens = count_text(summary)

    # トークン数が上限を超えていたら、再度要約を生成
    if summary_tokens > token_limit:
        return recursive_summary(summary, prompt, model, token_limit, depth + 1)

    return summary


def get_local_video_file():
    root = tk.Tk()
    root.withdraw()  # Hide the main window.
    video_path = filedialog.askopenfilename()  # Open the file dialog and get the selected file path.
    return video_path


def process_video(video_path, api_key, model):
    # Set API key
    openai.api_key = api_key

    # Get video title by hashing the video_path
    hash_object = hashlib.sha256(video_path.encode())
    video_title = hash_object.hexdigest()

    # Extract audio from video
    stream = ffmpeg.input(video_path)
    audio_path = os.path.join(TMP_PATH, video_title + ".mp3")
    stream = ffmpeg.output(stream, audio_path)
    ffmpeg.run(stream)

    # Split the audio into segments
    splits = split_audio(audio_path, 1200, ".mp3", video_title)

    # Transcribe audio to text
    transcript_text_sum = ""
    with ThreadPoolExecutor() as executor:
        results = executor.map(transcribe_audio, splits)
        for index, result in enumerate(results):
            print(f"Transcript {index}:\n{result}")
            transcript_text_sum += result

    # Summarize the transcript text
    summary = recursive_summary(transcript_text_sum, "Please summarize the following sentences in Japanese, separating them into paragraphs and line breaks:", model)

    # Generate a title for the summary using ChatGPT
    response = summarize_text(
        summary, "Please create a heading for the following text in Japanese:", model)
    return response

def summarize_video_from_youtube(video_url, api_key, model):
    if not validate_youtube_url(video_url):
        raise ValueError(f"'{video_url}' is not a valid YouTube URL.")

    # Download video from YouTube
    video_title = download_youtube_video(video_url, TMP_PATH)
    video_path = os.path.join(TMP_PATH, f"{video_title}.mp4")

    return process_video(video_path, api_key, model)


def summarize_video(video_path, api_key, model):
    return process_video(video_path, api_key, model)




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Summarize a video.')
    parser.add_argument('api_key', type=str, help='OpenAI API Key')
    parser.add_argument('video_url', type=str, nargs='?', default=None, help='Path to the video file')
    args = parser.parse_args()

    make_tmp_dir()

    if args.video_url is None:
        video_path = get_local_video_file()
        if video_path is None:
            raise ValueError("No video file was selected.")
        summary = summarize_video(video_path, args.api_key, MODEL)
    else:
        summary = summarize_video_from_youtube(args.video_url, args.api_key, MODEL)

    print(f"要約タイトル:\n{summary}")
