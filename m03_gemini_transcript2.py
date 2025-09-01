import requests
import re
import json
import time
import os
import uuid
from google import genai
from google.genai import types
import pathlib
from dotenv import load_dotenv
import logging
import glob
import asyncio
from m03_api_key_manager import api_key_manager

PYTHON_NAME = os.path.basename(__file__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")
print(MODEL_NAME)
print('MODEL_NAME m03_gemini_transcript2.py')


def write_to_file(text, file_path):
    """文字列をファイルに書き込む。"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        logging.info(f"[{file_path}] に保存済。 : ({PYTHON_NAME})")
    except Exception as e:
        logging.info(f"ファイル書き込み中にエラーが発生しました: {e} : ({PYTHON_NAME})")

def gemini_transcribe2(transcription, file_path, api_key, import_file_num, 
        model_name=MODEL_NAME
        ):
    """
    渡されたAPIキーを使ってGemini APIを1回だけ呼び出す。
    リトライは行わない。
    """
    time.sleep(1)
    client = genai.Client(api_key=api_key)
    logging.info(f"[{file_path}] APIコール中 Key:{api_key[-4:]} model:{model_name}")
    start_time = time.time()
    
    if import_file_num == 2:
        import m03_gemini_prompt2 as prompt_module
    else:
        import m03_gemini_prompt3 as prompt_module
    
    prompt = prompt_module.main(transcription)

    generation_config = types.GenerateContentConfig(
        max_output_tokens=50000000,
        temperature=0.1,
        #thinking_config=types.ThinkingConfig(thinking_budget=-1),
        tools=[types.Tool(google_search=types.GoogleSearch())],
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_NONE
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE
            ),
        ]
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt],
            config=generation_config
        )

        
        if response.text:
            text1 = response.text
            logging.info(response)
            logging.info(f"[{file_path}] テキスト取得成功。")
            end_time = time.time()
            elapsed_time = end_time - start_time
            logging.info(f"[{file_path}] gemini_transcribe2の実行時間: {elapsed_time:.2f}秒")
            return text1

        logging.warning(f"[{file_path}] API応答からテキストを抽出できませんでした。応答内容: {response}")
        logging.warning(f"[{file_path}] API応答からテキストを抽出できませんでした。応答内容\n")
        raise ValueError("API応答からテキストを抽出できませんでした。")

    except Exception as e:
        logging.error(f"[{file_path}] API呼び出し中にエラーが発生しました: {e}")
        raise

async def process_step(step_name, input_file_path, output_file_path, prompt_module_num, 
    max_retries=10, 
    retry_delay=10
    ):
    """
    指定されたステップの処理を行う。
    リトライのたびに新しいAPIキーを取得する。
    """
    logging.info(f"--- {step_name} を開始します: {input_file_path} -> {output_file_path} ---")
    
    for attempt in range(max_retries):
        try:
            api_key = await api_key_manager.get_next_key()
            if not api_key:
                logging.error("APIキーが枯渇しました。処理をスキップします。")
                return None

            logging.info(f"[{input_file_path}] 試行 {attempt + 1}/{max_retries} 回目")

            with open(input_file_path, 'r', encoding='utf-8') as f:
                combined_text = f.read()

            transcription = await asyncio.to_thread(
                gemini_transcribe2,
                combined_text,
                input_file_path,
                api_key,
                prompt_module_num
            )
            
            if transcription:
                write_to_file(transcription, output_file_path)
                print(f'{step_name}の結果を {output_file_path} に保存しました。 : ({PYTHON_NAME})')
                return transcription

        except Exception as e:
            logging.error(f"[{input_file_path}] {step_name}でエラーが発生しました: {e} (試行回数: {attempt + 1})")

        if attempt < max_retries - 1:
            logging.info(f"{retry_delay}秒待機してAPIキーを変更し、再試行します...")
            await asyncio.sleep(retry_delay)

    logging.error(f"[{input_file_path}] 最大試行回数({max_retries}回)に達しました。{step_name}を中止します。")
    return None

async def process_file_pipeline(input_path):
    """
    単一の入力ファイルに対して、編集とマガジン化のパイプライン処理を行う。
    """
    directory = os.path.dirname(input_path)
    base_name = os.path.basename(input_path)
    
    output_base_z2 = base_name.replace('z1_', 'z2_')
    output_path_z2 = os.path.join(directory, output_base_z2)
    
    output_base_z3 = base_name.replace('z1_', 'z3_').replace('.txt', '.md')
    output_path_z3 = os.path.join(directory, output_base_z3)

    logging.info(f"--- パイプライン開始: {input_path} ---")

    step1_result = await process_step(
        step_name="日本語編集",
        input_file_path=input_path,
        output_file_path=output_path_z2,
        prompt_module_num=2
    )

    if not step1_result:
        logging.error(f"ステップ1（日本語編集）に失敗したため、{input_path} の処理を中断します。")
        return

    step2_result = await process_step(
        step_name="マガジン化",
        input_file_path=output_path_z2,
        output_file_path=output_path_z3,
        prompt_module_num=3
    )

    if not step2_result:
        logging.error(f"ステップ2（マガジン化）に失敗したため、{input_path} の処理を中断します。")
        return
        
    logging.info(f"--- パイプライン完了: {input_path} ---")


async def main(combined_file_path):
    """
    メイン処理。引数で渡された結合済みファイルに対して処理を実行する。
    """
    if not combined_file_path or not os.path.exists(combined_file_path):
        print("処理対象の z1_combined.txt ファイルが見つかりません。")
        return

    print(f"処理対象のファイル: ['{combined_file_path}']")

    # process_file_pipelineは非同期関数なので、そのままawaitで呼び出す
    await process_file_pipeline(combined_file_path)
    
    print("すべての処理が完了しました。")

if __name__ == "__main__":
    try:
        # このスクリプトが直接実行された場合のテスト動作
        test_file = "./split_m4a/z1_combined.txt"
        if os.path.exists(test_file):
            asyncio.run(main(test_file))
        else:
            print(f"テスト用のファイルが見つかりません: {test_file}")
    finally:
        api_key_manager.save_session()
        print(f"Exit : ({PYTHON_NAME})")