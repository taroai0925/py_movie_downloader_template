#
# ファイル名: dify_main_controller.py
# 役割: 全てのモジュールを連携させるメインプログラム
# 実行方法: python dify_main_controller.py
#

import dify_google_drive_manager as drive_manager
import dify_api_client as api_client
import dify_result_processor as processor

def main_process():
    """
    全体の処理をコントロールするメイン関数。
    """
    print("==================================================")
    print("STEP 1: Google Driveの新規ファイルをチェックします...")
    print("==================================================")
    
    # ▼▼▼ 変更点: file_idも受け取る ▼▼▼
    file_id, file_name, view_url = drive_manager.get_new_file_url()

    # URLが取得できた場合のみ次のステップへ
    if file_id and file_name and view_url:
        print("\n==================================================")
        print(f"STEP 2: ファイル '{file_name}' のDifyワークフローを実行します...")
        print("==================================================")
        
        result_json = api_client.call_dify_api(view_url)
        
        # ▼▼▼ 変更点: ログ記録のロジックをここに追加 ▼▼▼
        if result_json:
            # Difyからのレスポンスを解析
            data = result_json.get('data', {})
            status = data.get('status')
            
            markdown_content = processor.format_result_to_markdown(result_json)
            print(markdown_content)
            processor.save_markdown_to_file(markdown_content, file_name)

            # Difyの処理ステータスが 'succeeded' の場合のみ成功ログを記録
            if status == 'succeeded':
                drive_manager.log_entry(
                    drive_manager.SUCCESS_LOG_FILE,
                    file_id,
                    file_name,
                    "DIFY_PROCESSING_SUCCESS"
                )
            else:
                # Difyがエラーを返した場合、失敗ログを記録
                drive_manager.log_entry(
                    drive_manager.FAILURE_LOG_FILE,
                    file_id,
                    file_name,
                    "DIFY_PROCESSING_FAILED_IN_WORKFLOW"
                )
        else:
            # API通信自体が失敗した場合、失敗ログを記録
            print("INFO: Dify APIとの通信に失敗したため、後続の処理をスキップしました。", file=sys.stderr)
            drive_manager.log_entry(
                drive_manager.FAILURE_LOG_FILE,
                file_id,
                file_name,
                "DIFY_API_COMMUNICATION_FAILURE"
            )
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

    else:
        print("\n==================================================")
        print("完了: 処理対象の新しいファイルはありませんでした。")
        print("==================================================")

if __name__ == "__main__":
    print("自動処理を開始します...")
    main_process()
    print("\n全てのプロセスが終了しました。")