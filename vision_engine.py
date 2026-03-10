"""
Module 7: Vision Engine
Uses pywinauto and standard Windows APIs to scan the screen for UI elements.
This allows BEND to "see" buttons, text fields, and icons.
"""

import os
import time
from pywinauto import Desktop
import pyautogui

def scan_ui_elements():
    """
    Scans the current desktop and returns a list of visible UI elements.
    Focuses on buttons, menu items, and clickable text.
    """
    elements = []
    try:
        # Get all windows on the desktop
        windows = Desktop(backend="uia").windows()
        
        # We focus on the current active window or recent ones
        for win in windows[:3]: # Scan top 3 windows for performance
            if win.is_visible():
                title = win.window_text()
                # Aggressive scan for anything clickable with "Play" in the name
                all_els = win.descendants()
                for el in all_els:
                    try:
                        name = str(el.window_text() or el.element_info.name or "").strip()
                        if el.is_visible() and ("play" in name.lower() or name == "X"):
                            rect = el.rectangle()
                            # IGNORE elements in the bottom player bar (bottom 20% of window)
                            # This prevents playing the PREVIOUS song
                            win_rect = win.rectangle()
                            bottom_limit = win_rect.top + (win_rect.height() * 0.8)
                            
                            if rect.mid_point().y < bottom_limit:
                                elements.append({
                                    "type": "ui_element",
                                    "text": name,
                                    "center": (rect.mid_point().x, rect.mid_point().y),
                                    "y": rect.mid_point().y,
                                    "window": title
                                })
                    except:
                        continue # Skip elements that throw errors during inspection
    except Exception as e:
        print(f"⚠️ Vision scan error: {e}")
    
    return elements

def find_element_by_text(text):
    """
    Search for a specific piece of text or button name on the screen.
    Returns the (x, y) coordinates if found.
    """
    text_lower = text.lower().strip()
    elements = scan_ui_elements()
    
    for el in elements:
        el_text = str(el.get("text", "")).lower()
        if text_lower in el_text:
            print(f"👁️  Found Visual element: {el['text']} at {el['center']}")
            return el["center"]
    
    return None

def click_on_text(text):
    """
    Finds text on screen and clicks it.
    """
    coords = find_element_by_text(text)
    if coords:
        pyautogui.moveTo(coords[0], coords[1], duration=0.5)
        pyautogui.click()
        return True
    return False

if __name__ == "__main__":
    print("Scanning screen for buttons...")
    els = scan_ui_elements()
    for e in els:
        print(f"[{e['type']}] {e['text']} -> {e['center']}")
