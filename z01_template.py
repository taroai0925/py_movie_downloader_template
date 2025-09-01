import os
import shutil


def main():
    """処理に必要なディレクトリをクリーンアップして再作成する"""
    # 一時ログ用のディレクトリも作成
    dirs_to_create = ["m4a", "split_m4a", "downloads", "temp_logs","__pycache__"]
    for d in dirs_to_create:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"ディレクトリ '{d}' を削除しました。")
        #os.makedirs(d)
        #print(f"ディレクトリ '{d}' を作成しました。")
    
    delete_files= ["processed_success.log","processed_failure.log","token.json",".env"]
    for d in delete_files:
        if os.path.exists(d):
            os.remove(d)
            print(f"ファイル '{d}' を削除しました。")

    
main()