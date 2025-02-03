import base64
import json
import queue
import socket
import threading
import time

import pyaudio
import socks
import websocket

from credentials import OPENAI_API_KEY

socket.socket = socks.socksocket

WS_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"

CHUNK_SIZE = 1024
RATE = 24000
FORMAT = pyaudio.paInt16

audio_buffer = bytearray()
mic_queue = queue.Queue()

stop_event = threading.Event()

mic_on_at = 0
mic_active = None
REENGAGE_DELAY_MS = 500


def clear_audio_buffer():
    global audio_buffer
    audio_buffer = bytearray()


def stop_audio_playback():
    global is_playing
    is_playing = False


def mic_callback(in_data, frame_count, time_info, status):
    """Handle microphone input and put it into a queue"""
    global mic_on_at, mic_active

    if mic_active:
        print("🎙️🟢 Mic active")
        mic_active = True
    mic_queue.put(in_data)

    return (None, pyaudio.paContinue)


def send_mic_audio_to_websocket(ws):
    """Send microphone audio data to the WebSocket"""
    try:
        while not stop_event.is_set():
            if not mic_queue.empty():
                mic_chunk = mic_queue.get()
                encoded_chunk = base64.b64encode(mic_chunk).decode("utf-8")
                message = json.dumps(
                    {"type": "input_audio_buffer.append", "audio": encoded_chunk}
                )
                try:
                    ws.send(message)
                except Exception as e:
                    print(f"Error sending mic audio: {e}")
    except Exception as e:
        print(f"Exception in send_mic_audio_to_websocket thread: {e}")
    finally:
        print("Exiting send_mic_audio_to_websocket thread.")


def speaker_callback(in_data, frame_count, time_info, status):
    """Handle audio playback callback"""
    global audio_buffer, mic_on_at

    bytes_needed = frame_count * 2
    current_buffer_size = len(audio_buffer)

    if current_buffer_size >= bytes_needed:
        audio_chunk = bytes(audio_buffer[:bytes_needed])
        audio_buffer = audio_buffer[bytes_needed:]
        mic_on_at = time.time() + REENGAGE_DELAY_MS / 1000
    else:
        audio_chunk = bytes(audio_buffer) + b"\x00" * (
            bytes_needed - current_buffer_size
        )
        audio_buffer.clear()

    return (audio_chunk, pyaudio.paContinue)


def receive_audio_from_websocket(ws):
    """Receive audio data from the WebSocket and process events"""
    global audio_buffer

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
                    print("🤖 AI speaking:")

                elif event_type == "response.output_item.done":
                    output_item = message["item"]
                    transcript = output_item["content"][0]["transcript"]
                    print(transcript)  # print answer

                elif event_type == "response.audio.delta":
                    audio_content = base64.b64decode(message["delta"])
                    audio_buffer.extend(audio_content)

                elif event_type == "input_audio_buffer.speech_started":
                    print("🤠 ME speaking.")
                    clear_audio_buffer()
                    stop_audio_playback()

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
                "Du bist ein Schauspieler und spielst die Rolle einer ständig genervten und gehässigen Person,"
                "die zudem noch passiv aggressiv ist und sehr ironisch zu gleich."
                "Außerdem sollst du mich manchmal auf den arm nehmen."
            ),
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500,
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

        mic_thread = threading.Thread(target=send_mic_audio_to_websocket, args=(ws,))
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
    p = pyaudio.PyAudio()

    mic_stream = p.open(
        format=FORMAT,
        channels=1,
        rate=RATE,
        input=True,
        stream_callback=mic_callback,
        frames_per_buffer=CHUNK_SIZE,
    )

    speaker_stream = p.open(
        format=FORMAT,
        channels=1,
        rate=RATE,
        output=True,
        stream_callback=speaker_callback,
        frames_per_buffer=CHUNK_SIZE,
    )

    try:
        mic_stream.start_stream()
        speaker_stream.start_stream()

        connect_to_openai()

        while mic_stream.is_active() and speaker_stream.is_active():
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Gracefully shutting down...")
        stop_event.set()

    finally:
        mic_stream.stop_stream()
        mic_stream.close()
        speaker_stream.stop_stream()
        speaker_stream.close()

        p.terminate()
        print("Audio streams stopped and resources released. Exiting.")


if __name__ == "__main__":
    main()
