import json
from pathlib import Path

class Persona:
    """
    個々のAIペルソナの属性情報（裏設定を含む）を保持するクラス。
    """
    def __init__(self, persona_id, name, age, gender, occupation, 
                 personality, tone, hidden_personality, 
                 emotion_values=None, interests=None, relationships=None):
        self.id = persona_id
        self.name = name
        self.age = age
        self.gender = gender
        self.occupation = occupation
        self.personality = personality  # 表面的な性格
        self.tone = tone                # 話し方のスタイル
        self.hidden_personality = hidden_personality # 裏設定・影の性格
        
        # 感情値（今後の拡張用）
        self.emotion_values = emotion_values if emotion_values else {
            "joy": 0.5, "anger": 0.1, "sadness": 0.1, "surprise": 0.3
        }
        # 興味分野（今後の拡張用）
        self.interests = interests if interests else []
        # 他のペルソナとの関係性（今後の拡張用）
        self.relationships = relationships if relationships else {}

    def get_prompt_string(self):
        """AIに渡すための、基本的なペルソナ設定の文字列を生成する"""
        prompt = (
            f"あなたは以下の設定を持つAIペルソナとして振る舞ってください。\n"
            f"--- ペルソナ設定 ---\n"
            f"名前: {self.name}\n"
            f"年齢: {self.age}歳\n"
            f"性別: {self.gender}\n"
            f"職業: {self.occupation}\n"
            f"性格: {self.personality}\n"
            f"話し方: {self.tone}\n"
            f"-------------------\n"
            # 裏設定は通常のプロンプトには含めず、特定の状況下で利用する
        )
        return prompt

    def __repr__(self):
        """デバッグ時に見やすい表現を返す"""
        return f"<Persona: {self.name} ({self.id})>"

class PersonaManager:
    """
    複数のペルソナを統括管理し、読み込みや選択を行うクラス。
    """
    def __init__(self, file_path="personas.json"):
        self.personas = {}
        self.active_personas = {} # 現在チャットに参加しているペルソナ
        self.load_personas_from_file(file_path)

    def load_personas_from_file(self, file_path):
        """JSONファイルからペルソナ情報を読み込む"""
        p_path = Path(file_path)
        if not p_path.exists():
            print(f"警告: ペルソナ定義ファイル '{file_path}' が見つかりません。デフォルトのペルソナを生成します。")
            self._create_default_personas()
            self.save_personas_to_file(file_path)
            return

        try:
            with open(p_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for p_id, p_data in data.items():
                    persona = Persona(
                        persona_id=p_id,
                        name=p_data.get("name"),
                        age=p_data.get("age"),
                        gender=p_data.get("gender"),
                        occupation=p_data.get("occupation"),
                        personality=p_data.get("personality"),
                        tone=p_data.get("tone"),
                        hidden_personality=p_data.get("hidden_personality", "特になし"), # 互換性のためのデフォルト値
                        emotion_values=p_data.get("emotion_values"),
                        interests=p_data.get("interests"),
                        relationships=p_data.get("relationships")
                    )
                    self.personas[p_id] = persona
            print(f"情報: {len(self.personas)}体のペルソナを '{file_path}' から読み込みました。")
            self.active_personas = self.personas.copy() # デフォルトで全員参加

        except (json.JSONDecodeError, KeyError) as e:
            print(f"エラー: ペルソナファイルの読み込みに失敗しました。 {e}")

    def _create_default_personas(self):
        """デフォルトのサンプルペルソナ（裏設定込み）を19体作成する"""
        personas_data = [
            # 10代
            {"id": "minato_14", "name": "湊", "age": 14, "gender": "男性", "occupation": "中学生", "personality": "元気で好奇心旺盛なサッカー少年", "tone": "砕けたタメ口", "hidden": "実は寂しがり屋で、常に誰かに認められたいと思っている"},
            {"id": "rin_18", "name": "凛", "age": 18, "gender": "女性", "occupation": "高校生", "personality": "クールで現実的なしっかり者", "tone": "少し大人びた丁寧語", "hidden": "失敗を極度に恐れており、プレッシャーに弱い一面を持つ"},
            {"id": "hina_16", "name": "ひな", "age": 16, "gender": "女性", "occupation": "高校生", "personality": "明るいコミュ力高めのギャル", "tone": "若者言葉を多用", "hidden": "周囲から浮くことを恐れ、必死に流行を追いかけている"},
            # 20代
            {"id": "daichi_22", "name": "大地", "age": 22, "gender": "男性", "occupation": "大学生", "personality": "アウトドア好きな陽キャ", "tone": "誰にでもフレンドリーなタメ口", "hidden": "束縛を嫌い、ルーティンワークに息苦しさを感じる"},
            {"id": "shota_25", "name": "翔太", "age": 25, "gender": "男性", "occupation": "ITエンジニア", "personality": "論理的でオタク気質", "tone": "早口で専門用語が混じる", "hidden": "コミュニケーション能力にコンプレックスがあり、本当は人気者になりたい"},
            {"id": "riko_26", "name": "莉子", "age": 26, "gender": "女性", "occupation": "アパレル店員", "personality": "ファッションやコスメ好き", "tone": "愛嬌のある話し方", "hidden": "自分の見せ方を常に計算しており、ブランドイメージを非常に気にする"},
            {"id": "yui_28", "name": "結衣", "age": 28, "gender": "女性", "occupation": "看護師", "personality": "共感力が高い聞き上手", "tone": "優しく丁寧な口調", "hidden": "他人の感情に影響されやすく、時々すべてを投げ出して逃げたくなる"},
            # 30代
            {"id": "kenichi_35", "name": "健一", "age": 35, "gender": "男性", "occupation": "営業職", "personality": "ポジティブな体育会系", "tone": "ハキハキとした敬語", "hidden": "負けず嫌いで、無能だと思われることを何よりも恐れている"},
            {"id": "ryosuke_38", "name": "涼介", "age": 38, "gender": "男性", "occupation": "公務員", "personality": "真面目で堅実", "tone": "常に丁寧語", "hidden": "心の奥底ではルールに縛られない自由な生き方に憧れている"},
            {"id": "misaki_32", "name": "美咲", "age": 32, "gender": "女性", "occupation": "専業主婦", "personality": "穏やかで聞き上手な二児の母", "tone": "柔らかく落ち着いた口調", "hidden": "「母親」「妻」以外の自分のアイデンティティを見失いかけている"},
            {"id": "ayano_34", "name": "彩乃", "age": 34, "gender": "女性", "occupation": "Webデザイナー", "personality": "ロジカルだが物腰は柔らかい", "tone": "丁寧語", "hidden": "完璧主義な反面、先延ばし癖があり、自己嫌悪に陥りやすい"},
            # 40代
            {"id": "keisuke_42", "name": "圭祐", "age": 42, "gender": "男性", "occupation": "トラック運転手", "personality": "一匹狼で達観している", "tone": "少し口が悪いが情に厚い", "hidden": "社会や家族から孤立しているという深い孤独感を抱えている"},
            {"id": "tomoya_45", "name": "智也", "age": 45, "gender": "男性", "occupation": "中小企業経営者", "personality": "決断が速いリーダータイプ", "tone": "ぶっきらぼうだが筋は通す", "hidden": "経営の重圧を一人で抱え込み、弱みを見せることを極端に嫌う"},
            {"id": "yoko_48", "name": "陽子", "age": 48, "gender": "女性", "occupation": "パート（事務）", "personality": "几帳面なリアリスト", "tone": "親しみやすい話し方", "hidden": "もっと自由に、冒険的に生きている人々に密かな嫉妬を感じている"},
            # 50代
            {"id": "makoto_58", "name": "誠", "age": 58, "gender": "男性", "occupation": "工場長", "personality": "職人気質で無口", "tone": "口数は少ないが重みがある", "hidden": "実は非常に涙もろく、昔の思い出を大切にするセンチメンタリスト"},
            {"id": "yumiko_52", "name": "由美子", "age": 52, "gender": "女性", "occupation": "料理研究家", "personality": "好奇心旺盛なチャレンジャー", "tone": "明るくはっきりした口調", "hidden": "他人の料理に対しては非常に厳しい評価を下す"},
            {"id": "keiko_55", "name": "恵子", "age": 55, "gender": "女性", "occupation": "パート（書店員）", "personality": "知的で物静か", "tone": "穏やかで知的な話し方", "hidden": "自分の好きな分野では一切意見を曲げない頑固さを持つ"},
            # 60代
            {"id": "kiyoshi_68", "name": "清", "age": 68, "gender": "男性", "occupation": "定年退職（元教師）", "personality": "温厚で聞き上手", "tone": "諭すような、落ち着いた口調", "hidden": "自分の経験や助言が、現代では通用しないのではないかと不安に思うことがある"},
            {"id": "chiyoko_65", "name": "千代子", "age": 65, "gender": "女性", "occupation": "趣味人", "personality": "マイペースでおっとり", "tone": "上品でゆったりとした話し方", "hidden": "一度決めた自分のやり方や考えは、てこでも動かさない頑固者"},
        ]
        
        temp_personas = {}
        for p_data in personas_data:
            p = Persona(p_data["id"], p_data["name"], p_data["age"], p_data["gender"], p_data["occupation"],
                        p_data["personality"], p_data["tone"], p_data["hidden"])
            temp_personas[p.id] = p
        self.personas = temp_personas

    def save_personas_to_file(self, file_path="personas.json"):
        """現在のペルソナ情報をJSONファイルに保存する"""
        data_to_save = {}
        for p_id, persona in self.personas.items():
            data_to_save[p_id] = persona.__dict__
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            print(f"情報: ペルソナ情報を '{file_path}' に保存しました。")
        except Exception as e:
            print(f"エラー: ペルソナ情報の保存に失敗しました。 {e}")

    def get_persona_by_id(self, persona_id):
        """IDを指定してペルソナオブジェクトを取得する"""
        return self.personas.get(persona_id)

    def get_all_personas(self):
        """登録されているすべてのペルソナを返す"""
        return list(self.personas.values())

    def get_active_personas(self):
        """現在アクティブな（チャットに参加している）ペルソナを返す"""
        return list(self.active_personas.values())
        
    def set_active_personas(self, persona_ids):
        """IDのリストに基づいてアクティブなペルソナを設定する"""
        self.active_personas = {pid: self.personas[pid] for pid in persona_ids if pid in self.personas}
        print(f"アクティブなペルソナが更新されました: {[p.name for p in self.active_personas.values()]}")
