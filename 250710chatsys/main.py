import sys
import subprocess
import threading
import importlib.util
from pathlib import Path
import shutil

# PySide6のモジュールをインポート
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QLineEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QWidget
)
# ▼▼▼ 修正点1: シグナルとスロット、カーソル操作のために必要なモジュールを追加 ▼▼▼
from PySide6.QtCore import Slot, Signal, QObject
from PySide6.QtGui import QTextCursor
# ▲▲▲ 修正点1 ▲▲▲

# --- 他モジュールの動的インポート ---
# (変更なし)
def import_module_from_path(module_name):
    file_path = Path(f"./{module_name}.py")
    if file_path.exists():
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"モジュール '{module_name}.py' の読み込みに成功しました。")
            return module
        except Exception as e:
            print(f"エラー: モジュール '{module_name}.py' の読み込みに失敗しました。 {e}")
            return None
    else:
        print(f"情報: モジュール '{module_name}.py' は存在しません。基本的な機能で動作します。")
        return None

ui_module = import_module_from_path("ui")
persona_module = import_module_from_path("persona")
debate_module = import_module_from_path("debate")
config_module = import_module_from_path("config_session_command")

# ▼▼▼ 修正点2: バックグラウンドスレッドからの通信を受け取るためのクラスを定義 ▼▼▼
class Communicate(QObject):
    # str型のデータを受け取れる 'response_received' という名前のシグナルを定義
    response_received = Signal(str)
# ▲▲▲ 修正点2 ▲▲▲

class App(QMainWindow):
    def __init__(self, gemini_path):
        super().__init__()
        self.setWindowTitle("AI Chat System (PySide6)")
        self.setGeometry(100, 100, 800, 600)
        self.gemini_path = gemini_path

        self.ui = ui_module.UIHandler(self) if ui_module else BaseUIHandler(self)
        self.persona_manager = persona_module.PersonaManager() if persona_module else BasePersonaManager()
        self.debate_manager = debate_module.DebateManager(self) if debate_module else BaseDebateManager(self)
        self.config_manager = config_module.ConfigManager(self) if config_module else BaseConfigManager(self)

        self.ui.setup_ui()

    def closeEvent(self, event):
        print("\nアプリケーションを終了します。")
        super().closeEvent(event)


class BaseUIHandler:
    def __init__(self, app):
        self.app = app
        # ▼▼▼ 修正点3: 通信用のシグナルオブジェクトを作成 ▼▼▼
        self.comm = Communicate()
        # ▲▲▲ 修正点3 ▲▲▲

    def setup_ui(self):
        central_widget = QWidget()
        self.app.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        main_layout.addWidget(self.chat_display, 1)

        input_layout = QHBoxLayout()
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("メッセージを入力...")
        input_layout.addWidget(self.user_input, 1)
        self.send_button = QPushButton("送信")
        input_layout.addWidget(self.send_button)
        main_layout.addLayout(input_layout)

        # --- イベント接続 ---
        self.user_input.returnPressed.connect(self.send_message_event)
        self.send_button.clicked.connect(self.send_message_event)
        
        # ▼▼▼ 修正点4: シグナルと、GUIを更新するスロット（関数）を接続 ▼▼▼
        self.comm.response_received.connect(self.update_gui_with_response)
        # ▲▲▲ 修正点4 ▲▲▲
        
        self.user_input.setFocus()

    @Slot()
    def send_message_event(self):
        user_text = self.user_input.text().strip()
        if not user_text:
            return

        print(f"\n[User]: {user_text}")
        self.display_message("User", user_text)
        self.user_input.clear()

        if user_text.lower() in ["exit", "quit"]:
            self.app.close()
            return
        
        self.user_input.setEnabled(False)
        self.send_button.setEnabled(False)
        self.display_message("AI", "思考中...")
        print("[AI]: 思考中...")

        threading.Thread(target=self.get_ai_response, args=(user_text,), daemon=True).start()

    def get_ai_response(self, prompt):
        """バックグラウンドスレッドで実行される関数"""
        try:
            command = [self.app.gemini_path, "-p", prompt]
            result = subprocess.run(
                command, text=True, encoding='utf-8', check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            ai_text = result.stdout.strip()
            
            if not ai_text:
                ai_text = "エラー: Gemini CLIから応答がありませんでした。\n【確認】`gemini auth login` を実行し認証を確認してください。"

        except subprocess.CalledProcessError as e:
            ai_text = f"エラー: Gemini CLIの実行に失敗しました。\n{e.stderr}"
        except Exception as e:
            ai_text = f"予期せぬエラーが発生しました: {e}"
        
        print(f"[AI]: {ai_text}")
        # ▼▼▼ 修正点5: GUIを直接操作せず、シグナルをemit（発行）する ▼▼▼
        self.comm.response_received.emit(ai_text)
        # ▲▲▲ 修正点5 ▲▲▲

    @Slot(str)
    def update_gui_with_response(self, ai_text):
        """シグナル受信時にメインスレッドで安全に実行される関数"""
        self.update_last_message("AI", ai_text)
        self.user_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.user_input.setFocus()

    def display_message(self, sender, message):
        self.chat_display.append(f"{sender}: {message}\n")

    def update_last_message(self, sender, message):
        cursor = self.chat_display.textCursor()
        # ▼▼▼ 修正点6: エラーの出ていた定数を正しいものに修正 ▼▼▼
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        # ▲▲▲ 修正点6 ▲▲▲
        if "AI: 思考中..." in cursor.selectedText():
            cursor.removeSelectedText()
        self.display_message(sender, message)

class BasePersonaManager:
    def __init__(self):
        print("情報: ペルソナマネージャーは基本モードで動作します。")
class BaseDebateManager:
    def __init__(self, app):
        self.app = app
        print("情報: 討論マネージャーは基本モードで動作します。")
class BaseConfigManager:
    def __init__(self, app):
        self.app = app
        print("情報: 設定マネージャーは基本モードで動作します。")

if __name__ == "__main__":
    gemini_path = shutil.which("gemini")
    if not gemini_path:
        print("致命的エラー: 'gemini' コマンドがPATH内に見つかりません。")
        sys.exit(1)
    
    print(f"情報: Gemini CLI を検出しました: {gemini_path}")

    qapp = QApplication(sys.argv)
    app = App(gemini_path=gemini_path)
    app.show()
    sys.exit(qapp.exec())
