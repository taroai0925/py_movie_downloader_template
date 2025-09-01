import os
import io
import re
import sys
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request

# --- 設定 ---
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TOKEN_FILE = 'token.json'
SUCCESS_LOG_FILE = 'processed_success.log'
FAILURE_LOG_FILE = 'processed_failure.log'
DOWNLOADS_DIR = 'downloads'

# ▼▼▼ ここが未完成なポイント！ ▼▼▼
# TODO: Geminiに指示して、ここにGoogle DriveのフォルダIDを設定してもらう
SHARED_DRIVE_FOLDER_ID = '1KarJiVGgwYC8MRoiX14tEBMQifNSxDAe'
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

def _sanitize_filename(filename):
    """Windowsでも使えるようにファイル名をサニタイズする"""
    return re.sub(r'[\\/:*?"<>|]', '_', filename)

def authenticate():
    """token.jsonを使って認証し、Drive APIサービスオブジェクトを返す"""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        print("エラー: 認証情報(token.json)が無効です。", file=sys.stderr)
        print("'python start.py'を先に実行して、認証を完了させてください。", file=sys.stderr)
        return None
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('drive', 'v3', credentials=creds)

def list_new_videos(service):
    """指定されたフォルダから、まだ処理していない動画ファイルのリストを取得する"""
    if not SHARED_DRIVE_FOLDER_ID:
        errmsg="""
エラー: 検索対象のフォルダIDが設定されていません！
以下の？？？？をあなたのgoogleドライブのIDに変更して、コピーします。
@m01_google_drive_manager.py の'SHARED_DRIVE_FOLDER_ID'を'？？？？'に設定してください。
---------------------------------------------------------------------------------------
上記の命令をgeminiに貼り付け、エンターキーを押してください。
geminiから、修正しても良いですかと英語で聞かれますので、エンターキーを押してください。"""
        print(errmsg, file=sys.stderr)
        return []

    processed_ids = set()
    for log_file in [SUCCESS_LOG_FILE, FAILURE_LOG_FILE]:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    processed_ids.add(line.strip().split(',')[1])
    
    print(f"'{SHARED_DRIVE_FOLDER_ID}'をスキャンしています...")
    new_videos = []
    page_token = None
    while True:
        response = service.files().list(
            q=f"'{SHARED_DRIVE_FOLDER_ID}' in parents and (mimeType contains 'video/') and trashed = false",
            spaces='drive',
            fields='nextPageToken, files(id, name, fileExtension)',
            orderBy='createdTime',
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        for file in response.get('files', []):
            if file.get('id') not in processed_ids:
                new_videos.append(file)
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    return new_videos

def log_success(file_id, file_name, log_file_path):
    print(f"DEBUG: log_success() CALLED for {file_name} -> {log_file_path}", file=sys.stderr)
    try:
        jst = timezone(timedelta(hours=9))
        timestamp = datetime.now(jst).isoformat()
        # 渡されたパスに書き込む（ファイルは上書きされる）
        with open(log_file_path, 'w', encoding='utf-8') as f:
            f.write(f"{timestamp},{file_id},{_sanitize_filename(file_name)}\n")
        print(f"成功ログを一次ファイルに記録しました: {log_file_path}", file=sys.stderr)
        log_entry(SUCCESS_LOG_FILE, file_id, file_name, "SUCCESS")


    except IOError as e:
        print(f"成功ログの書き込み中にエラー: {e}", file=sys.stderr)

def log_failure(file_id, file_name, error, log_file_path):
    print(f"DEBUG: log_failure() CALLED for {file_name} -> {log_file_path}", file=sys.stderr)
    try:
        jst = timezone(timedelta(hours=9))
        timestamp = datetime.now(jst).isoformat()
        error_oneline = str(error).replace('\n', ' ')
        # 渡されたパスに書き込む（ファイルは上書きされる）
        with open(log_file_path, 'w', encoding='utf-8') as f:
            f.write(f"{timestamp},{file_id},{_sanitize_filename(file_name)},{error_oneline}\n")
        print(f"失敗ログを一次ファイルに記録しました: {log_file_path}", file=sys.stderr)
        log_entry(SUCCESS_LOG_FILE, file_id, file_name, "FAILURE")
    except IOError as e:
        print(f"失敗ログの書き込み中にエラー: {e}", file=sys.stderr)

def download_video(service, file_id, file_name):
    """ファイルをダウンロードする"""
    if not os.path.exists(DOWNLOADS_DIR):
        os.makedirs(DOWNLOADS_DIR)
    
    local_path = os.path.join(DOWNLOADS_DIR, _sanitize_filename(file_name))
    #print(f"  -> '{file_name}' をダウンロード中...", end="", flush=True)
    print(f"  -> '{file_name}' をダウンロード中...\n")
    try:
        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        with io.FileIO(local_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        print(f"{local_path} にダウンロードしました。")
        print(f"完了")
        return True
    except Exception as e:
        print(f"失敗: {e}")
        return False

def log_entry(log_file, file_id, file_name, status):
    """ログファイルにエントリを追記する"""
    with open(log_file, 'a', encoding='utf-8') as f:
        timestamp = datetime.now(timezone.utc).isoformat()
        f.write(f"{timestamp},{file_id},{_sanitize_filename(file_name)},{status}\n")
    print(f"ログを追記しました: {log_file}", file=sys.stderr)

def main():
    """メインの処理"""
    service = authenticate()
    if not service:
        return

    videos_to_process = list_new_videos(service)
    if not videos_to_process:
        print("")
        return None,None
    
    print(f"\n{len(videos_to_process)}件の新しい動画が見つかりました。１件のみ処理を開始します。")
    for i,video in enumerate(videos_to_process):
        if i == 0:
            file_name_to_use = video['name']
            base_name, current_ext = os.path.splitext(file_name_to_use)
            if not current_ext:
                drive_extension = video.get('fileExtension')
                if drive_extension:
                    file_name_to_use = f"{file_name_to_use}.{drive_extension}"
                else:
                    file_name_to_use = f"{file_name_to_use}.mp4"

            download_video(service, video['id'], file_name_to_use)
            #if download_video(service, video['id'], file_name_to_use):
                #log_entry(SUCCESS_LOG_FILE, video['id'], file_name_to_use, "SUCCESS")
            #else:
                #log_entry(FAILURE_LOG_FILE, video['id'], file_name_to_use, "FAILURE")
            
            return video['id'],file_name_to_use
    
    print("\n全ての処理が終了しました。")


if __name__ == '__main__':
    main()