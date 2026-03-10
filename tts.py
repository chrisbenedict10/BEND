"""
Module 4: Text-to-Speech (TTS)
Converts text responses into spoken audio using pyttsx3 (offline, no API needed).
"""

import pyttsx3
import config

# Initialize the TTS engine once
_engine = None


def _get_engine():
    """Lazy-initialize the TTS engine."""
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        _engine.setProperty("rate", config.TTS_RATE)
        _engine.setProperty("volume", config.TTS_VOLUME)

        # Try to pick a natural-sounding voice
        voices = _engine.getProperty("voices")
        # Prefer a female voice (index 1 on most Windows systems is "Zira")
        if len(voices) > 1:
            _engine.setProperty("voice", voices[1].id)
    return _engine


def speak(text):
    """
    Speak the given text aloud through the laptop's speakers.

    Args:
        text: The string to speak.
    """
    if not text:
        return
    print(f"🔊 Speaking: \"{text}\"")
    engine = _get_engine()
    engine.say(text)
    engine.runAndWait()


if __name__ == "__main__":
    # Quick standalone test
    print("=== TTS Module Test ===")
    speak(f"Hello! I am {config.ASSISTANT_NAME}. I am your voice assistant.")
    print("✅ TTS test complete.")
