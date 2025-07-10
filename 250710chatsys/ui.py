import sys
import subprocess
import threading
import random
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QLineEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
    QListWidget, QLabel, QGroupBox, QSlider, QSizePolicy,
    QFormLayout
)
from PySide6.QtCore import Slot, Signal, QObject, Qt
from PySide6.QtGui import QTextCursor, QFont

class Communicate(QObject):
    user_response_received = Signal(str, str)
    debate_thinking = Signal(str)
    debate_response_received = Signal(str, str)
    system_message = Signal(str)
    set_input_enabled = Signal(bool)

class UIHandler:
    def __init__(self, app):
        self.app = app
        self.comm = Communicate()
        self.history = []
        self.base_font_size = 14
        # ▼▼▼ 修正箇所: __init__では取得しない ▼▼▼
        self.persona_manager = self.app.persona_manager 
        self.debate_manager = None # まずはNoneで初期化
        # ▲▲▲ 修正箇所 ▲▲▲

    def link_debate_manager(self, manager):
        """main.pyからDebateManagerを受け取るためのメソッド"""
        self.debate_manager = manager

    def setup_ui(self):
        # (ウィジェットの配置コードは変更なし)
        central_widget = QWidget()
        self.app.setCentralWidget(central_widget)
        root_layout = QHBoxLayout(central_widget)
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        self.setup_chat_widgets(chat_layout)
        root_layout.addWidget(chat_container, 3)
        sidebar_container = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_container)
        self.setup_sidebar_widgets(sidebar_layout)
        sidebar_container.setMinimumWidth(300)
        sidebar_container.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        root_layout.addWidget(sidebar_container, 1)

        self.user_input.returnPressed.connect(self.send_message_event)
        self.send_button.clicked.connect(self.send_message_event)
        self.debate_start_button.clicked.connect(self.start_debate)
        self.debate_stop_button.clicked.connect(self.stop_debate)
        self.comm.user_response_received.connect(self.update_gui_with_user_response)
        self.comm.debate_thinking.connect(self.handle_debate_thinking)
        self.comm.debate_response_received.connect(self.handle_debate_response)
        self.comm.system_message.connect(self.handle_system_message)
        self.comm.set_input_enabled.connect(self.handle_set_input_enabled)
        
        self.user_input.setFocus()
        self.update_font_size(self.base_font_size)
        self.update_participant_list()
    
    # (これ以降のUI関連メソッドは前回から変更ありません)
    def setup_chat_widgets(self, layout):
        self.chat_display = QTextEdit(); self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display, 1)
        input_layout = QHBoxLayout()
        self.user_input = QLineEdit(); self.user_input.setPlaceholderText("メッセージを入力するか、/コマンドを入力...")
        input_layout.addWidget(self.user_input, 1)
        self.send_button = QPushButton("送信")
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)
    def setup_sidebar_widgets(self, layout):
        participants_group = QGroupBox("参加者"); participants_layout = QVBoxLayout()
        self.participant_list = QListWidget(); participants_layout.addWidget(self.participant_list)
        participants_group.setLayout(participants_layout); layout.addWidget(participants_group)
        debate_group = QGroupBox("討論モード"); debate_layout = QFormLayout()
        self.debate_theme_input = QLineEdit(); self.debate_theme_input.setPlaceholderText("討論テーマを入力")
        debate_layout.addRow(QLabel("テーマ:"), self.debate_theme_input)
        self.debate_start_button = QPushButton("討論開始"); self.debate_stop_button = QPushButton("討論停止")
        self.debate_stop_button.setEnabled(False)
        btn_layout = QHBoxLayout(); btn_layout.addWidget(self.debate_start_button); btn_layout.addWidget(self.debate_stop_button)
        debate_layout.addRow(btn_layout)
        debate_group.setLayout(debate_layout); layout.addWidget(debate_group)
        settings_group = QGroupBox("設定"); settings_layout = QVBoxLayout()
        font_size_label = QLabel("フォントサイズ"); self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setRange(10, 24); self.font_slider.setValue(self.base_font_size)
        self.font_slider.valueChanged.connect(self.update_font_size)
        settings_layout.addWidget(font_size_label); settings_layout.addWidget(self.font_slider)
        self.clear_history_button = QPushButton("会話履歴をクリア"); self.clear_history_button.clicked.connect(self.clear_history)
        settings_layout.addWidget(self.clear_history_button)
        settings_group.setLayout(settings_layout); layout.addWidget(settings_group); layout.addStretch(1)
    def update_participant_list(self):
        self.participant_list.clear(); self.participant_list.addItem("User (あなた)")
        for persona in self.persona_manager.get_active_personas(): self.participant_list.addItem(f"{persona.name} ({persona.age}歳)")
    @Slot()
    def send_message_event(self):
        user_text = self.user_input.text().strip()
        if not user_text: return
        self.user_input.clear(); print(f"\n[User]: {user_text}")
        if user_text.startswith('/'): self.display_message("System", f"コマンドを実行します: {user_text}"); return
        self.display_message("User", user_text); self.history.append(f"User: {user_text}")
        if user_text.lower() in ["exit", "quit"]: self.app.close(); return
        active_personas = self.persona_manager.get_active_personas()
        if not active_personas: self.display_message("System", "応答できるAIがいません。"); return
        self.set_input_enabled(False); speaker = random.choice(active_personas)
        self.display_message(speaker.name, "思考中..."); print(f"[{speaker.name}]: 思考中...")
        threading.Thread(target=self.get_ai_response, args=(user_text, speaker), daemon=True).start()
    def get_ai_response(self, prompt, speaker):
        try:
            final_prompt = self.build_prompt(prompt, speaker)
            command = [self.app.gemini_path, "-p", final_prompt]
            result = subprocess.run(command, text=True, encoding='utf-8', check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            ai_text = result.stdout.strip() or "エラー: Gemini CLIから応答がありませんでした。"
            self.history.append(f"{speaker.name}: {ai_text}")
        except Exception as e: ai_text = f"予期せぬエラーが発生しました: {e}"
        print(f"[{speaker.name}]: {ai_text}"); self.comm.user_response_received.emit(ai_text, speaker.name)
    def build_prompt(self, user_prompt, speaker):
        recent_history = "\n".join(self.history[-10:]); persona_prompt = speaker.get_prompt_string()
        return (f"{persona_prompt}あなたは上記のペルソナとしてユーザーとの会話に参加しています。\n"
                f"以下の会話履歴を踏まえ、あなたの役柄に沿って応答してください。\n--- 会話履歴 ---\n{recent_history}\n"
                f"--- 会話履歴ここまで ---\n\nユーザーの最後の発言: \"{user_prompt}\"")
    @Slot(str, str)
    def update_gui_with_user_response(self, ai_text, speaker_name):
        self.update_last_message(speaker_name, ai_text); self.set_input_enabled(True)
    def display_message(self, sender, message):
        formatted_message = message.replace('\n', '<br>')
        self.chat_display.append(f"<b>{sender}:</b> {formatted_message}<br>")
    def update_last_message(self, sender, message):
        cursor = self.chat_display.textCursor(); cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        if f"<b>{sender}:</b> 思考中..." in cursor.selectedText(): cursor.removeSelectedText()
        self.display_message(sender, message)
    @Slot()
    def clear_history(self):
        self.history.clear(); self.chat_display.clear()
        self.display_message("System", "会話履歴がクリアされました。")
    @Slot(int)
    def update_font_size(self, size):
        font = QFont(); font.setPointSize(size); self.chat_display.setFont(font); self.user_input.setFont(font)
        self.send_button.setFont(font)
        for group_box in self.app.findChildren(QGroupBox): group_box.setFont(font)
    @Slot()
    def start_debate(self):
        theme = self.debate_theme_input.text().strip()
        if not theme: self.display_message("System", "討論テーマを入力してください。"); return
        self.debate_start_button.setEnabled(False); self.debate_stop_button.setEnabled(True)
        self.debate_manager.start_debate(theme)
    @Slot()
    def stop_debate(self): self.debate_manager.stop_debate()
    @Slot(str)
    def handle_debate_thinking(self, speaker_name): self.display_message(speaker_name, "思考中...")
    @Slot(str, str)
    def handle_debate_response(self, speaker_name, message): self.update_last_message(speaker_name, message)
    @Slot(str)
    def handle_system_message(self, message): self.display_message("System", message)
    @Slot(bool)
    def handle_set_input_enabled(self, enabled):
        self.set_input_enabled(enabled)
        if enabled: self.debate_start_button.setEnabled(True); self.debate_stop_button.setEnabled(False)
    def set_input_enabled(self, enabled):
        self.user_input.setEnabled(enabled); self.send_button.setEnabled(enabled)
        if enabled: self.user_input.setFocus()

