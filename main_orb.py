import os
import sys
import threading
import time

# Set DPI awareness BEFORE any UI is created
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal

# Import existing BEND modules
import stt
import brain
import executor
import tts
import config

# Import new Orb components
from orb_ui import OrbWindow
from state_manager import state_manager, OrbState
from audio_listener import audio_listener

import pythoncom

class AssistantThread(QThread):
    """Runs the BEND voice assistant loop in a background thread."""
    def run(self):
        # Initialize COM for this thread so pyttsx3 (SAPI5) can work reliably
        pythoncom.CoInitialize()
        print("🤖 BEND Assistant Logic starting...")
        
        while True:
            try:
                # 1. Listening Phase
                state_manager.current_state = OrbState.IDLE
                result = stt.listen_continuously(config.WAKE_PHRASE)
                
                # 2. Recognition/Wake Phase
                state_manager.current_state = OrbState.LISTENING
                
                command = None
                if result is True:
                    # Wake word heard
                    tts.speak("How can I help?")
                    command = stt.listen()
                elif isinstance(result, str):
                    # Inline command
                    command = result
                
                if command:
                    # 3. Processing Phase
                    state_manager.current_state = OrbState.PROCESSING
                    print(f"🧠 Thinking: {command}")
                    steps = brain.think(command)
                    
                    # 4. Action/Speaking Phase
                    for i, step in enumerate(steps):
                        # Speak
                        spoken = step.get("spoken_response", "")
                        if spoken:
                            state_manager.current_state = OrbState.SPEAKING
                            tts.speak(spoken)
                        
                        # Execute
                        state_manager.current_state = OrbState.PROCESSING
                        result = executor.execute(step)
                        
                        if result != spoken and result:
                            state_manager.current_state = OrbState.SPEAKING
                            tts.speak(result)
                            
            except Exception as e:
                print(f"❌ Error in Assistant Loop: {e}")
                time.sleep(1)

def main():
    """Main launcher."""
    # 1. Create Qt Application
    app = QApplication(sys.argv)
    
    # 2. Start Microhpone Amplitude Listener (for real-time bounce)
    audio_listener.start()
    
    # 3. Initialize Visual Window
    window = OrbWindow()
    window.show()
    
    # 4. Start Assistant Logic in background thread
    assistant = AssistantThread()
    assistant.start()
    
    # 5. Run UI Main Loop
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        audio_listener.stop()

if __name__ == "__main__":
    main()
