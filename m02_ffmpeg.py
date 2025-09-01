import subprocess
import os
import shutil
import glob
import sys
PYTHON_NAME = os.path.basename(__file__)


def split_audio(input_file, output_dir, segment_time, base_name):
    """
    ffmpegを使って音声ファイルを指定時間で分割し、指定のファイル名形式で出力する。

    Args:
        input_file (str): 入力音声ファイルのパス。
        output_dir (str): 出力ファイルのディレクトリパス。
        segment_time (int): 分割する時間（秒）。
        base_name (str): 元のファイル名（拡張子なし）。
    """

    command = [
        "ffmpeg",
        "-i", input_file,
        "-f", "segment",
        "-segment_time", str(segment_time),
        "-c", "copy",
        os.path.join(output_dir, f"{base_name}_split%03d.m4a")  # 出力ファイル名を変更
    ]
    try:
        subprocess.run(command, check=True)
        print(f"分割完了: .{output_dir} フォルダに出力 : ({PYTHON_NAME})")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"エラーが発生しました: {e} : ({PYTHON_NAME})")
        return -1

def convert_audio(input_file, output_file):
    """
    ffmpegを使って動画ファイルを音声ファイルに変換する。

    Args:
        input_file (str): 入力動画ファイルのパス。
        output_file (str): 出力音声ファイルのパス。
    """
    if os.path.exists(output_file):
        os.remove(output_file)
    command = [
        "ffmpeg",
        "-i", input_file,
        "-vn",
        "-ac", "1",
        "-af", "atempo=1.3,aresample=44100",
        "-ab", "64k",
        "-acodec", "aac",
        output_file
    ]
    try:
        subprocess.run(command, check=True)
        print(f"変換完了: {output_file} : ({PYTHON_NAME})")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"エラーが発生しました: {e} : ({PYTHON_NAME})")
        return -1

def main():
    downloads_dir = os.path.join(os.path.expanduser("."), "downloads")
    m4a_dir = "m4a"
    split_m4a_dir = "split_m4a"
    segment_time = 240 #240

    try:
        mp4_files = glob.glob(os.path.join(downloads_dir, "*.mp4"))
        print(f"Found mp4 files: {mp4_files} : ({PYTHON_NAME})")

        if not mp4_files:
            print(f"エラー: downloadsフォルダに処理対象の.mp4ファイルが見つかりません。 : ({PYTHON_NAME})")
            sys.exit(1)

        input_file = mp4_files[0]
        print(f"処理対象ファイル: {input_file} : ({PYTHON_NAME})")

        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(m4a_dir, f"{base_name}.m4a")

        if convert_audio(input_file, output_file) != 0:
            print(f"音声変換に失敗したため、処理を中断します。 : ({PYTHON_NAME})")
            sys.exit(1)

        if split_audio(output_file, split_m4a_dir, segment_time, base_name) != 0:
            print(f"音声の分割に失敗したため、処理を中断します。 : ({PYTHON_NAME})")
            sys.exit(1)

        shutil.copy2(input_file, split_m4a_dir)

        # 【ここから追加】空のテキストファイルを作成
        txt_filename = os.path.splitext(os.path.basename(input_file))[0] + '.txt'
        txt_filepath = os.path.join(split_m4a_dir, txt_filename)
        with open(txt_filepath, 'w') as f:
            f.write("") # 空のファイルを作成
            #pass # 空のファイルを作成
        print(f"空のテキストファイルを作成しました: {txt_filepath} : ({PYTHON_NAME})")
        # 【ここまで追加】

        print(f"split_m4aフォルダ内のファイル : ({PYTHON_NAME})")
        for filename in os.listdir(split_m4a_dir):
            print(f"{filename} : ({PYTHON_NAME})")
        print(f"処理完了: {base_name} : ({PYTHON_NAME})")

    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e} : ({PYTHON_NAME})")
        sys.exit(1)

if __name__ == "__main__":
    main()
    print(f"Exit : ({PYTHON_NAME})")
