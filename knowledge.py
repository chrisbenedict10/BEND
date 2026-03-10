"""
Module 6: Knowledge Base
Stores application-specific keyboard shortcuts and interaction patterns.
These are dynamically injected into the AI's prompt only when the user
mentions the specific application, to save tokens and prevent confusion.
"""

APP_SHORTCUTS = {
    "whatsapp": """
WHATSAPP AUTOMATION (Calls & Messages):
If asked to text/call someone on WhatsApp:
1. open_app "whatsapp"
2. wait 5 seconds (it takes time to load)
3. key_press "ctrl+f", wait 1 sec (focuses search box on Desktop App)
4. type_text "<contact name>"
5. wait 2 seconds (for search results)
6. key_press "tab", wait 0.5 sec, key_press "enter" (focus and open chat)
7. wait 1 second
8. For messages: type_text "<message>", wait 1, key_press "enter"
   For audio call: key_press "ctrl+shift+a" (WhatsApp Desktop shortcut for voice call)
   For video call: key_press "ctrl+shift+v" (WhatsApp Desktop shortcut for video call)

Other WhatsApp Shortcuts:
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
SPOTIFY SHORTCUTS:
- Play/Pause: space
- Next/Prev track: ctrl+right, ctrl+left
- Volume up/down: ctrl+up, ctrl+down
- Max vol / Mute: ctrl+shift+up, ctrl+shift+down
- Search / Focus search: ctrl+f, ctrl+l
- New playlist / folder: ctrl+n, ctrl+shift+n
- Toggle repeat / shuffle: ctrl+r, ctrl+s
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
