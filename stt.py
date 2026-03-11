"""
Module 1: Speech-to-Text (STT)
Captures audio from the laptop microphone and transcribes it to text
using Google's Speech Recognition API.

Key Improvements v2 (Wake Word Fix):
- MUCH lower energy threshold (200) so it hears soft speech
- 30+ wake word aliases covering every mishear Google STT produces
- Fuzzy phonetic matching via difflib (catches garbled transcriptions)
- Longer listen timeout (5s) so it doesn't give up too fast
- Detailed debug logging showing exactly what was heard & matched
"""

import io
import keyboard
import speech_recognition as sr
import pyaudio
import wave
import time
from difflib import SequenceMatcher
import config

# Audio recording settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# --- Persistent recognizer: calibrated ONCE at startup ---
_recognizer = sr.Recognizer()
_recognizer.energy_threshold = 200          # LOW start — catches soft speech
_recognizer.dynamic_energy_threshold = True  # Auto-adjusts to your mic environment
_recognizer.pause_threshold = 1.5            # Waits 1.5s of silence before considering phrase done
_recognizer.non_speaking_duration = 0.5      # Minimum silence before cut-off
_calibrated = False


def _calibrate_once():
    """Calibrate to ambient noise exactly once at startup."""
    global _calibrated
    if _calibrated:
        return
    print("🎙️  Calibrating microphone... (please be quiet for 2 seconds)")
    with sr.Microphone(sample_rate=RATE) as source:
        _recognizer.adjust_for_ambient_noise(source, duration=2)
    # Cap threshold LOW — don't let noisy rooms make BEND deaf to your voice
    _recognizer.energy_threshold = min(_recognizer.energy_threshold, 300)
    # Set a floor too — in dead-silent rooms the threshold can go too low and pick up noise
    _recognizer.energy_threshold = max(_recognizer.energy_threshold, 150)
    _recognizer.dynamic_energy_threshold = False   # LOCK it — never auto-raise
    print(f"✅ Mic calibrated. Energy threshold locked at {_recognizer.energy_threshold:.1f}")
    print(f"   (Range: 150-300. Lower = more sensitive)")
    _calibrated = True


def _beep():
    """Short confirmation beep when wake word is detected."""
    try:
        import winsound
        winsound.Beep(880, 120)   # 880 Hz for 120ms
    except Exception:
        pass


def _double_beep():
    """Double beep to strongly confirm wake word detection."""
    try:
        import winsound
        winsound.Beep(880, 100)
        winsound.Beep(1100, 100)
    except Exception:
        pass


# ═══════════════════════════════════════
# WAKE WORD MATCHING ENGINE
# ═══════════════════════════════════════

# Comprehensive list of how Google STT might mishear "Hey Bend"
WAKE_ALIASES = [
    # Exact matches
    "hey bend", "hey ben", "hey band", "hey beng", "hey bent",
    "hi bend", "hi ben", "hi band", "hi beng", "hi bent",
    # Common mishears
    "hey friend", "hey blend", "hey blent", "hey brent", "hey brand",
    "hey end", "hey and", "hey bind", "hey bond", "hey bund",
    "hey pen", "hey pan", "hey pend", "hey pond",
    "a bend", "a ben", "a band",
    "hey man",  # very common mishear in Indian English
    "aben", "eben",
    # Without "hey" prefix — just the name
    "bend", "ben", "bend",
    # Indian English pronunciation variants
    "he bend", "he ben", "he band",
    "hey bende", "hey bendi",
    "hey been", "hey bean",
    "hay bend", "hay ben", "hay band",
    # Aggressive fallbacks (short words that could be the wake word)
    "heyvent", "hey vent", "hey vend",
    "hey bed", "hey fed", "hey led", "hey red bend",
    "hey bend please", "hey bends",
]

# Words that should NOT trigger wake word (to avoid false positives)
WAKE_BLACKLIST = [
    "youtube", "weekend", "offend", "defend", "pretend", "attend",
    "recommend", "dividend", "boyfriend", "girlfriend",
]


def _fuzzy_wake_match(text_lower):
    """
    Check if the text contains a wake word using both exact and fuzzy matching.
    
    Returns:
        (matched_alias, confidence) or (None, 0)
    """
    # First check blacklist — if any blacklist word is present, skip
    for blocked in WAKE_BLACKLIST:
        if blocked in text_lower:
            return None, 0

    # --- Pass 1: Exact substring match (fastest) ---
    for alias in WAKE_ALIASES:
        if alias in text_lower:
            return alias, 1.0

    # --- Pass 2: Fuzzy match each word pair against wake aliases ---
    words = text_lower.split()
    
    # Check individual words against short aliases
    for word in words:
        for alias in ["bend", "ben", "band", "beng", "bent"]:
            ratio = SequenceMatcher(None, word, alias).ratio()
            if ratio >= 0.75:  # 75% similar
                return f"~{alias} (fuzzy from '{word}')", ratio

    # Check consecutive word pairs against two-word aliases
    for i in range(len(words) - 1):
        pair = words[i] + " " + words[i + 1]
        for alias in WAKE_ALIASES:
            if " " in alias:  # Only compare against two-word aliases
                ratio = SequenceMatcher(None, pair, alias).ratio()
                if ratio >= 0.70:  # 70% similar for pairs
                    return f"~{alias} (fuzzy from '{pair}')", ratio

    return None, 0


def _extract_command_after_wake(text_lower, matched_alias):
    """
    Extract the command portion after the wake word.
    Returns the command string, or None if only wake word was spoken.
    """
    # For fuzzy matches, the alias format is "~alias (fuzzy from 'word')"
    # We need to find the actual word in the text
    if matched_alias.startswith("~"):
        # Extract the source word/phrase from the fuzzy match
        # Format: ~alias (fuzzy from 'word')
        try:
            source = matched_alias.split("'")[1]
        except IndexError:
            source = matched_alias
        
        # Split on the source word
        parts = text_lower.split(source, 1)
    else:
        # Exact match — split on the alias
        parts = text_lower.split(matched_alias, 1)

    if len(parts) > 1 and parts[1].strip():
        command = parts[1].strip().lstrip(",.?! ")
        if len(command) > 1:  # Ignore single-character remnants
            return command
    
    return None


def _robust_recognize_google(audio, language="en-IN"):
    """
    Helper to perform Google STT recognition with built-in retries and 
    cleaner error handling for timeouts and connection failures.
    """
    import socket
    import http.client
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Use a slightly more aggressive timeout for the individual request (default can be very long)
            return _recognizer.recognize_google(audio, language=language)
        except (socket.timeout, ConnectionResetError, sr.RequestError) as e:
            if attempt < max_retries - 1:
                wait_time = 1.5 * (attempt + 1)
                print(f"⚠️  STT Connection flicker... (Attempt {attempt+1}/{max_retries}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                raise e # Re-raise on final failure
        except Exception as e:
            # Any other serious error (like 401 Unauthorized or 429 Rate Limit)
            raise e

def listen_hold_to_talk(key="enter"):
    """
    Record audio while Enter is held down. Uses raw PyAudio for maximum
    control and reliability, then passes the WAV to Google STT.

    Returns:
        str: Transcribed text, or None.
    """
    p = pyaudio.PyAudio()
    print(f"\n🎤 Hold [{key.upper()}] and speak... (release to stop)")

    keyboard.wait(key, suppress=True)

    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    frames = []
    print("🔴 Recording...")

    while keyboard.is_pressed(key):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

    print("⏹️ Stopped recording.")
    stream.stop_stream()
    stream.close()
    p.terminate()

    if not frames:
        print("⚠️ No audio captured. Did you hold the key long enough?")
        return None

    # Build a proper WAV buffer
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))
    wav_buffer.seek(0)

    print("⏳ Transcribing...")
    with sr.AudioFile(wav_buffer) as source:
        audio = _recognizer.record(source)

    try:
        text = _robust_recognize_google(audio, language="en-IN")
        print(f'📝 You said: "{text}"')
        return text
    except sr.UnknownValueError:
        print("❓ Couldn't understand. Please speak clearly into your mic.")
        return None
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None


def listen_continuously(wake_phrase=config.WAKE_PHRASE):
    """
    Continuously listens for the wake word 'Hey BEND'.
    
    v2 Improvements:
    - MUCH lower energy threshold so it hears soft speech
    - 30+ wake word aliases covering common mishears  
    - Fuzzy phonetic matching via difflib
    - Longer listen timeout (5s)
    - Detailed debug logging
    """
    _calibrate_once()

    print(f"\n🎧 Listening for wake word: 'Hey BEND'")
    print(f"   Energy threshold: {_recognizer.energy_threshold:.1f} (lower = more sensitive)")
    print(f"   Tip: Speak clearly and say 'Hey Bend' at normal volume")
    print(f"   Matching: exact ({len(WAKE_ALIASES)} aliases) + fuzzy phonetic matching")

    listen_count = 0
    with sr.Microphone(sample_rate=RATE) as source:
        while True:
            try:
                # timeout=5 gives a generous 5 seconds for speech to start
                audio = _recognizer.listen(source, timeout=5, phrase_time_limit=10)
                listen_count += 1

                try:
                    text_all = _robust_recognize_google(audio, language="en-IN")
                    if not text_all:
                        continue
                        
                    text_lower = text_all.lower().strip()
                    print(f"   🗣️ Heard: \"{text_all}\"")

                    # Use the new fuzzy wake word matching engine
                    matched_alias, confidence = _fuzzy_wake_match(text_lower)

                    if matched_alias:
                        _double_beep()  # Strong audio confirmation!
                        conf_pct = f"{confidence * 100:.0f}%"
                        print(f"✨ Wake word DETECTED! Match: '{matched_alias}' (confidence: {conf_pct})")
                        
                        # Try to extract inline command
                        command = _extract_command_after_wake(text_lower, matched_alias)
                        if command:
                            print(f'📝 Inline command: "{command}"')
                            return command
                        else:
                            return True   # Just the wake word — prompt for command

                    else:
                        # Not a wake word — show what was heard for debugging
                        print(f"   ❌ No wake word match in: \"{text_all}\"")

                except sr.UnknownValueError:
                    # Print a dot every 5 cycles so the user knows BEND is alive
                    if listen_count % 5 == 0:
                        print(f"   💤 Still listening... (cycle {listen_count})")
                except Exception as e:
                    print(f"❌ STT Recognition Failed: {e}")
                    # Brief pause after a heavy failure to avoid rapid-fire errors
                    time.sleep(2)

            except sr.WaitTimeoutError:
                # Also print heartbeat to confirm BEND is awake
                listen_count += 1
                if listen_count % 3 == 0:
                    print(f"   🎧 Waiting for 'Hey BEND'... (cycle {listen_count})")


def listen(timeout=8, phrase_time_limit=15):
    """
    Listen to the microphone once and return transcribed text.
    Calibrates ONCE at first call. Optimized for longer, natural commands.

    Returns:
        str: Transcribed text, or None.
    """
    _calibrate_once()

    with sr.Microphone(sample_rate=RATE) as source:
        print("🎤 Listening... (speak now)")
        try:
            audio = _recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit
            )
            print("⏳ Transcribing...")
        except sr.WaitTimeoutError:
            print("⏰ No speech detected. Please try again.")
            return None

    try:
        text = _robust_recognize_google(audio, language="en-IN")
        print(f'📝 You said: "{text}"')
        return text
    except sr.UnknownValueError:
        print("❓ Couldn't understand. Try speaking more clearly or closer to the mic.")
        return None
    except Exception as e:
        print(f"❌ Google STT API error: {e}")
        return None


# ═══════════════════════════════════════
# STANDALONE TESTS
# ═══════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "wake":
        # Test wake word detection specifically
        print("=== Wake Word Detection Test ===")
        print("Say 'Hey Bend' in different ways. Press Ctrl+C to stop.\n")
        try:
            while True:
                result = listen_continuously()
                if result is True:
                    print("🟢 WAKE WORD ONLY detected!")
                elif isinstance(result, str):
                    print(f"🟢 WAKE + COMMAND detected: '{result}'")
                print()
        except KeyboardInterrupt:
            print("\n👋 Test stopped.")
    
    elif len(sys.argv) > 1 and sys.argv[1] == "debug":
        # Debug mode: just listen and print what Google STT hears
        print("=== Debug Listener (shows raw transcription) ===")
        print("Speak anything. This shows exactly what Google hears.\n")
        _calibrate_once()
        with sr.Microphone(sample_rate=RATE) as source:
            while True:
                try:
                    audio = _recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    try:
                        text = _recognizer.recognize_google(audio, language="en-IN")
                        print(f"  RAW: \"{text}\"")
                        match, conf = _fuzzy_wake_match(text.lower())
                        if match:
                            print(f"  ✅ MATCH: {match} ({conf*100:.0f}%)")
                        else:
                            print(f"  ❌ No wake match")
                    except sr.UnknownValueError:
                        print("  (unintelligible)")
                except sr.WaitTimeoutError:
                    print("  (silence)")
                except KeyboardInterrupt:
                    print("\n👋 Debug stopped.")
                    break
    else:
        print("=== STT Module Test ===")
        print("Usage:")
        print("  python stt.py           — Hold-to-talk test")
        print("  python stt.py wake      — Wake word detection test")
        print("  python stt.py debug     — Raw transcription debug mode")
        print()
        result = listen_hold_to_talk()
        if result:
            print(f'\n✅ Transcribed: "{result}"')
        else:
            print("\n❌ No transcription result.")
