import sys
import subprocess
import threading
import random
import json
import time

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QLineEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
    QListWidget, QLabel, QGroupBox, QSizePolicy,
    QFormLayout, QSlider
)
from PySide6.QtCore import Slot, Signal, QObject, Qt, QTimer
from PySide6.QtGui import QTextCursor, QFont

class Communicate(QObject):
    user_response_received = Signal(str, str)
    debate_thinking = Signal(str)
    debate_response_received = Signal(str, str)
    system_message = Signal(str)
    conclusion_finished = Signal()

class UIHandler:
    def __init__(self, app):
        self.app = app
        self.comm = Communicate()
        self.history = []
        self.base_font_size = 14
        self.persona_manager = self.app.persona_manager
        self.config_manager = self.app.config_manager
        self.learning_manager = self.app.learning_manager
        self.debate_manager = None
        self.sender_colors = {}
        self.autochat_timer = QTimer()
        self.autochat_timer.setSingleShot(True)
        self.autochat_timer.setInterval(15000)
        self.autochat_timer.timeout.connect(self.start_autochat)

    def link_debate_manager(self, manager): self.debate_manager = manager

    def setup_ui(self):
        central_widget = QWidget(); self.app.setCentralWidget(central_widget)
        root_layout = QHBoxLayout(central_widget)
        chat_container = QWidget(); chat_layout = QVBoxLayout(chat_container)
        self.setup_chat_widgets(chat_layout)
        root_layout.addWidget(chat_container, 3)
        sidebar_container = QWidget(); sidebar_layout = QVBoxLayout(sidebar_container)
        self.setup_sidebar_widgets(sidebar_layout)
        sidebar_container.setMinimumWidth(300); sidebar_container.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        root_layout.addWidget(sidebar_container, 1)

        self.user_input.returnPressed.connect(self.send_message_event)
        self.user_input.textChanged.connect(self.on_user_typing)
        self.send_button.clicked.connect(self.send_message_event)
        self.debate_start_button.clicked.connect(self.start_debate)
        self.debate_stop_button.clicked.connect(self.conclude_debate_event)
        self.font_slider.valueChanged.connect(self.update_font_size)
        self.comm.user_response_received.connect(self.handle_ai_response)
        self.comm.debate_thinking.connect(self.handle_autochat_thinking)
        self.comm.debate_response_received.connect(self.handle_autochat_response)
        self.comm.system_message.connect(self.handle_system_message)
        self.comm.conclusion_finished.connect(self.on_conclusion_finished)

        self.user_input.setFocus()
        self.update_font_size(self.base_font_size)
        self.update_participant_list()
        self.autochat_timer.start()

    def setup_chat_widgets(self, layout):
        self.chat_display = QTextEdit(); self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display, 1)
        input_layout = QHBoxLayout()
        self.user_input = QLineEdit(); self.user_input.setPlaceholderText("メッセージを入力...")
        input_layout.addWidget(self.user_input, 1)
        self.send_button = QPushButton("送信"); input_layout.addWidget(self.send_button)
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
        font_size_layout = QHBoxLayout()
        font_size_label = QLabel("フォント:")
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setRange(10, 24)
        self.font_slider.setValue(self.base_font_size)
        font_size_layout.addWidget(font_size_label)
        font_size_layout.addWidget(self.font_slider)
        settings_layout.addLayout(font_size_layout)
        
        self.clear_history_button = QPushButton("会話履歴をクリア"); self.clear_history_button.clicked.connect(self.clear_history)
        settings_layout.addWidget(self.clear_history_button)
        
        settings_group.setLayout(settings_layout); layout.addWidget(settings_group); layout.addStretch(1)

    @Slot(int)
    def update_font_size(self, size):
        font = QFont(); font.setPointSize(size)
        self.chat_display.setFont(font)
        self.user_input.setFont(font)
        self.send_button.setFont(font)
        for child in self.app.findChildren(QWidget):
            if isinstance(child, (QGroupBox, QLabel, QListWidget, QLineEdit, QPushButton)):
                child.setFont(font)

    def update_participant_list(self):
        self.participant_list.clear()
        self.participant_list.addItem(f"{self.config_manager.user_name} (あなた)")
        for persona in self.persona_manager.get_active_personas():
            self.participant_list.addItem(f"{persona.name} ({persona.age}歳)")

    @Slot()
    def on_user_typing(self):
        if self.debate_manager and self.debate_manager.is_autochatting:
            self.debate_manager.stop_all_ai_talk()
        self.autochat_timer.start()

    @Slot()
    def start_autochat(self):
        if self.debate_manager and not self.debate_manager.is_debating: self.debate_manager.start_autochat()

    @Slot()
    def start_debate(self):
        self.on_user_typing()
        theme = self.debate_theme_input.text().strip()
        if not theme: self.display_message("System", "討論テーマを入力してください。"); return
        if self.debate_manager:
            self.set_debate_buttons_enabled(False)
            self.debate_manager.start_debate(theme)

    @Slot()
    def conclude_debate_event(self):
        if self.debate_manager: self.debate_manager.conclude_debate()
    
    @Slot()
    def on_conclusion_finished(self):
        print("情報: 司会者の総括が完了しました。")
        self.set_debate_buttons_enabled(True)
        self.on_user_typing()

    def set_debate_buttons_enabled(self, start_is_enabled):
        self.debate_start_button.setEnabled(start_is_enabled)
        self.debate_stop_button.setEnabled(not start_is_enabled)

    @Slot()
    def send_message_event(self):
        self.on_user_typing()
        user_text = self.user_input.text().strip()
        if not user_text: return
        self.user_input.clear()
        
        if user_text.startswith('/'):
            print(f"\n[Command]: {user_text}")
            self.config_manager.execute_command(user_text)
            return

        print(f"\n[{self.config_manager.user_name}]: {user_text}")
        self.history.append(f"{self.config_manager.user_name}: {user_text}")
        self.display_message(self.config_manager.user_name, user_text)

        if self.debate_manager and self.debate_manager.is_debating:
            self.debate_manager.history_context.append(f"{self.config_manager.user_name}: {user_text}")
            print("情報: ユーザーが討論に参加しました。次のAIのターンを待ちます。")
            return

        active_personas = self.persona_manager.get_active_personas()
        if not active_personas: return

        speaker = None
        for p in active_personas:
            if p.name in user_text:
                speaker = p; print(f"情報: {p.name} が指名されました。"); break
        if speaker is None:
            speaker = random.choice(active_personas); print(f"情報: ランダムで {speaker.name} が応答します。")

        self.display_message(speaker.name, "入力中...")
        threading.Thread(target=self.get_ai_response, args=(user_text, speaker), daemon=True).start()

    def trigger_all_personas_response(self, question):
        user_text = f"{self.config_manager.user_name}: (全員へ) {question}"
        self.history.append(user_text)
        self.display_message(self.config_manager.user_name, f"(全員へ) {question}")
        threading.Thread(target=self._ask_all_worker, args=(question,), daemon=True).start()

    def _ask_all_worker(self, question):
        active_personas = self.persona_manager.get_active_personas()
        if not active_personas: return
        for speaker in active_personas:
            self.comm.debate_thinking.emit(speaker.name)
            self.get_ai_response(question, speaker)
            time.sleep(random.uniform(2, 4))
            
    def get_ai_response(self, prompt_text, speaker):
        final_prompt = self.build_prompt(prompt_text, speaker)
        ai_text = ""
        try:
            # ▼▼▼ 修正箇所 ▼▼▼
            # シンプルな単一モデル呼び出しに戻す
            command = [self.app.gemini_path, "--model", self.app.model_name]
            result = subprocess.run(
                command, input=final_prompt, text=True, encoding='utf-8',
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            ai_text = result.stdout.strip() or "(...)"
            self.history.append(f"{speaker.name}: {ai_text}")
            turn_context = f"{self.history[-2]}\n{self.history[-1]}"
            self.learning_manager.add_to_buffer(speaker.id, turn_context)
            # ▲▲▲ 修正箇所 ▲▲▲
        except Exception as e:
            error_message = f"エラーが発生しました: {e}"
            if isinstance(e, subprocess.CalledProcessError):
                error_message = f"AI応答エラー: {e.stderr.strip()}"
            print(error_message)
            ai_text = error_message

        self.comm.user_response_received.emit(ai_text, speaker.name)

    def build_prompt(self, user_prompt, speaker):
        recent_history = "\n".join(self.history[-10:])
        persona_prompt = speaker.get_prompt_string()
        
        learning_summary = self.learning_manager.get_summary_for(speaker.id)
        summary_instruction = ""
        if learning_summary:
            summary_instruction = (
                f"これはあなたの過去の会話からの学びや感情の要約です。この内容も参考にしてください:\n"
                f"--- あなたの記憶の要約 ---\n{learning_summary}\n--- あなたの記憶の要約ここまで ---\n"
            )

        identity_instruction = f"会話履歴の中の `{speaker.name}:` で始まる発言は、あなた自身の過去の発言です。"
        formatting_instruction = "あなたの発言が長くなる場合は、人間が読みやすいように、適度に改行を入れてください。"
        output_instruction = f"あなたの応答には、あなた自身の名前（{speaker.name}）を含めないでください。"
        
        is_ask_all = "(全員へ)" in user_prompt or user_prompt.startswith("/ask_all")
        last_statement_line = "全員に向けられた質問" if is_ask_all else "ユーザーの最後の発言"

        return (f"{persona_prompt}あなたは会話に参加しています。\n"
                f"{summary_instruction}\n"
                f"以下の会話履歴とあなたの役割を踏まえ、応答してください。\n"
                f"- {identity_instruction}\n- {formatting_instruction}\n- {output_instruction}\n"
                f"--- 会話履歴 ---\n{recent_history}\n--- 会話履歴ここまで ---\n\n"
                f"{last_statement_line}: \"{user_prompt.replace('(全員へ)','')}\"\n\nあなたの応答:")

    @Slot(str, str)
    def handle_ai_response(self, ai_text, speaker_name):
        self.update_last_message(speaker_name, ai_text); self.autochat_timer.start()

    @Slot(str)
    def handle_autochat_thinking(self, speaker_name):
        self.display_message(speaker_name, "入力中...")

    @Slot(str, str)
    def handle_autochat_response(self, speaker_name, message):
        self.update_last_message(speaker_name, message)

    @Slot(str)
    def handle_system_message(self, message): self.display_message("System", message)

    def get_sender_color(self, sender):
        if sender == "System": return "#B0B0B0"
        if sender == self.config_manager.user_name: return "#32CD32"
        if sender not in self.sender_colors:
            r, g, b = [random.randint(130, 250) for _ in range(3)]
            if r > 220 and g > 220 and b > 220:
                idx = random.randint(0, 2);
                if idx == 0: r -= random.randint(80, 100)
                elif idx == 1: g -= random.randint(80, 100)
                else: b -= random.randint(80, 100)
            self.sender_colors[sender] = f"#{r:02x}{g:02x}{b:02x}"
        return self.sender_colors[sender]

    def display_message(self, sender, message):
        name_color = self.get_sender_color(sender)
        safe_message = (message.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace(chr(10), "<br>"))
        html = (f'<p style="margin-bottom: 8px; margin-left: 5px;">'
                f'<b style="color: {name_color};">{sender}</b><br>'
                f'<span style="margin-left: 10px;">{safe_message}</span></p>')
        self.chat_display.append(html)
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    def update_last_message(self, sender, message):
        cursor = self.chat_display.textCursor(); cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        if "入力中..." in cursor.selection().toHtml():
            cursor.removeSelectedText()
            new_cursor = self.chat_display.textCursor(); new_cursor.movePosition(QTextCursor.MoveOperation.End)
            new_cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            if not new_cursor.hasSelection() or new_cursor.selectedText().strip() == "": new_cursor.removeSelectedText()
        self.display_message(sender, message)

    @Slot()
    def clear_history(self):
        self.history.clear()
        if self.debate_manager: self.debate_manager.history_context.clear()
        self.learning_manager.summaries.clear()
        self.learning_manager.save_summaries()
        self.chat_display.clear(); self.display_message("System", "会話履歴と学習履歴がクリアされました。"); self.on_user_typing()
