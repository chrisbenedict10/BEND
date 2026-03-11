"""
Module 6: Knowledge Base
Stores application-specific keyboard shortcuts and interaction patterns.
These are dynamically injected into the AI's prompt only when the user
mentions the specific application, to save tokens and prevent confusion.
"""

APP_SHORTCUTS = {
    "whatsapp": """
WHATSAPP AUTOMATION (Reliable Messaging):
- For ANY request to text/call someone or open a chat on WhatsApp:
- ALWAYS use the single "whatsapp_message" action with parameters: { "contact": "<name>", "message": "<text>" }.
- NEVER break it down into "open_app", "wait", and "key_press" steps yourself.
- The "whatsapp_message" action in the executor handles the entire sequence: opening the app, searching for the contact, and typing the message.

Other WhatsApp Shortcuts (for manual control):
- Focus search: ctrl+f
- New chat: ctrl+n
- Mark unread: ctrl+shift+u
- Mute/unmute: ctrl+shift+m
- Archive chat: ctrl+e
- Delete chat: ctrl+backspace
- Search in chat: ctrl+f
- Zoom in/out/reset: ctrl++, ctrl+-, ctrl+0
- Next/Prev chat: ctrl+tab, ctrl+shift+tab
""",

    "chrome": """
GOOGLE CHROME SHORTCUTS:
- New tab: ctrl+t
- Close tab: ctrl+w
- Reopen closed tab: ctrl+shift+t
- Next/prev tab: ctrl+tab, ctrl+shift+tab
- Focus address bar: ctrl+l
- Find on page: ctrl+f
- History: ctrl+h
- Downloads: ctrl+j
- Bookmark: ctrl+d
- Incognito: ctrl+shift+n
- Reload: ctrl+r
- Zoom in/out: ctrl++, ctrl+-
- Go back/forward: alt+left, alt+right
""",

    "word": """
MICROSOFT WORD SHORTCUTS:
- New doc: ctrl+n
- Open doc: ctrl+o
- Save: ctrl+s
- Save As: ctrl+shift+s
- Print: ctrl+p
- Select all: ctrl+a
- Find / Replace: ctrl+f / ctrl+h
- Bold/Italic/Underline: ctrl+b, ctrl+i, ctrl+u
- Align Left/Center/Right/Justify: ctrl+l, ctrl+e, ctrl+r, ctrl+j
- Hyperlink: ctrl+k
- Spell check: f7
""",

    "excel": """
MICROSOFT EXCEL SHORTCUTS:
- New workbook: ctrl+n
- Save: ctrl+s
- Find / Replace: ctrl+f / ctrl+h
- Go to A1 / Last cell: ctrl+home, ctrl+end
- Toggle filters: ctrl+shift+l
- AutoSum: alt+=
- Create table: ctrl+t
- Edit cell: f2
- Lock reference ($): f4
- Format cells: ctrl+1
- Insert/delete row/col: ctrl+shift++, ctrl+-
- Next/prev sheet: ctrl+pagedown, ctrl+pageup
""",

    "spotify": """
SPOTIFY AUTOMATION (Reliable Playback):
- For ANY request to play music, a song, or an artist:
- ALWAYS use the single "play_spotify" action with the parameters: { "song": "<song/artist name>" }.
- NEVER break it down into "open_app", "vision_scan", or "key_press" steps.
- The "play_spotify" action handles the entire process: opening the app, searching, and clicking the green play button.

Other Spotify Shortcuts:
- Play/Pause: space
- Next/Prev track: ctrl+right, ctrl+left
- Volume up/down: ctrl+up, ctrl+down
- Search / Focus search: ctrl+f, ctrl+l
""",

    "zoom": """
ZOOM SHORTCUTS (Meeting controls):
- Mute/unmute audio: alt+a
- Start/stop video: alt+v
- Start/stop screen share: alt+s
- Pause/resume screen share: alt+t
- Record: alt+r
- Show/hide chat: alt+h
- Show/hide participants: alt+u
- Raise/lower hand: alt+y
- Full screen: alt+f
- Leave meeting: ctrl+w
""",

    "slack": """
SLACK SHORTCUTS:
- Quick switcher: ctrl+k
- Search: ctrl+f
- Browse DMs / channels: ctrl+shift+k, ctrl+shift+l
- Threads: ctrl+shift+t
- Prev/next channel: alt+up, alt+down
- Go back/forward: ctrl+[, ctrl+]
- Activity / mentions: ctrl+shift+m
- Emoji: ctrl+shift+e
- Set status: ctrl+shift+y
- Toggle mute in huddle: ctrl+shift+space
""",

    "notepad": """
NOTEPAD SHORTCUTS:
- New / Open: ctrl+n, ctrl+o
- Save / Save As: ctrl+s, ctrl+shift+s
- Print: ctrl+p
- Select all: ctrl+a
- Find / Replace: ctrl+f / ctrl+h
- Go to line: ctrl+g
- Insert date/time: f5
""",

    "explorer": """
FILE EXPLORER SHORTCUTS:
- Open Explorer: win+e
- Go back/forward/up: alt+left, alt+right, alt+up
- Rename: f2 
- Refresh: f5
- New window / close: ctrl+n, ctrl+w
- Search: ctrl+f
- New folder: ctrl+shift+n
- Properties: alt+enter
- Address bar: alt+d
- Delete / Permanent: delete, shift+delete
""",

    "task manager": """
TASK MANAGER SHORTCUTS:
- Open Task Manager: ctrl+shift+esc
- Close: alt+f4
- Refresh data: f5
- End task: delete
- Cycle tabs: ctrl+tab
- Process properties: alt+enter
"""
}

def get_relevant_shortcuts(user_text):
    """
    Looks for app names in the user's text and returns their specific shortcuts.
    """
    text_lower = user_text.lower()
    injections = []
    
    for app_name, shortcuts in APP_SHORTCUTS.items():
        if app_name in text_lower:
            injections.append(shortcuts)
            
    # Also catch common aliases
    if "browser" in text_lower and "chrome" not in text_lower:
        injections.append(APP_SHORTCUTS["chrome"])
    if "music" in text_lower and "spotify" not in text_lower:
        injections.append(APP_SHORTCUTS["spotify"])

    if not injections:
        return ""
        
    final_output = "\n\n═══════════════════════════════════════\nAPP-SPECIFIC KNOWLEDGE FOR THIS REQUEST:\n═══════════════════════════════════════\n"
    for injection in injections:
        final_output += str(injection) + "\n"
    return final_output
