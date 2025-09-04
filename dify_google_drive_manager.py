#
# ファイル名: dify_google_drive_manager.py
# 役割: Google Driveから新しいPDF/画像ファイルのURLを1件取得する
#

import os
import re
import sys
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# --- 設定 ---
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TOKEN_FILE = 'token.json'
SUCCESS_LOG_FILE = 'dify_get_url_success.log'
FAILURE_LOG_FILE = 'dify_get_url_failure.log'
SHARED_DRIVE_FOLDER_ID = '1KarJiVGgwYC8MRoiX14tEBMQifNSxDAe'

def _sanitize_filename(filename):
    return re.sub(r'[\\/:*?"<>|]', '_', filename)

def authenticate():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        print("\nエラー: 認証情報(token.json)が無効です。", file=sys.stderr)
        print("`python a00_start.py`等を先に実行して、認証を完了させてください。\n", file=sys.stderr)
        return None
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('drive', 'v3', credentials=creds)

def find_new_files(service):
    if not SHARED_DRIVE_FOLDER_ID:
        print("エラー: 検索対象のフォルダIDが設定されていません！", file=sys.stderr)
        return []

    processed_ids = set()
    for log_file in [SUCCESS_LOG_FILE, FAILURE_LOG_FILE]:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        processed_ids.add(line.strip().split(',')[1])
    
    print(f"INFO: Driveフォルダ '{SHARED_DRIVE_FOLDER_ID}' をスキャンしています...")
    new_files = []
    page_token = None
    query = f"'{SHARED_DRIVE_FOLDER_ID}' in parents and (mimeType='application/pdf' or mimeType contains 'image/') and trashed = false"

    while True:
        response = service.files().list(
            q=query,
            spaces='drive',
            fields='nextPageToken, files(id, name, webViewLink)',
            orderBy='createdTime',
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        for file in response.get('files', []):
            if file.get('id') not in processed_ids:
                new_files.append(file)
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    return new_files

def log_entry(log_file, file_id, file_name, status):
    """ログファイルにエントリを追記する (この関数はコントローラーから呼ばれる)"""
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now(timezone.utc).isoformat()
            f.write(f"{timestamp},{file_id},{_sanitize_filename(file_name)},{status}\n")
        print(f"INFO: ログを記録しました: {log_file} ({_sanitize_filename(file_name)})", file=sys.stderr)
    except IOError as e:
        print(f"エラー: ログの書き込み中にエラーが発生しました: {e}", file=sys.stderr)

# ▼▼▼ 変更点 ▼▼▼
def get_new_file_url():
    """
    Google Driveから未処理の新しいファイルを探し、ID, 名前, URLを返すメイン関数。
    """
    service = authenticate()
    if not service:
        return None, None, None

    files_to_process = find_new_files(service)
    if not files_to_process:
        return None, None, None
    
    print(f"INFO: {len(files_to_process)}件の新しいファイルが見つかりました。最初の1件を処理します。")
    
    file_to_process = files_to_process[0]
    file_id = file_to_process.get('id')
    file_name = file_to_process.get('name')
    file_url = file_to_process.get('webViewLink')

    if file_url:
        print(f"INFO: ファイル '{file_name}' のURLを取得しました。")
        # ★★★ ここにあった成功ログ記録処理を削除 ★★★
        # 戻り値に file_id を追加
        return file_id, file_name, file_url
    else:
        print(f"エラー: ファイル '{file_name}' のURLが取得できませんでした。", file=sys.stderr)
        # URL取得自体の失敗はここでログに残す
        log_entry(FAILURE_LOG_FILE, file_id, file_name, "URL_RETRIEVAL_FAILURE")
        return None, None, None
# ▲▲▲▲▲▲▲▲▲▲▲▲

if __name__ == '__main__':
    print("--- dify_google_drive_manager.py 単体テスト実行 ---")
    f_id, f_name, f_url = get_new_file_url() # 戻り値を3つ受け取るように変更
    if f_url:
        print("\n--- 取得結果 ---")
        print(f"File ID: {f_id}")
        print(f"ファイル名: {f_name}")
        print(f"URL: {f_url}")
    else:
        print("\n処理対象の新しいファイルはありませんでした。")
    print("--- 単体テスト終了 ---")