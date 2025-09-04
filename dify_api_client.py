#
# ファイル名: dify_api_client.py
# 役割: Dify APIとの通信（会話）に特化したクライアント
#

import requests

def call_dify_api(target_url: str) -> dict | None:
    """
    Dify APIを呼び出し、生のJSONレスポンスを返すことに専念する関数。
    成功した場合はレスポンスの辞書を、失敗した場合はNoneを返す。
    :param target_url: Difyに渡す直接ダウンロード用URL
    """
    if not target_url:
        print("エラー: Difyに渡すURLが空です。", file=sys.stderr)
        return None

    # あなたのDifyアプリケーションのAPIキーに書き換えてください
    api_key = "app-v77yR3Z8sdUbmNi7sIf7SkDb"
    api_url = "https://api.dify.ai/v1/workflows/run"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "inputs": {"url": target_url}, # Difyワークフローの入力変数 'url' に合わせています
        "response_mode": "blocking",
        "user": "Dify-Automation"
    }
    
    print(f"INFO: Difyワークフローを実行します...\n  -> Target URL: {target_url}\n")

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        return response.json()  # 成功したらJSONの辞書を返す
    except requests.exceptions.HTTPError as http_err:
        print(f"## HTTPエラーが発生しました\n\n`{http_err}`\n", file=sys.stderr)
        print(f"**レスポンス内容:**\n```\n{response.text}\n```", file=sys.stderr)
        return None  # 失敗したらNoneを返す
    except requests.exceptions.RequestException as err:
        print(f"## リクエスト中にエラーが発生しました\n\n`{err}`", file=sys.stderr)
        return None  # 失敗したらNoneを返す