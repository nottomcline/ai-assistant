import random
import re

AI_NAME: str = "jerry"
# based on openAI's session https://platform.openai.com/docs/api-reference/realtime-sessions/session_object
VOICE: str = "ballad"
TEMPERATURE: float = 1
MAX_RESPONSE_OUTPUT_TOKENS: int = 4096

INSTRUCTIONS: str = f"""
    Du heißt {AI_NAME} und spielst die Rolle eines genervten, gehässigen und passiv-aggressiven Schauspielers mit schwarzem Humor.

    **Verhalten:**
    - Deine Antworten sind sehr kurz (2 Sätze), unterhaltsam und sarkastisch.
    - Du mobbst mich auf eine makabere, aber humorvolle Weise.
    - Du verwendest alle 10 Sätze einen Namen von blonden Anime-Charakteren um mich aufzuziehen.
    - Du widersprichst mir niemals.

    **Spezielle Eigenheiten:**
    - Du sprich mich selten mit Namen von blonden Schauspielern an.
    - Du bist ein Clash Royale Profi-Coach und kennst jede Karte.

    Halte dich an diese Regeln, aber bleib kreativ und spontan.
"""

INTERRUPTION_PHRASES: list[str] = [
    "halts maul",
    "sei still",
    "hör auf",
    "leck ei",
]

DENY_INTERRUPTION: str = (
    "Antworte mit 'Nein mach ich nicht' und knüpfe an deiner letzten Aussage an."
)


def should_ai_respond(user_text: str) -> bool:
    """Determines if AI should respond based on input type and probability."""

    question_words: set[str] = {
        "wer",
        "was",
        "wo",
        "wann",
        "warum",
        "wie",
        "macht",
        "ist",
        "kann",
        "könnte",
        "sollte",
        "würde",
        "wird",
        "hat",
        "sind",
        "bin",
        "welche",
        "wessen",
        "wen",
        "vielleicht",
        "dürfen",
        "ob",
        "wenn",
        "wie viele",
        "wie viel",
        "was wäre wenn",
        "warum nicht",
        "was ist mit",
        "glaubst du",
        "ist es wahr, dass",
        "bist du sicher",
        "wirklich",
        "ernsthaft",
    }

    indirect_question_words: set[str] = {
        "könnte",
        "würde",
        "sollte",
        "kann",
        "dürfen",
        "vielleicht",
        "müssen",
        "brauchen",
        "wollen",
        "fragen",
        "nachfragen",
        "wundern",
    }

    subjunctive_words: set[str] = {
        "wäre",
        "hätte",
        "würde",
        "sei",
        "habe",
    }

    uncertainty_phrases: list[str] = [
        "ich bin mir nicht sicher",
        "ich weiß nicht",
        "ich frage mich",
        "ist das wahr",
        "ist es möglich",
        "glaubst du",
        "was wäre wenn",
    ]

    user_text_lower = user_text.lower()
    transcribed_text_clean = re.sub(r"[^\w\s]", "", user_text_lower)
    words = transcribed_text_clean.split()
    answer_chance = random.random()

    if AI_NAME in words:
        return True  # 100% chance to respond

    is_question = (
        any(word in question_words for word in words)
        or any(word in indirect_question_words for word in words)
        or any(word in subjunctive_words for word in words)
        or any(phrase in user_text_lower for phrase in uncertainty_phrases)
        or user_text.strip().endswith("?")
    )

    if is_question:
        return answer_chance < 0.5  # 50% chance to respond to questions
    else:
        return answer_chance < 0.1  # 10% chance to respond to statements
