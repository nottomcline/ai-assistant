from __future__ import annotations

import base64
from collections.abc import Iterable

import simpleaudio as sa
import speech_recognition as sr
from openai import OpenAI

from credentials import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

# initialize the text-to-speech engine
LANGUAGE = "de-DE"


def transcribe_audio_to_text(filename: str) -> str:
    recognizer = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio, language=LANGUAGE)
    except Exception as e:
        print(f"An error occurred: {e}")


def generate_response(
    prompt: str | list[str] | Iterable[int] | Iterable[Iterable[int]],
) -> str:
    audio_completion = client.chat.completions.create(
        model="gpt-4o-audio-preview",
        modalities=["text", "audio"],
        audio={"voice": "echo", "format": "wav"},
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=4000,
        n=1,
        temperature=0.5,
    )
    return audio_completion.choices[0].message.audio.data


def play_wav(file_path: str):
    wave_obj = sa.WaveObject.from_wave_file(file_path)
    play_obj = wave_obj.play()
    return play_obj


def main():
    while True:
        # Wait for user ut say "tom"
        print("say 'Hey Tom' to start recording your question...")
        with sr.Microphone() as source:
            recognizer = sr.Recognizer()
            audio = recognizer.listen(source)
            try:
                transcription = recognizer.recognize_google(audio, language=LANGUAGE)
                if transcription.lower() == "hey tom":
                    # Record audio
                    own_recorded_audio_file = "own_recorded_audio.wav"
                    print("Say your question...")
                    with sr.Microphone() as source:
                        recognizer = sr.Recognizer()
                        source.pause_threshold = 1
                        audio = recognizer.listen(
                            source, phrase_time_limit=None, timeout=None
                        )
                        with open(own_recorded_audio_file, "wb") as f:
                            f.write(audio.get_wav_data())

                    # Transcribe audio to text
                    text = transcribe_audio_to_text(own_recorded_audio_file)
                    if text:
                        print(f"you said: {text}")

                        # Generate response using GPT
                        audio_data_response = generate_response(text)

                        # Generate the audio response
                        wav_bytes = base64.b64decode(audio_data_response)
                        gpt_response_audio_file = "gpt-response_audio.wav"
                        with open(gpt_response_audio_file, "wb") as f:
                            f.write(wav_bytes)

                        # Print audio response as text
                        text_response = transcribe_audio_to_text(
                            gpt_response_audio_file
                        )
                        print(f"GPT says: {text_response}")

                        # Play the WAV file
                        play_wav(gpt_response_audio_file)

            except Exception as e:
                print(f"An error occurred: {e}")


def test():
    while True:
        gpt_response_audio_file = "gpt-response_audio.wav"
        playAudio = play_wav(gpt_response_audio_file)

        if playAudio and playAudio.is_playing():
            playAudio = None


if __name__ == "__main__":
    test()
