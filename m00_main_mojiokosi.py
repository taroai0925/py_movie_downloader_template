import asyncio
import os
import shutil
import argparse

# 他のモジュールのインポート
import m01_google_drive_manager
import m02_ffmpeg
import m03_gemini_transcript1
import m03_gemini_transcript2

PYTHON_NAME = os.path.basename(__file__)

def setup_directories():
    """処理に必要なディレクトリをクリーンアップして再作成する"""
    # 一時ログ用のディレクトリも作成
    dirs_to_create = ["m4a", "split_m4a", "downloads", "temp_logs"]
    for d in dirs_to_create:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"ディレクトリ '{d}' を削除しました。")
        os.makedirs(d)
        print(f"ディレクトリ '{d}' を作成しました。")

async def main():
    """指定された1つの動画をダウンロードし、文字起こし処理を実行する"""
    
    temp_log_dir = "temp_logs"
    os.makedirs(temp_log_dir, exist_ok=True)

    print(f"--- 処理開始: ")
    real_video_id = None
    video_filename = None

    try:
        # 1. ディレクトリのセットアップ
        setup_directories()

        # 2. Google Driveから指定された動画をダウンロード
        print("Google Driveに接続しています...")
        real_video_id, video_filename = m01_google_drive_manager.main()
        
        if not video_filename:
            print(f"ダウンロード対象が有りません。処理を正常終了します。")
            return

        # 3. ffmpegで音声変換・分割
        print("\n--- 音声変換を開始します ---")
        m02_ffmpeg.main()

        # 4. Geminiで文字起こし・編集・要約
        print("\n--- 文字起こしを開始します ---")
        # --- ▼▼▼ ここからが修正箇所 ▼▼▼ ---
        
        # m03_gemini_transcript1.main() の戻り値（結合ファイルのパス）を変数に格納する
        combined_file_path = await m03_gemini_transcript1.main()
        
        # 結合ファイルが正常に作成されたかチェック
        if combined_file_path and os.path.exists(combined_file_path):
            print("\n--- 編集とマガジン化を開始します ---")
            # 格納したパスを、m03_gemini_transcript2.main() の引数として渡す
            await m03_gemini_transcript2.main(combined_file_path)
        else:
            # 結合ファイルが作成されなかった場合は、後続処理をスキップする
            print("警告: 結合された文字起こしファイルが見つからなかったため、編集とマガジン化の処理をスキップします。")

        # --- ▲▲▲ ここまでが修正箇所 ▲▲▲ ---

        # 5. 成功ログを一時ファイルに記録
        success_log_path = os.path.join(temp_log_dir, f"success_0.log")
        m01_google_drive_manager.log_success(real_video_id, video_filename, success_log_path)

        print(f"\n--- 全ての処理が正常に完了しました: {video_filename} ---")

    except Exception as e:
        print(f"エラーが発生したため、処理を中断します: {video_filename}")
        print(f"エラー詳細: {e}")
        # 失敗ログを一時ファイルに記録
        failure_log_path = os.path.join(temp_log_dir, f"failure_0.log")
        log_filename = video_filename if video_filename else "UnknownFileOnError"
        log_video_id = real_video_id if real_video_id else "UnknownIDOnError"
        m01_google_drive_manager.log_failure(log_video_id, log_filename, str(e), failure_log_path)
        raise

if __name__ == "__main__":

    try:
        asyncio.run(main())
    except Exception as e:
        # main内で捕捉されなかった予期せぬエラー
        print(f"スクリプト全体で致命的なエラーが発生しました: {e}")
        # 失敗終了コードでプロセスを終了
        exit(1)