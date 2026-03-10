















































































"""
Module 3: Action Executor
Takes the structured JSON action from the brain and executes
the corresponding command on the Windows system.
"""

import os
import time
import subprocess
import webbrowser
import pyautogui
import config
import vision_engine


# Map of common app names to their Windows executable names or paths
# Use "start {name}" to let Windows search the PATH automatically.
# Use web URLs for mobile-first apps that you open in the browser.
APP_MAP = {
    "chrome": "start chrome",
    "google chrome": "start chrome",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "file explorer": "explorer",
    "explorer": "explorer",
    "command prompt": "cmd",
    "cmd": "cmd",
    "terminal": "wt",
    "powershell": "powershell",
    "edge": "start msedge",
    "microsoft edge": "start msedge",
    "vs code": "code",
    "vscode": "code",
    "spotify": "start spotify:",
    "discord": "discord",
    "slack": "slack",
    "word": "start winword",
    "excel": "start excel",
    "powerpoint": "start powerpnt",
    "paint": "mspaint",
    "snipping tool": "snippingtool",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    # Apps that might be installed as Windows Desktop/UWP apps, with web fallbacks
    "whatsapp": "start whatsapp:",
    "youtube": "start youtube:",
}


def execute(action_dict):
    """
    Execute an action based on the structured JSON from the brain.

    Args:
        action_dict: dict with keys 'action', 'parameters', 'spoken_response'

    Returns:
        str: The spoken_response to be read aloud by TTS.
    """
    action = action_dict.get("action", "chat_response")
    params = action_dict.get("parameters", {})
    spoken = action_dict.get("spoken_response", "Done.")

    try:
        if action == "open_app":
            _open_app(params.get("name", ""))
        elif action == "web_search":
            _web_search(params.get("query", ""))
        elif action == "open_url":
            _open_url(params.get("url", ""))
        elif action == "type_text":
            _type_text(params.get("text", ""))
        elif action == "system_command":
            _system_command(params.get("command", ""))
        elif action == "write_file":
            _write_file(params.get("path", ""), params.get("content", ""))
        elif action == "create_folder":
            _create_folder(params.get("path", ""))
        elif action == "close_app":
            _close_app(params.get("name", ""))
        elif action == "key_press":
            _key_press(params.get("keys", ""))
        elif action == "click_element":
            _click_element(params.get("text", ""))
        elif action == "vision_scan":
            return _vision_scan()
        elif action == "play_spotify":
            _play_spotify_song(params.get("song", ""))
        elif action == "wait":
            _wait(params.get("seconds", 1))
        elif action == "chat_response":
            pass  # No system action, just speak the response
        else:
            print(f"⚠️  Unknown action type: {action}")
            spoken = f"I don't know how to do that action: {action}"
    except Exception as e:
        print(f"❌ Execution error: {e}")
        spoken = f"Sorry, I ran into an error: {str(e)}"

    return spoken


def _open_app(name):
    """Open an application by name. Falls back to web URL if desktop app is missing."""
    name_lower = name.lower().strip()
    executable = APP_MAP.get(name_lower, name_lower)

    # If the exact executable is a URL, just open the URL directly
    if isinstance(executable, str) and (executable.startswith("http://") or executable.startswith("https://")):
        print(f"🌍 Opening web app: {executable}")
        webbrowser.open(executable)
        return

    print(f"🚀 Attempting to open desktop app: {executable}")

    # Handle special URI schemes (like ms-settings:)
    if isinstance(executable, str) and ":" in executable and not executable.startswith("start "):
        if hasattr(os, "startfile"):
            os.startfile(executable)
        else:
            subprocess.Popen(["cmd", "/c", "start", executable], shell=True)
        return

    # Check if a web fallback exists for this app in case the desktop version fails
    web_fallbacks = {
        "whatsapp": "https://web.whatsapp.com",
        "youtube": "https://www.youtube.com",
        "discord": "https://discord.com/app",
        "spotify": "https://open.spotify.com",
    }

    # If it's a URI scheme (like 'start whatsapp:')
    if isinstance(executable, str) and executable.startswith("start ") and executable.endswith(":"):
        uri = executable.replace("start ", "")
        try:
            # os.startfile understands URI schemes
            if hasattr(os, "startfile"):
                os.startfile(uri)
            else:
                subprocess.Popen(["cmd", "/c", "start", uri], shell=True)
            return
        except Exception:
            print(f"⚠️ App not installed ({uri}). Falling back to web.")
            if name_lower in web_fallbacks:
                webbrowser.open(web_fallbacks[name_lower])
            return

    # Handle other special URI schemes (like ms-settings:)
    if isinstance(executable, str) and ":" in executable and not executable.startswith("start "):
        try:
            if hasattr(os, "startfile"):
                os.startfile(executable)
            else:
                subprocess.Popen(["cmd", "/c", "start", executable], shell=True)
        except Exception:
            pass
        return

    # Try to launch traditional executables
    try:
        if not isinstance(executable, str):
            executable = str(executable) if executable is not None else ""
            
        # Use 'start' to let Windows search the PATH
        if not executable.startswith("start "):
            launch_cmd = f"start {executable}"
        else:
            launch_cmd = executable
            
        subprocess.Popen(launch_cmd, shell=True)
            
    except Exception as e:
        print(f"❌ Failed to open {name_lower}: {e}")
        if name_lower in web_fallbacks:
            print(f"   Falling back to web version.")
            webbrowser.open(web_fallbacks[name_lower])


def _web_search(query):
    """Open a web search in the default browser."""
    if not query:
        return
    url = f"https://www.google.com/search?q={query}"
    print(f"🔍 Searching: {query}")
    webbrowser.open(url)


def _open_url(url):
    """Open a specific URL in the default browser."""
    if not url:
        return
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    print(f"🌍 Opening URL: {url}")
    webbrowser.open(url)


def _write_file(path, content):
    """Write text content to a file on disk. Supports ~ for home directory."""
    if not path:
        return
    
    # Expand ~ to the user's home directory
    path = os.path.expanduser(path)
    
    # Create directories if they don't exist
    target_dir = os.path.dirname(os.path.abspath(path))
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
    
    print(f"💾 Writing file: {path}")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"   Successfully wrote {len(content)} characters.")
    except PermissionError:
        print(f"   Permission denied to write to: {path}")
        raise Exception(f"Permission denied. I can't write to {path}. Try a different location like your home folder.")
    except Exception as e:
        print(f"   Failed to write file: {e}")
        raise


def _play_spotify_song(song_name: str):
    """
    Dedicated Spotify song player.
    Strategy:
    1. Open Spotify
    2. Search for song using Ctrl+L
    3. Wait for Top Result to appear
    4. Calculate position of the green play button (always at ~57% x, ~28% y in the window)
    5. Click it directly using pyautogui
    """
    if not song_name:
        print("⚠️ No song name provided.")
        return

    print(f"🎵 Playing '{song_name}' on Spotify...")

    # Step 1: Open / Focus Spotify
    _open_app("spotify")
    print("⏳ Waiting for Spotify to load...")
    time.sleep(5)

    # Step 2: Focus search bar and clear it completely
    print("🔍 Focusing search bar...")
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.8)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.3)
    pyautogui.press("backspace")
    time.sleep(0.5)

    # Step 3: Type song name slowly character by character
    print(f"⌨️ Typing: {song_name}")
    for char in song_name:
        pyautogui.typewrite(char if char.isascii() else '?', interval=0.07)
    print("⏳ Waiting for Top Result to load...")
    time.sleep(4.5)

    # Step 4: Find the Spotify window position and click the green play button
    # The green play button in the Top Result card is ALWAYS at ~57% x, ~28% y of the window
    try:
        from pywinauto import Desktop
        wins = Desktop(backend="uia").windows()
        spotify_win = None
        for w in wins:
            try:
                title = w.window_text()
                if "spotify" in title.lower() or w.is_visible():
                    # Check if it's likely Spotify by class or title
                    cls = w.element_info.class_name or ""
                    if "spotify" in title.lower() or "chrome_widget_win" in cls.lower():
                        spotify_win = w
                        break
            except:
                continue

        if spotify_win:
            rect = spotify_win.rectangle()
            win_x = rect.left
            win_y = rect.top
            win_w = rect.width()
            win_h = rect.height()

            # The green play button in the Top Result:
            # Horizontally: at about 56-57% of the window width
            # Vertically: at about 27-28% of the window height (below title bar ~40px)
            btn_x = int(win_x + win_w * 0.565)
            btn_y = int(win_y + win_h * 0.275)

            print(f"🖱️  Clicking green play button at ({btn_x}, {btn_y})...")
            pyautogui.moveTo(btn_x, btn_y, duration=0.4)
            time.sleep(0.3)
            pyautogui.click()
            print(f"▶️  Clicked play for '{song_name}'.")
        else:
            # Fallback: use Tab + Enter navigation
            print("⚠️ Could not find Spotify window. Using keyboard fallback...")
            for _ in range(3):
                pyautogui.press("tab")
                time.sleep(0.3)
            pyautogui.press("enter")
    except Exception as e:
        print(f"⚠️ Click failed: {e}. Using keyboard fallback.")
        pyautogui.press("enter")
        time.sleep(0.5)
        pyautogui.press("enter")


def _create_folder(path):
    """Create a new folder at the specified path. Supports ~ for home directory."""
    if not path:
        return
    
    path = os.path.expanduser(path)
    print(f"📁 Creating folder: {path}")
    
    try:
        os.makedirs(path, exist_ok=True)
        print(f"   Successfully created folder.")
    except PermissionError:
        print(f"   Permission denied to create folder: {path}")
        raise Exception(f"Permission denied. I can't create a folder at {path}.")
    except Exception as e:
        print(f"   Failed to create folder: {e}")
        raise


def _type_text(text):
    """Type text at the current cursor position, supporting newlines."""
    if not text:
        text = ""
    print(f"⌨️  Typing text block...")
    # Slower, more reliable typing speed for Windows
    pyautogui.PAUSE = 0.05
    pyautogui.write(text, interval=0.03)


def _system_command(command):
    """Run a PowerShell command with safety checks."""
    if not command:
        return

    # Safety check for dangerous commands
    cmd_lower = command.lower()
    for keyword in config.DANGEROUS_KEYWORDS:
        if keyword in cmd_lower:
            print(f"⚠️  DANGEROUS COMMAND BLOCKED: {command}")
            print(f"   Contains dangerous keyword: '{keyword}'")
            raise Exception(f"Blocked dangerous command containing '{keyword}'. Say 'force' to override.")

    print(f"💻 Running: {command}")
    result = subprocess.run(
        ["powershell", "-Command", command],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.stdout:
        output_snippet = result.stdout.strip()
        # Use simple string truncation for linter compatibility
        if len(output_snippet) > 200:
            output_snippet = output_snippet[0:200]
        print(f"   Output: {output_snippet}")
    if result.stderr:
        error_snippet = result.stderr.strip()
        if len(error_snippet) > 200:
            error_snippet = error_snippet[0:200]
        print(f"   Error: {error_snippet}")


def _close_app(name):
    """Close a running application by process name."""
    name_lower = name.lower().strip()
    # Map app names to process names
    process_map = {
        "chrome": "chrome",
        "notepad": "notepad",
        "spotify": "Spotify",
        "discord": "Discord",
        "edge": "msedge",
        "vs code": "Code",
        "vscode": "Code",
    }
    process_name = process_map.get(name_lower, name_lower)
    print(f"🛑 Closing: {process_name}")
    subprocess.run(
        ["powershell", "-Command", f"Stop-Process -Name '{process_name}' -Force -ErrorAction SilentlyContinue"],
        capture_output=True,
    )


def _key_press(keys):
    """Press a key or key combination (e.g., 'enter', 'ctrl+s', 'alt+f4')."""
    if not keys:
        return
    keys_lower = keys.lower().strip()
    print(f"⌨️  Pressing: {keys_lower}")

    if "+" in keys_lower:
        # It's a hotkey combo like "ctrl+s"
        parts = [k.strip() for k in keys_lower.split("+")]
        pyautogui.hotkey(*parts)
    else:
        pyautogui.press(keys_lower)


def _wait(seconds):
    """Pause execution for a given number of seconds."""
    if not isinstance(seconds, (int, float)):
        seconds = 1
    seconds = min(max(float(seconds), 0.5), 10)  # Clamp between 0.5 and 10
    print(f"⏳ Waiting {seconds}s...")
    time.sleep(seconds)


def _click_element(text):
    """Finds a UI element by text and clicks it."""
    if not text:
        return
    print(f"👁️  Searching for element to click: {text}")
    success = vision_engine.click_on_text(text)
    if not success:
        raise Exception(f"Could not find UI element '{text}' on screen.")


def _vision_scan():
    """Scans the screen and returns a summary of buttons found."""
    print("👁️  Scanning screen for UI elements...")
    elements = vision_engine.scan_ui_elements()
    if not elements:
        return "I can't see any buttons or elements on the screen right now."
    
    # Create a nice summary for the AI
    summary = "Visible UI Elements:\n"
    for el in elements[:15]: # Limit to 15 to stay focused
        summary += f"- {el['type']}: '{el['text']}'\n"
    
    # We return the summary so it can be used as a spoken response or context
    return summary


if __name__ == "__main__":
    # Quick standalone test — opens Notepad
    print("=== Executor Module Test ===")
    test_action = {
        "action": "open_app",
        "parameters": {"name": "notepad"},
        "spoken_response": "Opening Notepad for you.",
    }
    result = execute(test_action)
    print(f"Spoken: {result}")
