# ---- Configuration ----
import os
from dotenv import load_dotenv

load_dotenv()  # Reads from .env file in the same directory

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = "mistral-small-latest"  # Good balance of speed and intelligence
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Assistant personality
ASSISTANT_NAME = "BEND"
WAKE_PHRASE = "hey bend"

# TTS settings
TTS_RATE = 175   # Words per minute (default ~200, lower = slower)
TTS_VOLUME = 1.0 # 0.0 to 1.0

# Safety: commands containing these words will require spoken confirmation
DANGEROUS_KEYWORDS = ["shutdown", "restart", "del ", "rm ", "format", "rmdir", "taskkill"]
