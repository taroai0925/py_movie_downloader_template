import re
import os

# 処理対象のファイル名
TARGET_FILE = "m01_google_drive_manager.py"

def reset_folder_id_in_file(file_path):
    exec = f"""\n指定されたPythonファイルを読み込み、
SHARED_DRIVE_FOLDER_IDの値を空文字列'' に書き換える。"""
    print(exec)
    try:
        # --- 1. ファイルを読み込む ---
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f"'{file_path}' を読み込みました。")

        # --- 2. 書き換える行を探し、新しい行リストを作成する ---
        new_lines = []
        found_and_modified = False
        
        # 正規表現パターンを定義
        # 'SHARED_DRIVE_FOLDER_ID'で始まり、'='を経て、任意の値が続く行にマッチ
        pattern = re.compile(r"^\s*SHARED_DRIVE_FOLDER_ID\s*=\s*.*")

        for line in lines:
            # パターンにマッチするかチェック
            if not found_and_modified and pattern.match(line):
                # マッチした場合、その行を書き換える
                current_value_match = re.search(r"=\s*'(.*)'", line)
                current_value = current_value_match.group(1) if current_value_match else "（不明）"
                
                if current_value != "":
                    new_line = "SHARED_DRIVE_FOLDER_ID = ''\n"
                    new_lines.append(new_line)
                    found_and_modified = True
                    print(f"変更前: {line.strip()}")
                    print(f"変更後: {new_line.strip()}")
                else:
                    # すでに空文字列の場合は、何もしない
                    new_lines.append(line)
                    print(f"初期化済です: \n{line.strip()}\n処理不要です。")
                    return # これ以上処理は不要なので関数を抜ける
            else:
                # マッチしない行は、そのまま新しいリストに追加
                new_lines.append(line)

        # --- 3. 変更があった場合のみ、ファイルを書き換える ---
        if found_and_modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"'{file_path}' のSHARED_DRIVE_FOLDER_IDをリセットしました。")
        else:
            print(f"'{file_path}' 内でSHARED_DRIVE_FOLDER_IDの行が見つからなかったか、変更は不要でした。")

    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません: {file_path}")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
def make_env_template():
    output_file = 'env_template'
    text = """MODEL_NAME='gemini-2.5-flash'
GOOGLE_API_KEY_1=''
GOOGLE_API_KEY_2=''
GOOGLE_API_KEY_3=''
"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"\n---------------------------------------\n{output_file} を初期化しました。\n---------------------------------------")
    
def main():    
    if os.path.exists(TARGET_FILE):
        reset_folder_id_in_file(TARGET_FILE)
    else:
        print(f"対象ファイル '{TARGET_FILE}' がこのディレクトリに存在しません。")

if __name__ == "__main__":
    main()
