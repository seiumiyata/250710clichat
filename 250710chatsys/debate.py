import threading
import time
import random
import subprocess
import json

class DebateManager:
    def __init__(self, app):
        self.app = app
        self.comm = None
        self.is_debating = False
        self.is_autochatting = False
        self.thread = None
        self.theme = ""
        self.moderator = None
        self.speakers = []
        self.turn_index = 0
        self.history_context = []
        self.learning_manager = self.app.learning_manager

    def link_comm(self, comm):
        self.comm = comm

    def start_debate(self, theme):
        if self.is_debating or self.is_autochatting: return
        self.theme = theme
        self.is_debating = True
        self.history_context = [f"【討論テーマ】: {self.theme}"]
        active_personas = self.app.persona_manager.get_active_personas()
        if len(active_personas) < 2:
            self.comm.system_message.emit("討論には最低2人のAIが必要です。"); self.is_debating = False; return
        self.moderator = random.choice(active_personas)
        self.speakers = [p for p in active_personas if p.id != self.moderator.id]; random.shuffle(self.speakers)
        self.turn_index = -1
        start_message = (f"討論モードを開始します。\nテーマ: 「{self.theme}」\n司会進行は {self.moderator.name} さんです。")
        self.comm.system_message.emit(start_message)
        self.thread = threading.Thread(target=self._run_loop, daemon=True); self.thread.start()

    def start_autochat(self):
        if self.is_debating or self.is_autochatting: return
        self.is_autochatting = True
        if not self.history_context or "【雑談中】" not in self.history_context[0]:
            self.history_context.insert(0, "【雑談中】")
        self.speakers = self.app.persona_manager.get_active_personas()
        if len(self.speakers) < 2: self.is_autochatting = False; return
        random.shuffle(self.speakers); self.turn_index = -1
        self.thread = threading.Thread(target=self._run_loop, daemon=True); self.thread.start()

    def conclude_debate(self):
        if not self.is_debating: return
        self.is_debating = False
        self.comm.system_message.emit("討論を終了し、司会者が総括します...")
        threading.Thread(target=self._run_conclusion_worker, daemon=True).start()

    def _run_conclusion_worker(self):
        if not self.moderator: self.comm.conclusion_finished.emit(); return
        speaker = self.moderator
        task_prompt = "あなたは司会です。これまでの議論全体を振り返り、各意見をまとめ、討論を締めくくる総括の弁を述べてください。"
        print(f"総括中... 司会者: {speaker.name}");
        self.comm.debate_thinking.emit(speaker.name)
        
        ai_text = self._generate_response(speaker, task_prompt)
        
        self.history_context.append(f"{speaker.name}: {ai_text}")
        self.app.ui.history.append(f"{speaker.name}: {ai_text}")
        self.comm.debate_response_received.emit(speaker.name, ai_text)
        self.comm.conclusion_finished.emit()

    def stop_all_ai_talk(self):
        if self.is_debating:
            self.is_debating = False; self.comm.system_message.emit("討論モードが中断されました。")
        if self.is_autochatting:
            self.is_autochatting = False; print("情報: 自動会話を中断しました。")

    def _run_loop(self):
        time.sleep(random.uniform(3, 5))
        while self.is_debating or self.is_autochatting:
            self._run_turn()
            if not (self.is_debating or self.is_autochatting): break
            time.sleep(random.uniform(5, 10))
        print("情報: 自動会話ループが終了しました。")

    def _run_turn(self):
        if not (self.is_debating or self.is_autochatting): return
        self.turn_index += 1
        task_prompt = ""
        
        if self.is_debating:
            if self.turn_index == 0: speaker = self.moderator; task_prompt = "あなたが司会です。このテーマで議論を開始してください。"
            else: speaker_index = (self.turn_index - 1) % len(self.speakers); speaker = self.speakers[speaker_index]; task_prompt = "前の意見を踏まえ、あなたの立場で意見を述べてください。"
        else:
            speaker_index = self.turn_index % len(self.speakers)
            speaker = self.speakers[speaker_index]
            user_name = self.app.config_manager.user_name
            if len(self.history_context) > 2 and random.random() < 0.15:
                task_prompt = f"これまでの会話の流れを踏まえ、参加者の一人である「{user_name}」さんに質問を投げかけて、会話に引き込んでください。"
            elif len(self.history_context) > 3 and random.random() < 0.2:
                task_prompt = "直前の会話の中から興味深いキーワードを一つ選び、それについて深掘りするような質問を投げかけて、会話を盛り上げてください。"
            else:
                task_prompt = "雑談です。直前の会話の流れを踏まえ、自由に発言してください。新しい話題を始めても構いません。"

        print(f"自動会話中... 次の発言者: {speaker.name}"); self.comm.debate_thinking.emit(speaker.name)
        
        ai_text = self._generate_response(speaker, task_prompt)

        if not (self.is_debating or self.is_autochatting): return
        
        self.history_context.append(f"{speaker.name}: {ai_text}")
        self.app.ui.history.append(f"{speaker.name}: {ai_text}")
        self.comm.debate_response_received.emit(speaker.name, ai_text)

    def _generate_response(self, speaker, task_prompt):
        final_prompt = self._build_turn_prompt(speaker, task_prompt)
        ai_text = ""
        try:
            # ▼▼▼ 修正箇所 ▼▼▼
            # シンプルな単一モデル呼び出しに戻す
            command = [self.app.gemini_path, "--model", self.app.model_name]
            result = subprocess.run(
                command, input=final_prompt, text=True, encoding='utf-8',
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            ai_text = result.stdout.strip() or "(…)"
            if self.history_context:
                turn_context = f"{self.history_context[-1]}\n{speaker.name}: {ai_text}"
                self.learning_manager.add_to_buffer(speaker.id, turn_context)
            # ▲▲▲ 修正箇所 ▲▲▲
        except Exception as e:
            error_message = f"エラーが発生しました: {e}"
            if isinstance(e, subprocess.CalledProcessError):
                error_message = f"AI応答エラー: {e.stderr.strip()}"
            print(error_message)
            ai_text = error_message
            self.stop_all_ai_talk()
            
        return ai_text

    def _build_turn_prompt(self, speaker, task_prompt):
        persona_prompt = speaker.get_prompt_string()
        history_str = "\n".join(self.history_context[-10:])
        mode_desc = f"【討論テーマ】: {self.theme}" if self.is_debating else "【雑談】"
        user_name = self.app.config_manager.user_name

        learning_summary = self.learning_manager.get_summary_for(speaker.id)
        summary_instruction = ""
        if learning_summary:
            summary_instruction = (
                f"これはあなたの過去の会話からの学びや感情の要約です。この内容も参考にしてください:\n"
                f"--- あなたの記憶の要約 ---\n{learning_summary}\n--- あなたの記憶の要約ここまで ---\n"
            )
        
        participants_info = f"あなたは今、他のAIや人間（ユーザー名: {user_name}）と会話をしています。"
        identity_instruction = f"会話履歴の中の `{speaker.name}:` で始まる発言は、あなた自身の過去の発言です。"
        user_interaction_instruction = f"ユーザー（{user_name}）も会話に参加します。ユーザーの発言も踏まえて、自然に応答してください。"
        output_instruction = f"あなたの応答には、あなた自身の名前（{speaker.name}）を含めないでください。"

        return (f"{persona_prompt}\n{participants_info}\n{mode_desc}\n"
                f"{summary_instruction}\n"
                f"【重要な指示】:\n"
                f"- {identity_instruction}\n- {user_interaction_instruction}\n- {output_instruction}\n\n"
                f"--- 直前の会話 ---\n{history_str}\n--- 発言ここまで ---\n\n"
                f"【あなたの今回の役割】: {task_prompt}\n\nあなたの発言だけを生成してください:")
