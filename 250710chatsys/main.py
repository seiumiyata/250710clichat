import sys
import random
from PySide6.QtWidgets import QApplication, QMainWindow

# アプリケーションの各コンポーネントをインポート
from ui import UIHandler
from debate import DebateManager
from config_session_command import ConfigManager
from persona import PersonaManager
from learning_manager import LearningManager

class ChatApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Persona AI Chat")
        self.setGeometry(100, 100, 1200, 800)

        # Gemini CLIへのパス (環境に合わせて変更してください)
        self.gemini_path = "/usr/local/bin/gemini"
        
        # ▼▼▼ 修正箇所 ▼▼▼
        # 使用するモデルを、動作確認が取れている単一のモデルに固定
        self.model_name = "gemini-2.5-flash"
        # ▲▲▲ 修正箇所 ▲▲▲

        # 各マネージャークラスをインスタンス化
        self.persona_manager = PersonaManager()
        self.config_manager = ConfigManager(self)
        self.learning_manager = LearningManager(self)
        self.debate_manager = DebateManager(self)
        self.ui = UIHandler(self)

        # UIとDebateManagerを連携
        self.ui.link_debate_manager(self.debate_manager)
        self.debate_manager.link_comm(self.ui.comm)

        # UIのセットアップ
        self.ui.setup_ui()

    def closeEvent(self, event):
        # アプリケーション終了時に学習履歴を保存
        self.learning_manager.save_summaries()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatApplication()
    window.show()
    sys.exit(app.exec())
