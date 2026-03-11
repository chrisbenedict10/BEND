"""
state_manager.py — Controls the voice assistant orb's visual behavior.
States: IDLE, LISTENING, PROCESSING, SPEAKING
"""

from enum import Enum

class OrbState(Enum):
    IDLE = 0
    LISTENING = 1
    PROCESSING = 2
    SPEAKING = 3

class StateManager:
    def __init__(self):
        self._current_state = OrbState.IDLE
        self._amplitude = 0.0  # Real-time mic volume (0.0 to 1.0)
        self._is_active = True

    @property
    def current_state(self):
        return self._current_state

    @current_state.setter
    def current_state(self, state: OrbState):
        if self._current_state != state:
            # print(f"🔵 State change: {self._current_state.name} -> {state.name}")
            self._current_state = state

    @property
    def amplitude(self):
        return self._amplitude

    @amplitude.setter
    def amplitude(self, value):
        # Apply smoothing to prevent extreme jumps (0.4/0.6 weighting)
        self._amplitude = (self._amplitude * 0.4) + (value * 0.6)

    def stop(self):
        self._is_active = False

# Global instance for easy access across threads
state_manager = StateManager()
