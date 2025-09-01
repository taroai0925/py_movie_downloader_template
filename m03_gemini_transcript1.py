import requests
import re
import json
import time
import os
import uuid
# google-genai SDKをインポート
from google import genai
from google.genai import types # 設定用の型をインポート
import pathlib
from dotenv import load_dotenv
import logging  # ログ記録用のライブラリを追加
import glob
import asyncio
from m03_api_key_manager import api_key_manager

PYTHON_NAME = os.path.basename(__file__)

# ----------------------------------------------------------------
# ▼▼▼ ここからが新しい設定項目 ▼▼▼
# ----------------------------------------------------------------

# Gemini APIへの最大同時リクエスト数（並列実行数）
MAX_CONCURRENT_REQUESTS = 1

# ----------------------------------------------------------------
# ▲▲▲ ここまでが新しい設定項目 ▲▲▲
# ----------------------------------------------------------------


# ログの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# .envファイルを読み込む
load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")


"""
・調査結果
Gemini
mp3対応可能
ファイルサイズ制限あり。
"""



def get_m4a_file_names(directory,extract):
    """
    指定されたディレクトリ以下の *.m4a ファイルのファイル名を配列で返す。
    """
    try:
        file_names = glob.glob(os.path.join(directory, extract))
        # ファイル名でソートして処理順を安定させる
        file_names.sort()
        return file_names
    except Exception as e:
        print(f"エラー: ファイル名取得中にエラーが発生しました: {e}")
        return []
    
def extract_audio_urls(json_string):
    """
    JSON文字列から音声ファイルのURLを抽出する。
    """
    try:
        data = json.loads(json_string)
        if 'urls' in data:
            urls = data['urls']
            audio_urls = [url for url in urls if url.endswith(('.m4a', '.mp3'))]
            return audio_urls
        else:
            return []
    except json.JSONDecodeError as e:
        logging.error(f"JSONのデコードに失敗しました: {e} : ({PYTHON_NAME})")
        return []

def download_audio(url, arg1,title):
    """
    指定されたURLから音声ファイルをダウンロードし、ローカルに保存する。
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # HTTPエラーをチェック

        match = re.search(r'episodes/([^/]+)', arg1)
        if match:
            file_name = f"audio_{match.group(1)}_{title}.m4a"
        else:
            file_name = f"audio_{uuid.uuid4().hex}_{title}.m4a"
        
        file_path = os.path.join(os.getcwd(), file_name)

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8122):
                f.write(chunk)
        logging.info(f"音声ファイルを {file_path} に保存しました。 : ({PYTHON_NAME})")
        return file_path
    except requests.exceptions.RequestException as e:
        logging.error(f"音声ファイルのダウンロード中にエラーが発生しました: {e} : ({PYTHON_NAME})")
        return None

logging.info(f"model_name: {MODEL_NAME}")

def gemini_transcribe(api_key, audio_file_path, 
        model_name=MODEL_NAME,
        max_retries=10, 
        retry_delay=10, 
        timeout=180000
        ):
    """Gemini API を使用して音声ファイルを文字起こしする。"""
    client = genai.Client(api_key=api_key)
    logging.info(f"[{audio_file_path}] Upload to Gemini: ({PYTHON_NAME})")
    start_time = time.time()
    
    audio_file = None  # audio_file を初期化
    # 音声ファイルをアップロード
    try:
        # 新しいSDKのファイルアップロードメソッドを使用
        audio_file = client.files.upload(file=pathlib.Path(audio_file_path))
    except Exception as e:
        logging.error(f"ファイルのアップロード中にエラーが発生しました: {e} : ({PYTHON_NAME})")
        # アップロードに失敗したファイルを削除
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)
            logging.info(f"アップロードに失敗したファイルを削除しました: {audio_file_path}")
        return None

    # 文字起こしをリクエスト
    import m03_gemini_prompt1
    prompt0 = m03_gemini_prompt1.main()

    response0 = None
    text0 = None # text0を初期化
    for attempt in range(max_retries): # 最大再試行回数まで繰り返す
        try:
            logging.info(f"[{audio_file_path}] 文字起こし　試行 {attempt + 1} 回目 : ({PYTHON_NAME})")
            # 新しいSDKの非ストリーミングメソッドを使用
            response0 = client.models.generate_content(
                            model=model_name,
                            contents=[prompt0, audio_file],
                            config=types.GenerateContentConfig(
                                max_output_tokens=50000, #50000000,
                                temperature=0.1,
                                #thinking_config=types.ThinkingConfig(thinking_budget=0),
                            ),
                        )
            
            # 非ストリーミングでは、レスポンスから直接textを取得
            # response0.textが存在しない場合や空の場合に再試行する
            if not response0 or not response0.text:
                logging.error(response0)
                logging.error('response0')
                logging.error(f"エラー: [{audio_file_path}] Gemini APIからの応答が空です。(試行回数: {attempt + 1}) : ({PYTHON_NAME})")
                if attempt == max_retries - 1:
                    logging.error(f"[{audio_file_path}] 最大試行回数に達しました。文字起こしを中止します。 : ({PYTHON_NAME})")
                    return None
                time.sleep(retry_delay)
                continue
            
            text0 = response0.text

            for part in response0.candidates[0].content.parts:
                if not part.text:
                    continue
                if part.thought:
                    print(part.text)
                    print("Thought summary:")
                    print()
                else:
                    print(part.text)
                    print("Answer:")
                    print()

            logging.info(response0)
            logging.info('response0')

            break # 正常に処理が完了した場合もループを抜ける
                
        except Exception as e:
            logging.error(f"[{audio_file_path}] 文字起こし中にエラーが発生しました: {e}(試行回数: {attempt + 1}) : ({PYTHON_NAME})")
            if attempt == max_retries - 1:
                logging.error(f"[{audio_file_path}] 最大試行回数に達しました。文字起こしを中止します。 : ({PYTHON_NAME})")
                return None
            time.sleep(retry_delay)  # 指定秒数だけ待機
            continue

    if text0 is None:
        logging.error(f"[{audio_file_path}] 文字起こしに失敗しました: prompt1 : ({PYTHON_NAME})")
        return None

    end_time = time.time()  # 終了時間を記録
    elapsed_time = end_time - start_time  # 経過時間を計算
    logging.info(f"[{audio_file_path}] gemini関数の実行時間: {elapsed_time:.2f}秒 : ({PYTHON_NAME})")

    # アップロードしたファイルを削除 (元のロジックにはなかったが、追加を推奨)
    if audio_file:
        try:
            client.files.delete(name=audio_file.name)
            logging.info(f"Gemini上のファイル {audio_file.name} を削除しました。")
        except Exception as e:
            logging.warning(f"Gemini上のファイル {audio_file.name} の削除に失敗しました: {e}")

    return [text0]


def write_to_file(text, file_path):
    """
    文字列をファイルに書き込む。
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        logging.info(f"[{file_path}] に保存済。 : ({PYTHON_NAME})")
    except Exception as e:
        logging.info(f"ファイル書き込み中にエラーが発生しました: {e} : ({PYTHON_NAME})")

def main2(filename, api_key):
    """1つのファイルの文字起こし処理"""
    audio_file_path = filename
    if audio_file_path:
        transcriptions = gemini_transcribe(api_key, audio_file_path)
        result=[]
        if transcriptions:
            for i,transcription in enumerate(transcriptions): 
                if transcription:                
                    output_file_path = os.path.splitext(audio_file_path)[0] + "_" + str(i) + ".txt"
                    write_to_file(transcription, output_file_path)
                    result.append(f'文字起こし結果を {output_file_path} に保存しました。 : ({PYTHON_NAME})')
                else:
                    result.append(f'Geminiでの文字起こしの一部（インデックス{i}）に失敗しました。 : ({PYTHON_NAME})')
        else:
            result.append(f'Geminiでの文字起こしに失敗しました。 : ({PYTHON_NAME})')

        logging.info(f"-----")
        return "\n".join(result)
    else:
        return f'音声ファイルがありません : ({PYTHON_NAME})'

async def worker(semaphore, filename, api_key_manager):
    """セマフォを使って並列実行を制御されるワーカー関数"""
    async with semaphore:
        print(f"[{os.path.basename(filename)}] 処理開始... (現在の並列実行数: {MAX_CONCURRENT_REQUESTS - semaphore._value}/{MAX_CONCURRENT_REQUESTS})")
        
        api_key = await api_key_manager.get_next_key()
        if not api_key:
            logging.error(f"APIキーが枯渇しました。{filename}の処理をスキップします。")
            return f"APIキー枯渇のため {filename} をスキップ"

        result = await asyncio.to_thread(main2, filename, api_key)
        
        print(f"[{os.path.basename(filename)}] 処理完了。")
        return result

async def main():
    directory = "./split_m4a/"
    extract = "*.m4a"
    m4a_files = get_m4a_file_names(directory,extract)
    if not m4a_files:
        logging.info(f"{directory} に対象ファイルが見つかりません。")
        return None
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    tasks = []
    for filename in m4a_files:
        task = asyncio.create_task(worker(semaphore, filename, api_key_manager))
        tasks.append(task)

    print(f"\n--- {len(tasks)}個のファイルを最大{MAX_CONCURRENT_REQUESTS}の並列度で文字起こし開始 ---")
    results = await asyncio.gather(*tasks)
    print("\n--- 全ての並列処理が完了 ---")
    
    for res in results:
        if res:
            logging.info(res)

    # 後処理
    for i in range(0,1):
        extract = "*" + str(i) + ".txt"
        txt_files = get_m4a_file_names(directory, extract)
        if not txt_files: continue
        
        combined_text = ""
        for txt_file in txt_files:
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    combined_text += f.read()
            except Exception as e:
                print(f"ファイル読み込みエラー: {txt_file} , {e} : ({PYTHON_NAME})")
        
        if combined_text:
            base_name = os.path.basename(os.path.splitext(txt_files[0])[0]).rsplit('_', 1)[0]
            output_file_path = os.path.join(directory, f"z1_combined.txt")
            write_to_file(combined_text, output_file_path)
            print(f"結合されたテキストを {output_file_path} に保存しました。")
            return output_file_path

    return None

if __name__ == "__main__":
    try:
        result_path = asyncio.run(main())
        if result_path:
            print(f"\nテスト実行完了。結合ファイルが作成されました: {result_path}")
        else:
            print(f"\nテスト実行完了。処理対象ファイルが見つからなかったか、結合に失敗しました。")
    finally:
        api_key_manager.save_session()
        print(f"Exit : ({PYTHON_NAME})")