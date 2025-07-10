import threading
import time
import random
import subprocess # ← ★★★ この一行を追加しました ★★★

class DebateManager:
    """
    AI同士の自動会話・討論モードを管理するクラス。
    """
    def __init__(self, app):
        self.app = app
        self.comm = None
        self.is_debating = False
        self.debate_thread = None
        self.theme = ""
        self.moderator = None
        self.speakers = []
        self.turn_index = 0
        self.debate_history = []

    def link_comm(self, comm):
        """main.pyからCommunicateオブジェクトを受け取るためのメソッド"""
        self.comm = comm

    def start_debate(self, theme):
        """討論モードを開始する"""
        if self.is_debating:
            print("警告: 既に討論が進行中です。")
            return

        active_personas = self.app.persona_manager.get_active_personas()
        if len(active_personas) < 2:
            self.comm.system_message.emit("討論を開始するには、最低でも2人のAI参加者が必要です。")
            return

        self.theme = theme
        self.is_debating = True
        self.debate_history = [f"【テーマ】: {self.theme}"]
        
        self.moderator = random.choice(active_personas)
        self.speakers = [p for p in active_personas if p.id != self.moderator.id]
        random.shuffle(self.speakers)
        self.turn_index = -1

        start_message = (f"討論モードを開始します。\n"
                         f"テーマ: 「{self.theme}」\n"
                         f"司会進行は {self.moderator.name} さんです。")
        self.comm.system_message.emit(start_message)
        print(f"\n{start_message}")

        self.debate_thread = threading.Thread(target=self._run_debate_loop, daemon=True)
        self.debate_thread.start()

    def stop_debate(self):
        """討論モードを終了する"""
        if not self.is_debating:
            return
        
        self.is_debating = False
        print("情報: 討論の終了を待っています...")
        self.comm.system_message.emit("討論モードが終了しました。")
        print("\n討論モードが終了しました。")

    def _run_debate_loop(self):
        """討論の進行を管理するメインループ"""
        self.comm.set_input_enabled.emit(False)

        while self.is_debating:
            self._run_debate_turn()
            if not self.is_debating:
                break
            # 討論が続く場合、次の発言までの間隔を設ける
            time.sleep(random.uniform(5, 10))

        print("情報: 討論ループが終了しました。")
        self.comm.set_input_enabled.emit(True)

    def _run_debate_turn(self):
        """討論の1ターンを実行する"""
        if not self.is_debating:
            return

        self.turn_index += 1
        if self.turn_index == 0:
            speaker = self.moderator
            task_prompt = "あなたが司会です。このテーマについて、議論の口火を切る形で皆に問いかけてください。"
        else:
            speaker_index = (self.turn_index - 1) % len(self.speakers)
            speaker = self.speakers[speaker_index]
            task_prompt = "前の人の意見を踏まえ、あなた自身の立場で意見を述べてください。"

        print(f"次の発言者: {speaker.name}")
        self.comm.debate_thinking.emit(speaker.name)

        final_prompt = self._build_debate_prompt(speaker, task_prompt)
        
        try:
            command = [self.app.gemini_path, "-p", final_prompt]
            result = subprocess.run(
                command, text=True, encoding='utf-8', check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            ai_text = result.stdout.strip() or "(沈黙している...)"
        except Exception as e:
            ai_text = f"(エラーにより発言できませんでした: {e})"

        self.debate_history.append(f"{speaker.name}: {ai_text}")
        self.comm.debate_response_received.emit(speaker.name, ai_text)

    def _build_debate_prompt(self, speaker, task_prompt):
        """討論用に、AIに渡すプロンプトを構築する"""
        persona_prompt = speaker.get_prompt_string()
        history_str = "\n".join(self.debate_history[-10:])

        system_prompt = (f"{persona_prompt}\n"
                         "あなたは今、他のAIペルソナたちと以下のテーマで討論会をしています。\n"
                         f"【テーマ】: {self.theme}\n\n"
                         "--- これまでの発言 ---\n"
                         f"{history_str}\n"
                         "--- これまでの発言ここまで ---\n\n"
                         f"【あなたの今回の役割】: {task_prompt}\n\n"
                         "以上の状況を踏まえ、あなたの役柄に沿って、次の発言を生成してください。")
        return system_prompt
