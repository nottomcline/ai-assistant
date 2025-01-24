from __future__ import annotations

from collections.abc import Iterable
from typing import list

import openai
import pyttsx3
import speech_recognition as sr

from .credentials import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

# initialize the text-to-speech engine
engine = pyttsx3.init()


def transcribe_audio_to_text(filename: str) -> str:
    recognizer = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_bing(audio)
    except Exception as e:
        print(f"An error occurred: {e}")


def generate_response(
    prompt: str | list[str] | Iterable[int] | Iterable[Iterable[int]],
) -> str:
    response = openai.completions.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=4000,
        n=1,
        stop=None,
        temperature=0.5,
    )
    return response["choices"][0]["text"]


def speak_text(text: str):
    engine.say(text)
    engine.runAndWait()


def main():
    while True:
        # Wait for user ut say "tom"
        print("say 'Hey Tom' to start recording your question...")
        with sr.Microphone() as source:
            recognizer = sr.Recognizer()
            audio = recognizer.listen(source)
            try:
                transcription = recognizer.recognize_bing(audio)
                if transcription.lower() == "hey tom":
                    # Record audio
                    filename = "input.wav"
                    print("Say your quiestion...")
                    with sr.Microphone() as source:
                        recognizer = sr.Recognizer()
                        source.pause_threshold = 1
                        audio = recognizer.listen(
                            source, phrase_time_limit=None, timeout=None
                        )
                        with open(filename, "wb") as f:
                            f.write(audio.get_wav_data())

                    # Transcribe audio to text
                    text = transcribe_audio_to_text(filename)
                    if text:
                        print(f"you said: {text}")

                        # Generate response using GPT
                        response = generate_response(text)
                        print(f"GPT says: {response}")

                        # Read response using text-to-speech
                        speak_text(response)
            except Exception as e:
                print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
