import base64
import io
import json
import os
import queue
import random
import re
import socket
import threading
import time
import wave

import pyaudio
import socks
import speech_recognition as sr
import websocket
from credentials import OPENAI_API_KEY
from openai import OpenAI

socket.socket = socks.socksocket

WS_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
CHUNK_SIZE = 4096
AI_NAME = "jerry"
REENGAGE_DELAY_MS = 500
# set constants based on openAI's requirements
# see input_audio_format -> https://platform.openai.com/docs/api-reference/realtime-sessions/create
FORMAT = pyaudio.paInt16
RATE = 24000  # 24kHz
CHANNELS = 1  # mono
BYTES_PER_SAMPLE = 2  # 16-bit PCM: 2 bytes per sample
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


client = OpenAI(api_key=OPENAI_API_KEY)
gpt_audio_buffer = bytearray()
mic_queue = queue.Queue()
mic_on_at = 0
stop_event = threading.Event()
recorder = sr.Recognizer()
recorder.energy_threshold = 1000
# dynamic energy compensation, lowers the energy threshold to a point where SpeechRecognizer never stops recording
recorder.dynamic_energy_threshold = False


def recorder_callback(_, audio: sr.AudioData) -> None:
    """
    Threaded callback function to receive audio data when recordings finish.
    audio: An AudioData containing the recorded bytes.
    """
    # Grab the raw bytes and push it into the thread safe queue.
    wave_data = audio.get_wav_data(convert_rate=RATE, convert_width=BYTES_PER_SAMPLE)
    mic_queue.put(wave_data)


def clear_audio_buffer():
    global gpt_audio_buffer
    gpt_audio_buffer = bytearray()


def stop_audio_playback():
    global is_playing
    is_playing = False


def should_ai_respond(user_text: str) -> bool:
    """Determines if AI should respond based on input type and probability."""

    question_words = {
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

    indirect_question_words = {
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

    subjunctive_words = {
        "wäre",
        "hätte",
        "würde",
        "sei",
        "habe",
    }

    uncertainty_phrases = [
        "ich bin mir nicht sicher",
        "ich weiß nicht",
        "ich frage mich",
        "ist das wahr",
        "ist es möglich",
        "glaubst du",
        "was wäre wenn",
    ]

    user_text_lower = user_text.lower()
    words = user_text_lower.split()
    answer_chance = random.random()

    is_question = (
        any(word in question_words for word in words)
        or any(word in indirect_question_words for word in words)
        or any(word in subjunctive_words for word in words)
        or any(phrase in user_text_lower for phrase in uncertainty_phrases)
        or user_text.strip().endswith("?")
    )

    if AI_NAME in words:
        return True  # 100% chance to respond
    elif is_question:
        return answer_chance < 0.9  # 90% chance to respond to questions
    else:
        return answer_chance < 0.5  # 50% chance to respond to statements


def stop_talking(transcribed_text: str):
    interruption_phrases = ["halts maul", "sei still", "hör auf", "leck ei"]

    # Remove punctuation from the transcribed text
    transcribed_text_clean = re.sub(r"[^\w\s]", "", transcribed_text.lower())
    words = transcribed_text_clean.split()
    return "stopp" in words or any(
        phrase in transcribed_text_clean for phrase in interruption_phrases
    )


def send_transcription_to_websocket(ws, user_text: str):
    create_conversation = json.dumps(
        {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": user_text}],
            },
        }
    )
    try:
        ws.send(create_conversation)  # initiate conversation
        create_response = json.dumps(
            {
                "type": "response.create",
                "response": {
                    "output_audio_format": "pcm16",
                },
            }
        )
        try:
            ws.send(create_response)  # request a response
        except Exception as e:
            print(f"Error sending mic audio in send_transcription_to_websocket: {e}")
    except Exception as e:
        print(f"Error sending mic audio in send_transcription_to_websocket: {e}")


def transcribe_and_send_to_websocket(ws):
    """Send microphone audio data to the WebSocket"""
    user_audio_buffer = io.BytesIO()
    own_recorded_audio_file = os.path.join(BASE_DIR, "audio", "own_recorded_audio.wav")
    processing_mic_audio = False
    try:
        while not stop_event.is_set():
            user_text: str = ""
            while not mic_queue.empty():
                mic_chunk = mic_queue.get()
                user_audio_buffer.write(mic_chunk)
                processing_mic_audio = True

            if processing_mic_audio:
                # Save buffer to WAV file with correct headers
                with wave.open(own_recorded_audio_file, "wb") as f:
                    f.setnchannels(1)  # Mono
                    f.setsampwidth(BYTES_PER_SAMPLE)  # 16-bit PCM
                    f.setframerate(RATE)  # 24kHz sample rate
                    f.writeframes(user_audio_buffer.getvalue())

                with open(own_recorded_audio_file, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1", file=audio_file
                    )

                user_text += f"{transcription.text} "
                processing_mic_audio = False
                user_audio_buffer = io.BytesIO()
                if stop_talking(transcription.text):
                    # Reset the buffer for the next utterance
                    chance_to_deny = random.random()
                    if chance_to_deny < 0.5:
                        user_text = ""
                    else:
                        user_text = "Antworte mit 'Nein mach ich nicht' und knüpfe an deiner letzten Aussage an."
                    break

                # only send data if AI isn't talking anymore
                if user_text and mic_queue.empty():
                    print(f"\n🤠 ME speaking:\n{user_text}")

                    send_transcription_to_websocket(ws, user_text)

    except Exception as e:
        print(f"Exception in transcribe_and_send_to_websocket thread: {e}")
    finally:
        print("Exiting transcribe_and_send_to_websocket thread.")


def speaker_callback(in_data, frame_count, time_info, status):
    """Handle audio playback callback"""
    global gpt_audio_buffer, mic_on_at

    bytes_needed = frame_count * 2
    current_buffer_size = len(gpt_audio_buffer)

    if current_buffer_size >= bytes_needed:
        audio_chunk = bytes(gpt_audio_buffer[:bytes_needed])
        gpt_audio_buffer = gpt_audio_buffer[bytes_needed:]
        mic_on_at = time.time() + REENGAGE_DELAY_MS / 1000
    else:
        audio_chunk = bytes(gpt_audio_buffer) + b"\x00" * (
            bytes_needed - current_buffer_size
        )
        gpt_audio_buffer.clear()

    return (audio_chunk, pyaudio.paContinue)


def receive_audio_from_websocket(ws):
    """Receive audio data from the WebSocket and process events"""
    global gpt_audio_buffer

    try:
        while not stop_event.is_set():
            try:
                message = ws.recv()
                if not message:  # Handle empty message (EOF or connection close)
                    print("Received empty message (possibly EOF or WebSocket closing).")
                    break

                message = json.loads(message)
                event_type = message["type"]

                if event_type == "session.created":
                    send_fc_session_update(ws)

                elif event_type == "response.created":
                    print("\n🤖 AI speaking:")

                elif event_type == "response.audio_transcript.delta":
                    print(message["delta"], end="", flush=True)  # Print progressively

                elif event_type == "response.audio.delta":
                    audio_content = base64.b64decode(message["delta"])
                    gpt_audio_buffer.extend(audio_content)

                elif event_type == "response.audio_transcript.done":
                    print()  # Print newline when final transcript is received

                # for debugging
                # elif event_type == "response.done":
                #     print(message["response"]["status"])
                #     print(message["response"]["status_details"]["type"])
                #     print(message["response"]["status_details"]["reason"])

            except Exception as e:
                print(f"Error receiving audio: {e}")
    except Exception as e:
        print(f"Exception in receive_audio_from_websocket thread: {e}")
    finally:
        print("Exiting receive_audio_from_websocket thread.")


def send_fc_session_update(ws):
    session_config = {
        "type": "session.update",
        "session": {
            "instructions": (
                f"Du heißt {AI_NAME} und bist ein Schauspieler, der die Rolle einer ständig genervten und gehässigen Person spielt,"
                "die zudem noch passiv aggressiv ist und sehr ironisch zu gleich."
                "Außerdem sollst du:"
                "- manchmal nur das nötigste antworten."
                "- mir niemals wiedersprechen."
                "- mir manchmal auffällig ausgedachte Antworten geben."
                "- mich manchmal auf den arm nehmen."
            ),
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500,
                "create_response": True,
            },
            "voice": "ballad",
            "temperature": 1,
            "max_response_output_tokens": 4096,
            "modalities": ["text", "audio"],
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {"model": "whisper-1"},
            "tool_choice": "auto",
            "tools": [],
        },
    }
    # Send the JSON configuration through the WebSocket
    try:
        session_config_json = json.dumps(session_config)
        ws.send(session_config_json)
    except Exception as e:
        print(f"Failed to send session update: {e}")


def create_connection_with_ipv4(*args, **kwargs):
    # Enforce the use of IPv4
    original_getaddrinfo = socket.getaddrinfo

    def getaddrinfo_ipv4(host, port, family=socket.AF_INET, *args):
        return original_getaddrinfo(host, port, socket.AF_INET, *args)

    socket.getaddrinfo = getaddrinfo_ipv4
    try:
        return websocket.create_connection(*args, **kwargs)
    finally:
        # Restore the original getaddrinfo method after the connection
        socket.getaddrinfo = original_getaddrinfo


def connect_to_openai():
    ws = None
    try:
        ws = create_connection_with_ipv4(
            WS_URL,
            header=[
                f"Authorization: Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta: realtime=v1",
            ],
        )
        print("Connected to OpenAI WebSocket.")

        # Start the recv and send threads
        receive_thread = threading.Thread(
            target=receive_audio_from_websocket, args=(ws,)
        )
        receive_thread.start()

        mic_thread = threading.Thread(
            target=transcribe_and_send_to_websocket, args=(ws,)
        )
        mic_thread.start()

        # Wait for stop_event to be set
        while not stop_event.is_set():
            time.sleep(0.1)

        # Send a close frame and close the WebSocket gracefully
        print("Sending WebSocket close frame.")
        ws.send_close()

        receive_thread.join()
        mic_thread.join()

        print("WebSocket closed and threads terminated.")
    except Exception as e:
        print(f"Failed to connect to OpenAI: {e}")
    finally:
        if ws is not None:
            try:
                ws.close()
                print("WebSocket connection closed.")
            except Exception as e:
                print(f"Error closing WebSocket connection: {e}")


def main():
    player = pyaudio.PyAudio()
    source = sr.Microphone(sample_rate=RATE)
    with source:
        recorder.adjust_for_ambient_noise(source)

    speaker_stream = player.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        output=True,
        stream_callback=speaker_callback,
        frames_per_buffer=CHUNK_SIZE,
    )

    try:
        listener_thread = recorder.listen_in_background(source, recorder_callback)
        speaker_stream.start_stream()

        connect_to_openai()

        while recorder.is_active() and speaker_stream.is_active():
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Gracefully shutting down...")
        stop_event.set()

    finally:
        listener_thread(wait_for_stop=True)
        speaker_stream.stop_stream()
        speaker_stream.close()

        player.terminate()
        print("Audio streams stopped and resources released. Exiting.")


if __name__ == "__main__":
    main()
