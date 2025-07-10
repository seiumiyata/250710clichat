import json
from pathlib import Path

class ConfigManager:
    """
    設定値の管理、セッションの保存・再開、コマンドの解析・実行を担うクラス。
    """
    def __init__(self, app):
        self.app = app
        self.config_file = Path("config.json")
        self.settings = self.load_settings()
        self.user_name = self.settings.get("user_name", "User")
        
        # 利用可能なコマンドとその説明、実行する関数をマッピング
        self.commands = {
            "/help": {"func": self.show_help, "desc": "利用可能なコマンドの一覧を表示します。"},
            "/join": {"func": self.join_persona, "desc": "指定したIDのペルソナを会話に参加させます。例: /join 莉子"},
            "/leave": {"func": self.leave_persona, "desc": "指定したIDのペルソナを会話から退出させます。例: /leave 翔太"},
            "/list": {"func": self.list_personas, "desc": "参加可能な全てのペルソナ一覧を表示します。"},
            "/members": {"func": self.list_members, "desc": "現在会話に参加しているメンバーを表示します。"},
            "/save": {"func": self.save_session, "desc": "現在の会話セッションを保存します。例: /save my_session"},
            "/load": {"func": self.load_session, "desc": "保存した会話セッションを再開します。例: /load my_session"},
            "/nick": {"func": self.set_nickname, "desc": "あなたのニックネームを設定します。例: /nick 田中"},
            "/theme": {"func": self.set_debate_theme, "desc": "討論のテーマを設定します。例: /theme 最高の朝食について"},
            "/summary": {"func": self.summarize_history, "desc": "これまでの会話履歴を要約します。（未実装）"}
        }

    def load_settings(self):
        """設定ファイルから設定を読み込む"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, KeyError):
                print(f"警告: '{self.config_file}' の読み込みに失敗しました。デフォルト設定を使用します。")
        return {"user_name": "User", "ui_theme": "dark-blue"} # デフォルト設定

    def save_settings(self):
        """現在の設定を設定ファイルに保存する"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"エラー: 設定の保存に失敗しました。 {e}")

    def execute_command(self, command_string):
        """入力されたコマンド文字列を解析し、対応する関数を実行する"""
        parts = command_string.strip().split()
        command = parts[0].lower()
        args = parts[1:]

        if command in self.commands:
            try:
                self.commands[command]["func"](args)
            except Exception as e:
                self.app.ui.display_message("System", f"コマンドの実行中にエラーが発生しました: {e}")
        else:
            self.app.ui.display_message("System", f"不明なコマンドです: '{command}'\n/help でコマンド一覧を表示できます。")

    # --- 以下、各コマンドに対応するメソッド ---

    def show_help(self, args):
        """/help コマンドの実装"""
        help_text = "<b>利用可能なコマンド一覧:</b><br>"
        for cmd, info in self.commands.items():
            help_text += f"<b>{cmd}</b>: {info['desc']}<br>"
        self.app.ui.display_message("System", help_text)
    
    def list_personas(self, args):
        """/list コマンドの実装"""
        all_personas = self.app.persona_manager.get_all_personas()
        if not all_personas:
            self.app.ui.display_message("System", "利用可能なペルソナがいません。")
            return
        
        persona_list_text = "<b>参加可能なペルソナ一覧:</b><br>"
        for p in all_personas:
            persona_list_text += f"- {p.name} (ID: {p.id})<br>"
        self.app.ui.display_message("System", persona_list_text)

    def list_members(self, args):
        """/members コマンドの実装"""
        active_personas = self.app.persona_manager.get_active_personas()
        member_list = [p.name for p in active_personas]
        message = f"現在の参加者: {self.user_name} (あなた), " + ", ".join(member_list)
        self.app.ui.display_message("System", message)

    def join_persona(self, args):
        """/join コマンドの実装"""
        if not args:
            self.app.ui.display_message("System", "エラー: 参加させるペルソナの名前またはIDを指定してください。")
            return
        
        target_name = args[0]
        all_personas = self.app.persona_manager.get_all_personas()
        persona_to_join = next((p for p in all_personas if p.name == target_name or p.id == target_name), None)

        if not persona_to_join:
            self.app.ui.display_message("System", f"エラー: ペルソナ '{target_name}' が見つかりません。")
            return

        active_ids = {p.id for p in self.app.persona_manager.get_active_personas()}
        if persona_to_join.id in active_ids:
            self.app.ui.display_message("System", f"{persona_to_join.name}さんは既に会話に参加しています。")
            return
            
        active_ids.add(persona_to_join.id)
        self.app.persona_manager.set_active_personas(list(active_ids))
        self.app.ui.update_participant_list()
        self.app.ui.display_message("System", f"{persona_to_join.name}さんが会話に参加しました。")

    def leave_persona(self, args):
        """/leave コマンドの実装"""
        if not args:
            self.app.ui.display_message("System", "エラー: 退出させるペルソナの名前を指定してください。")
            return

        target_name = args[0]
        active_personas = self.app.persona_manager.get_active_personas()
        persona_to_leave = next((p for p in active_personas if p.name == target_name or p.id == target_name), None)
        
        if not persona_to_leave:
            self.app.ui.display_message("System", f"エラー: {target_name}さんは現在会話に参加していません。")
            return
        
        active_ids = {p.id for p in active_personas}
        active_ids.remove(persona_to_leave.id)
        self.app.persona_manager.set_active_personas(list(active_ids))
        self.app.ui.update_participant_list()
        self.app.ui.display_message("System", f"{persona_to_leave.name}さんが会話から退出しました。")

    def set_nickname(self, args):
        """/nick コマンドの実装"""
        if not args:
            self.app.ui.display_message("System", f"現在のニックネームは '{self.user_name}' です。変更するには /nick [新しい名前] と入力してください。")
            return
        
        new_name = args[0]
        old_name = self.user_name
        self.user_name = new_name
        self.settings['user_name'] = new_name
        self.save_settings()
        self.app.ui.update_participant_list()
        self.app.ui.display_message("System", f"ニックネームを '{old_name}' から '{self.user_name}' に変更しました。")

    def set_debate_theme(self, args):
        """/theme コマンドの実装"""
        if not args:
            self.app.ui.display_message("System", "討論テーマを指定してください。例: /theme 最高の朝食について")
            return
        
        theme = " ".join(args)
        self.app.ui.debate_theme_input.setText(theme)
        self.app.ui.display_message("System", f"討論テーマを「{theme}」に設定しました。")

    def save_session(self, args):
        """/save コマンドの実装"""
        if not args:
            self.app.ui.display_message("System", "セッションファイル名を指定してください。例: /save my_talk")
            return
        
        session_name = args[0]
        session_file = Path(f"{session_name}.session.json")
        
        session_data = {
            "history": self.app.ui.history,
            "active_persona_ids": list(self.app.persona_manager.active_personas.keys()),
            "user_name": self.user_name
        }
        
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=4)
            self.app.ui.display_message("System", f"セッションを '{session_file}' に保存しました。")
        except Exception as e:
            self.app.ui.display_message("System", f"セッションの保存に失敗しました: {e}")

    def load_session(self, args):
        """/load コマンドの実装"""
        if not args:
            self.app.ui.display_message("System", "セッションファイル名を指定してください。例: /load my_talk")
            return
            
        session_name = args[0]
        session_file = Path(f"{session_name}.session.json")
        
        if not session_file.exists():
            self.app.ui.display_message("System", f"エラー: セッションファイル '{session_file}' が見つかりません。")
            return

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # データを復元
            self.app.ui.history = session_data.get("history", [])
            self.app.persona_manager.set_active_personas(session_data.get("active_persona_ids", []))
            self.user_name = session_data.get("user_name", "User")
            self.settings['user_name'] = self.user_name
            
            # UIを再描画
            self.app.ui.chat_display.clear()
            for line in self.app.ui.history:
                sender, message = line.split(":", 1)
                self.app.ui.display_message(sender.strip(), message.strip())
            
            self.app.ui.update_participant_list()
            self.app.ui.display_message("System", f"セッション '{session_file}' を再開しました。")

        except Exception as e:
            self.app.ui.display_message("System", f"セッションの再開に失敗しました: {e}")
            
    def summarize_history(self, args):
        """/summary コマンド（未実装）"""
        self.app.ui.display_message("System", "この機能（/summary）は現在実装中です。")

