"""
main_orb_demo.py — Standalone demo of the BEND Siri-style Voice Orb.
Cycles through all states to showcase the animations.
"""

import sys
import threading
import time
from PyQt6.QtWidgets import QApplication

# Import Orb components
from orb_ui import OrbWindow
from state_manager import state_manager, OrbState
from audio_listener import audio_listener

def state_cycler():
    """Cycles through assistant states for demo purposes."""
    print("🤖 Starting State Cycler Demo...")
    time.sleep(3)
    
    # Listening (Mic input already active)
    print("🎤 State: LISTENING (Talk to the orb!)")
    state_manager.current_state = OrbState.LISTENING
    time.sleep(10)
    
    # Processing (Thinking/Nebula)
    print("🧠 State: PROCESSING (Simulated thinking...)")
    state_manager.current_state = OrbState.PROCESSING
    time.sleep(10)
    
    # Speaking (Simulated waveform)
    print("🔊 State: SPEAKING (Simulated output...)")
    state_manager.current_state = OrbState.SPEAKING
    time.sleep(10)
    
    # Back to Idle
    print("💤 State: IDLE")
    state_manager.current_state = OrbState.IDLE

def main():
    """Main launcher."""
    # 1. Create Qt Application
    app = QApplication(sys.argv)
    
    # 2. Start Microphone Amplitude Listener
    audio_listener.start()
    
    # 3. Initialize Visual Window
    window = OrbWindow()
    window.show()
    
    # 4. Start Demo state cycling in a separate thread
    cycler_thread = threading.Thread(target=state_cycler, daemon=True)
    cycler_thread.start()
    
    # 5. Run UI Main Loop
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        audio_listener.stop()

if __name__ == "__main__":
    main()
