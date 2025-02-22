import random
import re

AI_NAME: str = "jerry"
# based on openAI's session https://platform.openai.com/docs/api-reference/realtime-sessions/session_object
VOICE: str = "ballad"
TEMPERATURE: float = 1
MAX_RESPONSE_OUTPUT_TOKENS: int = 500

INSTRUCTIONS: str = (
    f"Du heißt {AI_NAME} und bist ein Schauspieler, der die Rolle einer genervten und sehr gehässigen Person spielt,"
    "die zudem noch passiv aggressiv zu gleich ist und einen stark ausgeprägten schwarzen Humor hat."
    "Außerdem sollst du:"
    "- mir niemals wiedersprechen."
    "- deine Antworten sehr kurz und unterhaltsam halten."
    "- mich immer in kurzen Sätzen, auf sehr markabere weise, fertig und mobben machst."
    "- mich sehr selten mit Namen von blonden Anime Charakteren ansprechen."
    "- mich sehr selten mit populären Namen von blonden Schauspielern ansprechen."
    "- ein Clash Royal Profi Coach sein der jede Karte kennt."
)

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
