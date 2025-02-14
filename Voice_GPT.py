# This is just a small non-realtime solution using soundfiles to store mic inputs and gpt outpus
# use it if you're searching for a "blueprint"-projekt, as start to create your own ai-assistant
# pros: simple and easy to use
# const: not realtime, always require an key-word to proceed

from __future__ import annotations

import base64
import wave
from collections.abc import Iterable

import pyaudio
import speech_recognition as sr
from openai import OpenAI

from credentials import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

# initialize the text-to-speech engine
LANGUAGE = "de-DE"
FORMAT = pyaudio.paInt16
CHANNELS = 1
CHUNK = 512


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
        messages=[
            {
                "role": "system",
                "content": "Du bist ein Schauspieler und spielst die Rolle einer ständig genervten und gehässigen Person, die zudem noch passiv aggressiv ist und sehr ironisch zu gleich. Außerdem sollst du mich manchmal auf den arm nehmen.",
            },
            {"role": "user", "content": prompt},
        ],
        max_completion_tokens=4000,
        n=1,
        temperature=0.5,
    )
    return audio_completion.choices[0].message.audio.data


def play_wav(file_path: str):
    player = pyaudio.PyAudio()

    with wave.open(file_path, "rb") as wf:
        stream = player.open(
            format=player.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True,
        )

        # Read the first chunk of data
        data = wf.readframes(CHUNK)

        # Play the audio
        while data:
            stream.write(data)
            data = wf.readframes(CHUNK)

        stream.stop_stream()
        stream.close()

    player.terminate()  # Ensure PyAudio is properly closed


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
                    own_recorded_audio_file = "/audio/own_recorded_audio.wav"
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
                        gpt_response_audio_file = "/audio/gpt-response_audio.wav"
                        with open(gpt_response_audio_file, "wb") as f:
                            f.write(wav_bytes)

                        # Print audio response as text
                        print("transcribe audio to text...")
                        text_response = transcribe_audio_to_text(
                            gpt_response_audio_file
                        )
                        print(f"GPT says: {text_response}")

                        # Play the WAV file
                        play_wav(gpt_response_audio_file)
            except sr.WaitTimeoutError:
                print("Listening timed out. Restarting...")
            except Exception as e:
                print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
