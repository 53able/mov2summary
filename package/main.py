import argparse
import ffmpeg
import openai
from pytube import YouTube
import os
from concurrent.futures import ThreadPoolExecutor
import hashlib


MODEL = "gpt-3.5-turbo"
OUTPUT_PATH = "output"


def download_youtube_video(url, output_path):
    yt = YouTube(url)

    # ファイル名をハッシュ値化
    hash_object = hashlib.sha256(yt.title.encode())
    hashed_title = hash_object.hexdigest()

    yt.streams.filter(progressive=True, file_extension='mp4').order_by(
        'resolution').asc().first().download(output_path, f"{hashed_title}.mp4")
    return hashed_title


def split_audio(input_file, duration, output_format, title="output", dir_name="output"):
    # Create a list to store the file names
    output_files = []

    # clear the output directory
    os.system(f"rm -rf {dir_name}/{title}.split.*.mp3")

    # FFmpeg command for splitting audio
    (
        ffmpeg
        .input(input_file)
        .output(f"{dir_name}/{title}.split.%03d{output_format}", **{'c': 'copy', 'map': '0', 'segment_time': duration, 'f': 'segment', 'reset_timestamps': '1'})
        .run()
    )


    # Get the list of output file names
    file_names = os.listdir(dir_name)
    file_names.sort()  # Sort the file names in ascending order

    # Iterate through the output file names and add them to the list
    for file_name in file_names:
        if file_name.startswith(f"{title}.split") and file_name.endswith(output_format):
            output_files.append(f"{dir_name}/{file_name}")

    return output_files


# Transcribe audio to text
def transcribe_audio(audio_path):
    audio_file = open(audio_path, "rb")
    # Note: Whisper API is currently not supported in the Python OpenAI library
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript.text

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
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    result = response["choices"][0]["message"]["content"]
    return result


def recursive_summary(text, prompt, model, token_limit=2500, depth=0):
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


def summarize_video(video_url, api_key, model):
    openai.api_key = api_key

    # Download video from YouTube
    video_title = download_youtube_video(video_url, OUTPUT_PATH)
    video_path = f"{OUTPUT_PATH}/{video_title}.mp4"

    # Extract audio from video
    stream = ffmpeg.input(video_path)
    audio_path = video_path + ".mp3"
    stream = ffmpeg.output(stream, audio_path)
    ffmpeg.run(stream)

    splits = split_audio(audio_path, 1200, ".mp3", video_title)

    transcript_text_sum = ""
    with ThreadPoolExecutor() as executor:
        results = executor.map(transcribe_audio, splits)
        for index, result in enumerate(results):
            print(f"文字起こし {index}:\n{result}")
            transcript_text_sum += result

    summary = recursive_summary(transcript_text_sum, "Please summarize the following text with paragraph breaks and line breaks in Japanese:", model)

    # Generate summary using ChatGPT
    response = summarize_text(
        summary, "Please a heading the following text in Japanese:", model)
    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Summarize a video.')
    parser.add_argument('api_key', type=str, help='OpenAI API Key')
    parser.add_argument('video_url', type=str, help='Path to the video file')
    args = parser.parse_args()

    summary = summarize_video(args.video_url, args.api_key, MODEL)
    print(f"要約タイトル:\n{summary}")
