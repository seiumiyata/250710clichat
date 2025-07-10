import json
from pathlib import Path
import subprocess
import threading

class LearningManager:
    def __init__(self, app):
        self.app = app
        self.learning_file = Path("learning_history.json")
        self.summaries = self.load_summaries()
        self.history_buffers = {}
        self.update_threshold = 15

    def load_summaries(self):
        if self.learning_file.exists():
            try:
                with open(self.learning_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def save_summaries(self):
        try:
            with open(self.learning_file, 'w', encoding='utf-8') as f:
                json.dump(self.summaries, f, ensure_ascii=False, indent=4)
        except IOError as e:
            print(f"エラー: 学習履歴の保存に失敗: {e}")

    def get_summary_for(self, persona_id):
        return self.summaries.get(persona_id, "")

    def add_to_buffer(self, persona_id, turn_context):
        if persona_id not in self.history_buffers:
            self.history_buffers[persona_id] = []
        self.history_buffers[persona_id].append(turn_context)

        if len(self.history_buffers[persona_id]) >= self.update_threshold:
            self.trigger_summary_update(persona_id)

    def trigger_summary_update(self, persona_id):
        buffer = self.history_buffers.pop(persona_id, [])
        if not buffer:
            return

        print(f"情報: {persona_id} の学習履歴（記憶）を更新します...")
        threading.Thread(target=self._update_summary_worker, args=(persona_id, buffer), daemon=True).start()

    def _update_summary_worker(self, persona_id, history_to_summarize):
        persona = self.app.persona_manager.get_persona_by_id(persona_id)
        if not persona: return

        current_summary = self.get_summary_for(persona_id)
        history_text = "\n".join(history_to_summarize)

        prompt = (
            f"あなたはAIペルソナ「{persona.name}」です。\n"
            f"これはあなたのこれまでの会話から得た理解や感情の要約です:\n"
            f"--- 現在のあなたの記憶 ---\n{current_summary}\n--- 現在のあなたの記憶ここまで ---\n\n"
            f"以下の新しい会話内容を踏まえて、あなたの記憶（理解や感情）を更新し、"
            f"新たな記憶の要約を3～4文で作成してください。\n"
            f"--- 新しい会話 ---\n{history_text}\n--- 新しい会話ここまで ---\n\n"
            f"更新されたあなたの記憶の要約:"
        )
        
        try:
            # ▼▼▼ 修正箇所 ▼▼▼
            # シンプルな単一モデル呼び出しに戻す
            command = [self.app.gemini_path, "--model", self.app.model_name]
            result = subprocess.run(
                command, input=prompt, text=True, encoding='utf-8',
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            new_summary = result.stdout.strip()
            if new_summary:
                self.summaries[persona_id] = new_summary
                self.save_summaries()
                print(f"情報: {persona.name} の学習履歴が正常に更新されました。")
            # ▲▲▲ 修正箇所 ▲▲▲
        except Exception as e:
            print(f"エラー: {persona.name} の学習履歴の更新中にエラーが発生: {e}")
            if persona_id not in self.history_buffers:
                self.history_buffers[persona_id] = []
            self.history_buffers[persona_id].extend(history_to_summarize)
