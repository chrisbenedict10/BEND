"""
Module 1: Speech-to-Text (STT)
Captures audio from the laptop microphone and transcribes it to text
using Google's free Speech Recognition API.

Supports "hold Enter to speak" mode — records while Enter is held down.
"""

import io
import threading
import keyboard
import speech_recognition as sr
import pyaudio
import wave
import config


# Audio recording settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000


def listen_hold_to_talk(key="enter"):
    """
    Record audio while the specified key is held down (hold-to-talk).

    Args:
        key: The key to hold while speaking (default: 'enter').

    Returns:
        str: The transcribed text, or None if nothing was understood.
    """
    p = pyaudio.PyAudio()

    print(f"\n🎤 Hold [{key.upper()}] and speak... (release to stop)")

    # Wait for key press
    keyboard.wait(key, suppress=True)

    # Start recording
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                    input=True, frames_per_buffer=CHUNK)

    frames = []
    print("🔴 Recording...")

    # Record while key is held down
    while keyboard.is_pressed(key):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

    print("⏹️  Stopped recording.")

    # Stop and clean up the stream
    stream.stop_stream()
    stream.close()
    p.terminate()

    if not frames:
        print("⚠️  No audio captured.")
        return None

    # Convert raw frames to a WAV byte stream for SpeechRecognition
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT) if hasattr(p, 'get_sample_size') else 2)
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))
    wav_buffer.seek(0)

    # Transcribe
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_buffer) as source:
        audio = recognizer.record(source)

    print("⏳ Transcribing...")

    try:
        text = recognizer.recognize_google(audio)
        print(f'📝 You said: "{text}"')
        return text
    except sr.UnknownValueError:
        print("❓ Sorry, I couldn't understand that.")
        return None
    except sr.RequestError as e:
        print(f"❌ STT API error: {e}")
        return None

def listen_continuously(wake_phrase=config.WAKE_PHRASE):
    """
    Continuously listens in the background. If the wake phrase is heard, it checks if 
    the user spoke a command immediately after (in the same breath).
    
    Returns:
        str: The command spoken after the wake word.
        True: If ONLY the wake word was spoken (requesting a prompt).
    """
    recognizer = sr.Recognizer()
    # Increase sensitivity: lower energy threshold means it triggers on quieter sounds
    recognizer.energy_threshold = 250 
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 1.5 # Wait a bit longer for the user to speak/finish

    # Broad phonetic aliases for "Bend" to ensure the trigger is reliable
    wake_aliases = [
        wake_phrase.lower(), "hey bend", "hey ben", "hey band", "hey beng",
        "hi bend", "hi ben", "bend", "ben", "beng", "band"
    ]

    print(f"\n🎧 Listening for wake word: '{wake_phrase}'...")

    with sr.Microphone() as source:
        # Standard noise adjustment
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
        
        while True:
            try:
                # Standard phrase limit (10s)
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=10)
                
                try:
                    text_all = recognizer.recognize_google(audio)
                    text_lower = text_all.lower()
                    
                    # Check if the wake word OR any of its phonetic aliases were heard
                    detected_alias = next((alias for alias in wake_aliases if alias in text_lower), None)
                    
                    if detected_alias:
                        print(f"✨ Wake word detection triggered via: '{detected_alias}'")
                        
                        # Extract everything said AFTER the detected alias
                        parts = text_lower.split(detected_alias, 1)
                        if len(parts) > 1 and parts[1].strip():
                            command = parts[1].strip()
                            # Clean up leading punctuation
                            command = command.lstrip(",.?! ")
                            print(f'📝 Inline command detected: "{command}"')
                            return command 
                        else:
                            return True # Just the wake word detected
                        
                except sr.UnknownValueError:
                    # Optional: print something to show it heard *something* but couldn't parse it
                    # print("DEBUG: Heard noise but no speech.")
                    pass
                except sr.RequestError:
                    print("❌ STT API Error during continuous detection.")
                    
            except sr.WaitTimeoutError:
                pass

def listen(timeout=5, phrase_time_limit=10):
    """
    Listen to the microphone and return the transcribed text (auto-detect mode).
    """
    recognizer = sr.Recognizer()
    # Increase sensitivity: lower energy threshold means it triggers on quieter sounds
    recognizer.energy_threshold = 250
    recognizer.dynamic_energy_threshold = True
    # More patient pause threshold (1.5s) instead of the standard 0.8s
    recognizer.pause_threshold = 1.5

    with sr.Microphone() as source:
        print(f"🎤 Listening...")
        # Ambient noise adjustment
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
        print(f"DEBUG: Initial Energy Threshold: {recognizer.energy_threshold}")

        try:
            # Increased timeouts for more reliability
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            print("⏳ Transcribing...")
        except sr.WaitTimeoutError:
            print("⏰ No speech detected (timed out).")
            return None

    try:
        text = recognizer.recognize_google(audio)
        print(f'📝 You said: "{text}"')
        return text
    except sr.UnknownValueError:
        print("❓ Sorry, I couldn't understand that.")
        return None
    except sr.RequestError as e:
        print(f"❌ STT API error: {e}")
        return None


if __name__ == "__main__":
    print("=== STT Hold-to-Talk Test ===")
    result = listen_hold_to_talk()
    if result:
        print(f'\n✅ Successfully transcribed: "{result}"')
    else:
        print("\n❌ No transcription result.")
