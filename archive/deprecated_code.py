import numpy as np
from faster_whisper import WhisperModel

model = WhisperModel(
    "medium",
    device="cpu",
    compute_type="float32",
    num_workers=16,
)


# Deprecated function: Faster-Whisper transcription (not currently used)
def transcribe_audio_to_text(mic_chunk: any) -> str:
    """Transcribes audio chunks in real-time using faster_whisper."""
    try:
        audio_data = bytearray()
        audio_data.extend(mic_chunk)  # Append directly

        # Convert in-ram buffer to something the model can use directly without needing a temp audio file.
        # Convert data from 16 bit wide integers to floating point with a width of 32 bits.
        # Clamp the audio stream frequency to a PCM wavelength compatible default of 32768hz max.
        audio_np = (
            np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        )

        # Perform transcription using the Whisper model
        segments, _ = model.transcribe(audio_np, language="de", beam_size=10)

        # Extract and return the transcribed text
        transcribed_text = " ".join([segment.text for segment in segments])

        return transcribed_text.strip()
    except Exception as e:
        print(f"Error in transcription: {e}")
        return ""
