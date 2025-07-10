import json
from pathlib import Path

class Persona:
    """
    個々のAIペルソナの全データを保持し、プロンプトを生成するクラス。
    """
    def __init__(self, persona_data):
        # 必須項目
        self.id = persona_data.get('id', 'unknown')
        self.name = persona_data.get('name', '名無し')
        
        # ▼▼▼ 修正箇所 ▼▼▼
        # 新しい詳細項目もすべて読み込む
        self.age = persona_data.get('age', '不明')
        self.gender = persona_data.get('gender', '不明')
        self.occupation = persona_data.get('occupation', '不明')
        self.personality = persona_data.get('personality', '')
        self.background = persona_data.get('background', '')
        self.values = persona_data.get('values', '')
        self.quirks = persona_data.get('quirks', '')
        self.goals = persona_data.get('goals', '')
        self.speaking_style = persona_data.get('speaking_style', '普通に話します。')
        # ▲▲▲ 修正箇所 ▲▲▲

    def get_prompt_string(self):
        """
        AIに渡すための、構造化された詳細なプロンプト文字列を生成する。
        """
        # ▼▼▼ 修正箇所 (プロンプト生成ロジックの全面改訂) ▼▼▼
        return (
            f"あなたは以下の設定を持つAIペルソナ「{self.name}」です。この設定に厳密に従って応答してください。\n"
            f"--- 基本情報 ---\n"
            f"名前: {self.name}\n"
            f"年齢: {self.age}\n"
            f"性別: {self.gender}\n"
            f"職業: {self.occupation}\n\n"
            f"--- 詳細な人格設定 ---\n"
            f"性格: {self.personality}\n"
            f"背景: {self.background}\n"
            f"価値観: {self.values}\n"
            f"癖・特徴: {self.quirks}\n"
            f"目標・願望: {self.goals}\n\n"
            f"--- 話し方のルール ---\n"
            f"{self.speaking_style}\n"
        )
        # ▲▲▲ 修正箇所 ▲▲▲

class PersonaManager:
    """
    全てのペルソナを管理し、現在アクティブなペルソナを制御するクラス。
    """
    def __init__(self):
        self.persona_file = Path("personas.json")
        self.all_personas = self._load_all_personas()
        self.active_personas = {} # 現在会話に参加しているペルソナ (id -> Persona object)
        # 起動時は全員参加
        self.set_active_personas([p.id for p in self.all_personas])

    def _load_all_personas(self):
        """personas.jsonから全てのペルソナ情報を読み込む"""
        if not self.persona_file.exists():
            print(f"エラー: {self.persona_file} が見つかりません。")
            return []
        
        try:
            with open(self.persona_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                personas = [Persona(p_data) for p_data in data]
                print(f"情報: {len(personas)}体のペルソナを '{self.persona_file}' から読み込みました。")
                return personas
        except json.JSONDecodeError:
            print(f"エラー: {self.persona_file} のJSON形式が正しくありません。")
            return []
        except Exception as e:
            print(f"エラー: ペルソナの読み込み中に予期せぬエラーが発生: {e}")
            return []

    def get_all_personas(self):
        """全てのペルソナオブジェクトのリストを返す"""
        return self.all_personas

    def get_persona_by_id(self, persona_id):
        """IDを指定してペルソナオブジェクトを取得する"""
        return next((p for p in self.all_personas if p.id == persona_id), None)

    def get_active_personas(self):
        """現在アクティブなペルソナオブジェクトのリストを返す"""
        return list(self.active_personas.values())

    def set_active_personas(self, persona_ids):
        """IDのリストに基づいてアクティブなペルソナを設定する"""
        self.active_personas.clear()
        for pid in persona_ids:
            persona = self.get_persona_by_id(pid)
            if persona:
                self.active_personas[pid] = persona
