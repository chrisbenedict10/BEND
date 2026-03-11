"""
audio_listener.py — Captures real-time microphone amplitude for the orb.
Requires: PyAudio, NumPy
"""

import threading
import pyaudio
import numpy as np
from state_manager import state_manager, OrbState

# Audio capture constants
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class AudioListener:
    def __init__(self):
        self._pa = pyaudio.PyAudio()
        self._stream = None
        self._is_running = False
        self._thread = None
        self._lock = threading.Lock()
        self._noise_floor = 100 
        
    def start(self):
        """Start listening to the microphone in a separate thread."""
        try:
            self._stream = self._pa.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                start=True # Auto-start stream
            )
            self._is_running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            print("🎙️ Audio listener started.")
        except Exception as e:
            print(f"❌ Failed to start audio listener: {e}")

    def stop(self):
        """Stop capturing audio."""
        self._is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except:
                pass
        self._pa.terminate()

    def _run_loop(self):
        """Captures audio in real-time and calculates amplitude."""
        # Baseline noise floor (to avoid sensitivity to background hiss)
        while self._is_running:
            try:
                # Read audio block
                data = self._stream.read(CHUNK, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Calculate Root Mean Square (RMS) as a proxy for amplitude
                if len(audio_data) > 0:
                    rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
                    
                    # Normalize amplitude (scale to 0.0 - 1.0)
                    # 5000 is a decent baseline for speaking volume
                    norm_amp = max(0.0, (rms - self._noise_floor) / 4000.0)
                    norm_amp = min(1.0, norm_amp)
                    
                    # Update global state manager
                    state_manager.amplitude = float(norm_amp)
                    
                    # For demo purposes, auto-switch states based on sound levels
                    # (This logic is usually handled by the main_orb application,
                    # but we keep it here as a fallback/reactive layer)
                    if norm_amp > 0.08 and state_manager.current_state == OrbState.IDLE:
                        state_manager.current_state = OrbState.LISTENING
                    elif norm_amp < 0.02 and state_manager.current_state == OrbState.LISTENING:
                        # Simple timeout logic would be better, but this works for demo
                        state_manager.current_state = OrbState.IDLE

            except Exception as e:
                # Catch stream errors and ignore
                pass

# Global instance for easy starting
audio_listener = AudioListener()

if __name__ == "__main__":
    # Test capture loop
    import time
    audio_listener.start()
    try:
        while True:
            amp = state_manager.amplitude
            print(f"Volume: {'█' * int(amp * 50)} {amp:.2f}", end='\r')
            time.sleep(0.05)
    except KeyboardInterrupt:
        audio_listener.stop()
