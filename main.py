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
║   Hold [ENTER] Key to Speak                      ║
║   Press [Esc]    to quit                         ║
║                                                  ║
╚══════════════════════════════════════════════════╝
"""


def run_once():
    """Single cycle of listening, thinking, and executing."""
    
    # 1. Listen for command (Hold Enter to talk)
    user_text = stt.listen_hold_to_talk("enter")
        
    if not user_text:
        return

    # 3. Send to AI Brain
    print("🧠 Thinking...")
    steps = brain.think(user_text)

    # Step 3 & 4: Execute each step and speak its response
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
            run_once()
        except KeyboardInterrupt:
            print("\n👋 Interrupted. Shutting down.")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            tts.speak("Something went wrong. Let's try again.")


if __name__ == "__main__":
    main()
