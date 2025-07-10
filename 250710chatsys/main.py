import sys
import subprocess
import threading
import importlib.util
from pathlib import Path
import shutil

from PySide6.QtWidgets import (
    QApplication, QMainWindow
)
from PySide6.QtCore import Slot

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

class App(QMainWindow):
    def __init__(self, gemini_path):
        super().__init__()
        self.setWindowTitle("AI Chat System")
        self.setGeometry(100, 100, 800, 600)
        self.gemini_path = gemini_path

        # --- フェーズ1: 各モジュールを個別に初期化 ---
        self.persona_manager = persona_module.PersonaManager() if persona_module else BasePersonaManager()
        self.ui = ui_module.UIHandler(self) if ui_module else BaseUIHandler(self)
        self.debate_manager = debate_module.DebateManager(self) if debate_module else BaseDebateManager(self)
        self.config_manager = config_module.ConfigManager(self) if config_module else BaseConfigManager(self)

        # --- フェーズ2: モジュール同士を安全に接続 ---
        if ui_module and debate_module:
            self.ui.link_debate_manager(self.debate_manager)
            self.debate_manager.link_comm(self.ui.comm)
        
        # 最後にUIを構築
        self.ui.setup_ui()

    def closeEvent(self, event):
        print("\nアプリケーションを終了します。")
        if self.debate_manager.is_debating:
             self.debate_manager.stop_debate()
        super().closeEvent(event)

# --- (これ以降のBaseクラス群とmain実行部分は変更ありません) ---
class BaseUIHandler:
    def __init__(self, app): self.app = app
    def setup_ui(self): print("情報: UIは基本モードで動作します。")
    def link_debate_manager(self, manager): pass
class BasePersonaManager:
    def __init__(self): print("情報: ペルソナマネージャーは基本モードで動作します。")
    def get_active_personas(self): return []
class BaseDebateManager:
    def __init__(self, app):
        self.app = app
        self.is_debating = False
        print("情報: 討論マネージャーは基本モードで動作します。")
    def start_debate(self, theme): print(f"警告: 討論機能は無効です。")
    def stop_debate(self): print("警告: 討論機能は無効です。")
    def link_comm(self, comm): pass
class BaseConfigManager:
    def __init__(self, app):
        self.app = app
        print("情報: 設定マネージャーは基本モードで動作します。")

if __name__ == "__main__":
    gemini_path = shutil.which("gemini")
    if not gemini_path:
        print("致命的エラー: 'gemini' コマンドがPATH内に見つかりません。")
        sys.exit(1)
    
    qapp = QApplication(sys.argv)
    app = App(gemini_path=gemini_path)
    app.show()
    sys.exit(qapp.exec())
