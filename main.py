"""
J.A.R.V.I.S — Voice-Controlled Laptop Assistant
Main entry point. Ties all modules together in a listen-think-act-speak loop.

Usage:
    python main.py

Say the wake phrase (e.g., "HEY BEND") to activate, then speak your command.
Press [Esc] at any time to quit.
"""

import keyboard
import threading
import time
import stt
import brain
import executor
import tts
import config


BANNER = f"""
╔══════════════════════════════════════════════════╗
║                                                  ║
║       🤖     B E N D  Voice Assistant    🤖      ║
║                                                  ║
║   Say "HEY BEND" to activate                     ║
║   Press [Esc]    to quit                         ║
║                                                  ║
╚══════════════════════════════════════════════════╝
"""


def process_command(user_text):
    """Send command to AI Brain, execute steps, and speak responses."""
    if not user_text or user_text is True:
        return

    # Send to AI Brain
    print("🧠 Thinking...")
    steps = brain.think(user_text)

    # Execute each step and speak its response
    for i, step in enumerate(steps):
        print(f"\n--- Step {i + 1}/{len(steps)} ---")

        # Speak before executing (if there's something to say)
        spoken = step.get("spoken_response", "")
        if spoken:
            tts.speak(spoken)

        # Execute the action
        result = executor.execute(step)

        # If execute returned an error message different from the original, speak it
        if result != spoken and result:
            tts.speak(result)


def main():
    """Main loop — continuous wake word detection style."""
    print(BANNER)

    # Start a thread to check for the escape key so we can quit cleanly anytime
    def check_quit():
        keyboard.wait("esc")
        print("\n👋 Esc pressed. Shutting down.")
        os._exit(0)
        
    import os
    threading.Thread(target=check_quit, daemon=True).start()

    while True:
        try:
            # 1. Continuous Listening for Wake Word
            result = stt.listen_continuously(config.WAKE_PHRASE)
            
            if result is True:
                # Only wake word was heard, ask "How can I help?"
                tts.speak("How can I help?")
                command = stt.listen()
                if command:
                    process_command(command)
            elif isinstance(result, str):
                # Inline command heard (e.g. "Hey Bend open notepad")
                process_command(result)
                
        except KeyboardInterrupt:
            print("\n👋 Interrupted. Shutting down.")
            break
        except Exception as e:
            print(f"❌ Unexpected error in loop: {e}")
            time.sleep(1) # Short pause before retry


if __name__ == "__main__":
    main()
