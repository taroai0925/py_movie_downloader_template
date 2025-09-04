#
# ファイル名: dify_result_processor.py
# 役割: Difyの結果を解析し、Markdownへの整形とファイル保存を行う
#

import json
import os
import re


def format_result_to_markdown(result_json: dict) -> str:
    """
    DifyのAPIレスポンス(JSON)をMarkdown形式の文字列に変換する。
    """
    if not result_json or 'data' not in result_json:
        return "## 実行エラー\nレスポンスに 'data' フィールドが含まれていません。\n"

    data = result_json['data']
    status = data.get('status')
    markdown_output = []

    if status == 'succeeded':
        outputs = data.get('outputs', {})
        text_result = outputs.get('text', '（テキストの出力がありませんでした）')
        markdown_output.append("## ワークフロー実行結果\n")
        markdown_output.append("### 文字起こしテキスト\n")
        markdown_output.append(f"```text\n{text_result}\n```\n")
        markdown_output.append("### 実行情報\n")
        markdown_output.append(f"- **ステータス:** {status}")
        markdown_output.append(f"- **実行時間:** {data.get('elapsed_time', 0):.2f} 秒")
        markdown_output.append(f"- **合計トークン数:** {data.get('total_tokens', 0)}")
        markdown_output.append(f"- **ワークフロー実行ID:** `{result_json.get('workflow_run_id', 'N/A')}`")
    else:
        markdown_output.append("## ワークフロー実行エラー\n")
        markdown_output.append(f"- **ステータス:** {status}")
        markdown_output.append(f"- **エラー内容:** {data.get('error', '詳細不明')}")

    return "\n".join(markdown_output)

def save_markdown_to_file(markdown_content: str, original_filename: str):
    """
    Markdown文字列を指定されたルールでファイルに保存する。
    """
    output_dir = 'markdown'
    os.makedirs(output_dir, exist_ok=True)
    
    base_filename = os.path.splitext(original_filename)[0]
    output_filepath = os.path.join(output_dir, f"{base_filename}.md")

    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"\nINFO: 結果をMarkdownファイルに保存しました: {output_filepath}")
    except IOError as e:
        print(f"エラー: ファイルの書き込み中にエラーが発生しました: {e}", file=sys.stderr)