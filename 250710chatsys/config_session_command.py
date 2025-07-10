import json
from pathlib import Path
import threading
import subprocess
import random

class ConfigManager:
    def __init__(self, app):
        self.app = app
        self.config_file = Path("config.json")
        self.settings = self.load_settings()
        self.user_name = self.settings.get("user_name", "User")
        self.is_compressing = False

        self.commands = {
            "/ask_all": {"func": self.ask_all, "desc": "参加者全員に問いかけます。 例: /ask_all 今日の気分は？"},
            "/help": {"func": self.show_help, "desc": "利用可能なコマンド一覧。"},
            "/group": {"func": self.group_personas, "desc": "参加者をグループ分けします。/group help 参照。"},
            "/join": {"func": self.join_persona, "desc": "ペルソナを会話に参加させます。 例: /join 莉子"},
            "/leave": {"func": self.leave_persona, "desc": "ペルソナを会話から退出させます。 例: /leave 翔太"},
            "/list": {"func": self.list_personas, "desc": "参加可能な全ペルソナ一覧を表示。"},
            "/members": {"func": self.list_members, "desc": "現在の参加メンバーを表示。"},
            "/save": {"func": self.save_session, "desc": "現在の会話を保存します。 例: /save my_session"},
            "/load": {"func": self.load_session, "desc": "会話を再開します。 例: /load my_session"},
            "/nick": {"func": self.set_nickname, "desc": "あなたの名前を設定します。 例: /nick 田中"},
            "/compress": {"func": self.manual_compress_history, "desc": "会話履歴を手動で圧縮します。"}
        }
    
    def ask_all(self, args):
        if not args:
            self.app.ui.display_message("System", "エラー: /ask_all の後にメッセージを続けてください。")
            return
        
        question = " ".join(args)
        self.app.ui.trigger_all_personas_response(question)

    def trigger_compression(self):
        if self.is_compressing: return
        self.is_compressing = True
        self.app.ui.display_message("System", "会話履歴が長くなったため、古い内容を自動的に要約・圧縮します...")
        threading.Thread(target=self._compress_logic, daemon=True).start()

    def manual_compress_history(self, args):
        if self.is_compressing: self.app.ui.display_message("System", "既に圧縮処理が実行中です。"); return
        self.is_compressing = True
        self.app.ui.display_message("System", "会話履歴の圧縮を開始します...")
        threading.Thread(target=self._compress_logic, daemon=True).start()

    def _compress_logic(self):
        history = self.app.ui.history
        if len(history) < 20:
            self.app.ui.display_message("System", "履歴が20件未満のため、圧縮は不要です。")
            self.is_compressing = False
            return
        
        split_point = int(len(history) * 0.8)
        to_compress = history[:split_point]; remaining = history[split_point:]
        history_text = "\n".join(to_compress)
        prompt = f"以下の会話を、今後の文脈として残すために1-2文で超要約してください:\n\n---\n{history_text}\n---"
        
        summary = ""
        try:
            # ▼▼▼ 修正箇所 ▼▼▼
            # シンプルな単一モデル呼び出しに戻す
            command = [self.app.gemini_path, "--model", self.app.model_name]
            result = subprocess.run(
                command, input=prompt, text=True, encoding='utf-8',
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            summary = result.stdout.strip() or "要約失敗"
            self.app.ui.history = [f"System: [これまでの会話の要約] {summary}"] + remaining
            self.app.ui.chat_display.clear()
            for line in self.app.ui.history:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    self.app.ui.display_message(parts[0].strip(), parts[1].strip())
            self.app.ui.display_message("System", "履歴の圧縮が完了しました。")
            # ▲▲▲ 修正箇所 ▲▲▲
        except Exception as e:
            error_message = f"履歴の圧縮中にエラーが発生しました: {e}"
            if isinstance(e, subprocess.CalledProcessError):
                error_message = f"履歴の圧縮中にAI応答エラー: {e.stderr.strip()}"
            self.app.ui.display_message("System", error_message)
        finally:
            self.is_compressing = False

    def load_settings(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f: return json.load(f)
            except: pass
        return {"user_name": "User"}

    def save_settings(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f: json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception as e: print(f"エラー: 設定の保存に失敗: {e}")

    def execute_command(self, command_string):
        parts = command_string.strip().split(); command = parts[0].lower(); args = parts[1:]
        if command in self.commands:
            try: self.commands[command]["func"](args)
            except Exception as e: self.app.ui.display_message("System", f"コマンド実行エラー: {e}")
        else: self.app.ui.display_message("System", f"不明なコマンド: '{command}'")
    
    def group_personas(self, args):
        if not args or args[0] == 'help':
            help_text = "/group コマンドの使用法:\n/group random [人数]\n/group gender [男性|女性]\n/group age [10s|20s|...]\n/group all\n/group none"
            self.app.ui.display_message("System", help_text); return

        subcommand = args[0].lower(); all_personas = self.app.persona_manager.get_all_personas(); filtered_ids = []; message = ""
        try:
            if subcommand == 'random': num = int(args[1]); filtered_ids = [p.id for p in random.sample(all_personas, min(num, len(all_personas)))]; message = f"ランダムに{len(filtered_ids)}名を選択。"
            elif subcommand == 'gender': target_gender = args[1]; filtered_ids = [p.id for p in all_personas if p.gender == target_gender]; message = f"性別「{target_gender}」を選択。"
            elif subcommand == 'age': age_group = args[1].replace('s', ''); min_age = int(age_group); max_age = min_age + 9; filtered_ids = [p.id for p in all_personas if min_age <= p.age <= max_age]; message = f"「{age_group}代」を選択。"
            elif subcommand == 'all': filtered_ids = [p.id for p in all_personas]; message = "全員を選択。"
            elif subcommand == 'none': filtered_ids = []; message = "全員の選択を解除。"
            else: self.app.ui.display_message("System", f"不明なサブコマンド: {subcommand}"); return
            self.app.persona_manager.set_active_personas(filtered_ids); self.app.ui.update_participant_list(); self.app.ui.display_message("System", message)
        except (IndexError, ValueError): self.app.ui.display_message("System", "コマンドの引数が正しくありません。")

    def show_help(self, args):
        help_text = "利用可能なコマンド一覧:\n"
        help_text += "\n".join([f"{cmd}: {info['desc']}" for cmd, info in self.commands.items()])
        self.app.ui.display_message("System", help_text)

    def join_persona(self, args):
        if not args: self.app.ui.display_message("System", "エラー: 参加させるペルソナの名前を指定してください。"); return
        target_name = args[0]; persona_to_join = next((p for p in self.app.persona_manager.get_all_personas() if p.name == target_name or p.id == target_name), None)
        if not persona_to_join: self.app.ui.display_message("System", f"エラー: ペルソナ '{target_name}' が見つかりません。"); return
        active_ids = {p.id for p in self.app.persona_manager.get_active_personas()}
        if persona_to_join.id in active_ids: self.app.ui.display_message("System", f"{persona_to_join.name}さんは既に会話に参加しています。"); return
        active_ids.add(persona_to_join.id); self.app.persona_manager.set_active_personas(list(active_ids)); self.app.ui.update_participant_list(); self.app.ui.display_message("System", f"{persona_to_join.name}さんが会話に参加しました。")

    def leave_persona(self, args):
        if not args: self.app.ui.display_message("System", "エラー: 退出させるペルソナの名前を指定してください。"); return
        target_name = args[0]; persona_to_leave = next((p for p in self.app.persona_manager.get_active_personas() if p.name == target_name or p.id == target_name), None)
        if not persona_to_leave: self.app.ui.display_message("System", f"{target_name}さんは参加していません。"); return
        active_ids = {p.id for p in self.app.persona_manager.get_active_personas()}; active_ids.remove(persona_to_leave.id); self.app.persona_manager.set_active_personas(list(active_ids)); self.app.ui.update_participant_list(); self.app.ui.display_message("System", f"{persona_to_leave.name}さんが会話から退出しました。")

    def list_personas(self, args):
        all_personas = self.app.persona_manager.get_all_personas()
        persona_list_text = "参加可能なペルソナ一覧:\n" + "\n".join([f"- {p.name} (ID: {p.id})" for p in all_personas])
        self.app.ui.display_message("System", persona_list_text)

    def list_members(self, args):
        active_personas = self.app.persona_manager.get_active_personas()
        message = f"現在の参加者: {self.user_name} (あなた), " + ", ".join([p.name for p in active_personas])
        self.app.ui.display_message("System", message)

    def set_nickname(self, args):
        if not args: self.app.ui.display_message("System", f"現在のニックネームは '{self.user_name}' です。"); return
        new_name = args[0]; old_name = self.user_name; self.user_name = new_name; self.settings['user_name'] = new_name; self.save_settings(); self.app.ui.update_participant_list(); self.app.ui.display_message("System", f"ニックネームを '{old_name}' から '{self.user_name}' に変更しました。")

    def save_session(self, args):
        if not args: self.app.ui.display_message("System", "セッションファイル名を指定してください。"); return
        session_name = args[0]; session_file = Path(f"{session_name}.session.json")
        session_data = {"history": self.app.ui.history, "active_persona_ids": list(self.app.persona_manager.active_personas.keys()), "user_name": self.user_name}
        try:
            with open(session_file, 'w', encoding='utf-8') as f: json.dump(session_data, f, ensure_ascii=False, indent=4)
            self.app.ui.display_message("System", f"セッションを '{session_file}' に保存しました。")
        except Exception as e: self.app.ui.display_message("System", f"セッションの保存に失敗: {e}")

    def load_session(self, args):
        if not args: self.app.ui.display_message("System", "セッションファイル名を指定してください。"); return
        session_name = args[0]; session_file = Path(f"{session_name}.session.json")
        if not session_file.exists(): self.app.ui.display_message("System", f"エラー: セッションファイル '{session_file}' が見つかりません。"); return
        try:
            with open(session_file, 'r', encoding='utf-8') as f: session_data = json.load(f)
            self.app.ui.history = session_data.get("history", [])
            self.app.persona_manager.set_active_personas(session_data.get("active_persona_ids", []))
            self.user_name = session_data.get("user_name", "User"); self.settings['user_name'] = self.user_name
            self.app.ui.chat_display.clear()
            for line in self.app.ui.history:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    self.app.ui.display_message(parts[0].strip(), parts[1].strip())
            self.app.ui.update_participant_list()
            self.app.ui.display_message("System", f"セッション '{session_file}' を再開しました。")
        except Exception as e: self.app.ui.display_message("System", f"セッションの再開に失敗しました: {e}")
