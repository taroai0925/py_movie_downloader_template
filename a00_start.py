import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# このアプリが必要とする権限（スコープ）
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
# 認証情報ファイルの名前
CREDENTIALS_FILE = 'credentials.json'
# 発行されたトークンを保存するファイルの名前
TOKEN_FILE = 'token.json'

def main():
    """
    OAuth 2.0の認証フローを実行し、token.jsonを生成または更新する。
    Cloud ShellのようなCUI環境（手動コピペ方式）で正しく動作するコード。
    """
    creds = None
    print("--- アプリの認証を開始します ---")
    
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("既存の認証情報が期限切れです。更新します...")
            creds.refresh(Request())
        else:
            print("新しい認証が必要です。")
            
            # 1. credentials.jsonからクライアント設定情報を読み込む
            with open(CREDENTIALS_FILE, 'r') as f:
                # credentials.jsonの中の "installed" キーの値を取得する
                client_config_dict = json.load(f)

            # --- ここが最重要の修正点 ---
            # 2. InstalledAppFlowを初期化する際に、キーワード引数で正しく値を渡す
            flow = InstalledAppFlow.from_client_config(
                client_config=client_config_dict,
                scopes=SCOPES,
                redirect_uri="urn:ietf:wg:oauth:2.0:oob"
            )
            # --- 修正ここまで ---

            # 3. 認証用のURLを生成する
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            print('------------------------------------------------------------------')
            print('以下のURLをコピーして、お使いのブラウザで開いてください:')
            print(f'\n{auth_url}\n')
            print('------------------------------------------------------------------')
            
            # 4. ユーザーに認証コードの入力を促す
            code = input('ブラウザに表示された認証コードをコピーして、ここに貼り付けてください: ')
            
            # 5. 受け取った認証コードを使ってトークンを取得する
            flow.fetch_token(code=code)
            creds = flow.credentials
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            print(f"新しい認証情報を'{TOKEN_FILE}'に保存しました。")

    print("\n★★★ 認証が正常に完了しました！ ★★★")
    print("次に、'python m01_google_drive_manager.py' を実行して、アプリが未完成であることを確認してみましょう。\n")

if __name__ == '__main__':
    main()