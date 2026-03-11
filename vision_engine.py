"""
Module 7: Vision Engine
Uses pywinauto UIA backend + Win32 accessibility APIs to scan the screen
for ALL visible UI elements — buttons, text, links, menus, tabs, etc.

Key improvements over the original:
  • Scans the ACTIVE (foreground) window by default for speed, with a
    fallback to all visible windows.
  • Detects ALL control types (Button, Text, Edit, MenuItem, TabItem,
    Hyperlink, ListItem, TreeItem, CheckBox, RadioButton, ComboBox, etc.)
    instead of only "play" and "X".
  • Groups results by window and control type for easy consumption.
  • Supports partial and fuzzy text matching in find_element_by_text().
  • Integrates OCR (pytesseract) as a fallback when UIA cannot read
    certain custom-rendered UIs (e.g. Electron apps, Spotify, games).
"""

import time
import pyautogui
import numpy as np
from pywinauto import Desktop
from pywinauto.controls.uiawrapper import UIAWrapper

# ---------------------------------------------------------------------------
# Control types we care about (covers virtually all interactive & text elements)
# ---------------------------------------------------------------------------
INTERACTIVE_CONTROL_TYPES = {
    "Button", "SplitButton", "ToggleButton", "MenuButton",
    "MenuItem", "Menu", "MenuBar",
    "TabItem", "Tab",
    "Hyperlink", "Link",
    "ListItem", "TreeItem", "DataItem",
    "CheckBox", "RadioButton",
    "ComboBox", "Slider", "ScrollBar", "Spinner",
    "ToolBar", "ToolBarButton",
    "StatusBar",
}

TEXT_CONTROL_TYPES = {
    "Text", "Edit", "Document",
    "Header", "HeaderItem",
    "TitleBar",
}

ALL_CONTROL_TYPES = INTERACTIVE_CONTROL_TYPES | TEXT_CONTROL_TYPES

# Maximum number of elements to return (prevents overwhelming the AI)
MAX_ELEMENTS = 80

# Minimum text length worth reporting (skip blank or pure-whitespace labels)
MIN_TEXT_LEN = 1


# ---------------------------------------------------------------------------
# Core scanning
# ---------------------------------------------------------------------------

def _get_foreground_window():
    """Return the pywinauto wrapper for the current foreground window, or None."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            from pywinauto import Application
            app = Application(backend="uia").connect(handle=hwnd)
            return app.window(handle=hwnd)
    except Exception:
        pass
    return None


def _safe_element_info(el):
    """Extract element info safely, returning None if the element is stale."""
    try:
        name = str(el.window_text() or "").strip()
        if not name:
            # Try automation_id or legacy name as a backup
            try:
                name = str(el.element_info.name or "").strip()
            except Exception:
                pass
        if not name or len(name) < MIN_TEXT_LEN:
            return None

        if not el.is_visible():
            return None

        # Get control type
        try:
            ctrl_type = el.element_info.control_type or "Unknown"
        except Exception:
            ctrl_type = "Unknown"

        # Get bounding rectangle
        rect = el.rectangle()
        if rect.width() <= 0 or rect.height() <= 0:
            return None

        cx = rect.mid_point().x
        cy = rect.mid_point().y

        # Skip off-screen elements (negative or extremely large coordinates)
        if cx < 0 or cy < 0 or cx > 5000 or cy > 5000:
            return None

        return {
            "type": ctrl_type,
            "text": name,
            "center": (cx, cy),
            "rect": (rect.left, rect.top, rect.right, rect.bottom),
            "y": cy,
        }
    except Exception:
        return None


def scan_ui_elements(active_window_only=True, include_text=True):
    """
    Scans visible UI elements and returns a list of dicts.

    Each dict has:
        type   — The UIA control type (e.g. "Button", "MenuItem", "Text")
        text   — The visible label / name
        center — (x, y) screen coordinates for clicking
        rect   — (left, top, right, bottom) bounding rectangle
        y      — Vertical position (for sorting)

    Args:
        active_window_only: If True, only scan the foreground window (faster).
                            Falls back to scanning all visible windows if nothing
                            is found or the foreground window cannot be determined.
        include_text:       If True, include static text / labels. Set False to
                            get only clickable elements.

    Returns:
        list[dict]
    """
    wanted_types = ALL_CONTROL_TYPES if include_text else INTERACTIVE_CONTROL_TYPES
    elements = []
    seen_texts = set()  # Deduplicate by (text, approximate position)

    def _scan_window(win):
        """Scan one window's descendants and collect matching elements."""
        nonlocal elements
        try:
            win_title = win.window_text()
        except Exception:
            win_title = ""

        try:
            descendants = win.descendants()
        except Exception:
            return

        for el in descendants:
            if len(elements) >= MAX_ELEMENTS:
                break
            try:
                info = _safe_element_info(el)
                if info is None:
                    continue

                ctrl_type = info["type"]
                if ctrl_type not in wanted_types and ctrl_type != "Unknown":
                    # For "Unknown" types, keep them if they have 
                    # meaningful text (catches custom controls)
                    if ctrl_type != "Unknown":
                        continue

                # Deduplicate: skip if we already saw the exact same text
                # at approximately the same position
                dedup_key = (info["text"].lower(), info["center"][0] // 30, info["center"][1] // 30)
                if dedup_key in seen_texts:
                    continue
                seen_texts.add(dedup_key)

                info["window"] = win_title
                elements.append(info)
            except Exception:
                continue

    # --- Strategy 1: Scan the foreground (active) window ---
    if active_window_only:
        fg_win = _get_foreground_window()
        if fg_win:
            try:
                _scan_window(fg_win)
            except Exception:
                pass

    # --- Strategy 2: Fall back to all visible windows ---
    if not elements:
        try:
            windows = Desktop(backend="uia").windows()
            for win in windows[:5]:  # Top 5 windows for performance
                if len(elements) >= MAX_ELEMENTS:
                    break
                try:
                    if win.is_visible():
                        _scan_window(win)
                except Exception:
                    continue
        except Exception as e:
            print(f"⚠️ Desktop scan error: {e}")

    # Sort by vertical position (top-to-bottom reading order)
    elements.sort(key=lambda e: (e["y"], e["center"][0]))

    count = len(elements)
    if count:
        print(f"👁️  Vision scan found {count} UI elements.")
    else:
        print("👁️  Vision scan found 0 elements — trying OCR fallback...")
        elements = _ocr_fallback_scan()

    return elements


# ---------------------------------------------------------------------------
# OCR fallback — for apps that don't expose UIA elements well
# ---------------------------------------------------------------------------

def _ocr_fallback_scan(region=None, confidence_threshold=60):
    """
    Use Tesseract OCR to read on-screen text when the UIA tree is sparse.
    Returns a list of element dicts compatible with scan_ui_elements output.
    """
    elements = []
    try:
        import pytesseract
        img = pyautogui.screenshot(region=region)
        # Pre-process for better OCR: convert to grayscale, increase contrast
        img_np = np.array(img)
        gray = np.mean(img_np, axis=2).astype(np.uint8)
        from PIL import Image
        gray_img = Image.fromarray(gray)

        data = pytesseract.image_to_data(gray_img, output_type=pytesseract.Output.DICT)

        current_line = []
        last_line_num = -1

        for i in range(len(data["text"])):
            word = str(data["text"][i]).strip()
            conf = int(data["conf"][i])
            if not word or conf < confidence_threshold:
                continue

            x = data["left"][i]
            y = data["top"][i]
            w = data["width"][i]
            h = data["height"][i]

            if region:
                x += region[0]
                y += region[1]

            cx = x + w // 2
            cy = y + h // 2

            elements.append({
                "type": "OCR_Text",
                "text": word,
                "center": (cx, cy),
                "rect": (x, y, x + w, y + h),
                "y": cy,
                "window": "Screen (OCR)",
            })

        # Merge adjacent words on the same line into phrases
        elements = _merge_ocr_words(elements)

        if elements:
            print(f"📝 OCR fallback found {len(elements)} text regions.")
    except ImportError:
        print("ℹ️  pytesseract not installed — OCR fallback unavailable.")
    except Exception as e:
        print(f"⚠️  OCR fallback error: {e}")

    return elements


def _merge_ocr_words(elements, x_gap_threshold=25, y_tolerance=10):
    """
    Merge OCR words that are on the same line and close together
    into multi-word phrases for better readability.
    """
    if not elements:
        return elements

    merged = []
    current_group = [elements[0]]

    for el in elements[1:]:
        prev = current_group[-1]
        # Same line (close y) and close horizontally
        if (abs(el["center"][1] - prev["center"][1]) < y_tolerance and
                el["rect"][0] - prev["rect"][2] < x_gap_threshold):
            current_group.append(el)
        else:
            merged.append(_merge_group(current_group))
            current_group = [el]

    if current_group:
        merged.append(_merge_group(current_group))

    return merged


def _merge_group(group):
    """Merge a list of adjacent OCR word elements into one."""
    if len(group) == 1:
        return group[0]

    text = " ".join(el["text"] for el in group)
    left = min(el["rect"][0] for el in group)
    top = min(el["rect"][1] for el in group)
    right = max(el["rect"][2] for el in group)
    bottom = max(el["rect"][3] for el in group)
    cx = (left + right) // 2
    cy = (top + bottom) // 2

    return {
        "type": "OCR_Text",
        "text": text,
        "center": (cx, cy),
        "rect": (left, top, right, bottom),
        "y": cy,
        "window": group[0].get("window", "Screen (OCR)"),
    }


# ---------------------------------------------------------------------------
# Element finding & clicking
# ---------------------------------------------------------------------------

def find_element_by_text(text, interactive_only=False):
    """
    Search for a UI element whose label contains `text` (case-insensitive).

    Matching priority:
      1. Exact match (element text == search text)
      2. Starts-with match
      3. Contains match

    Returns the (x, y) coordinates if found, else None.
    """
    text_lower = text.lower().strip()
    if not text_lower:
        return None

    elements = scan_ui_elements(
        active_window_only=True,
        include_text=not interactive_only,
    )

    # Categorize matches by quality
    exact = []
    starts_with = []
    contains = []

    for el in elements:
        el_text = str(el.get("text", "")).lower()
        if el_text == text_lower:
            exact.append(el)
        elif el_text.startswith(text_lower):
            starts_with.append(el)
        elif text_lower in el_text:
            contains.append(el)

    # Pick the best match
    best = None
    if exact:
        best = exact[0]
    elif starts_with:
        best = starts_with[0]
    elif contains:
        best = contains[0]

    if best:
        print(f"👁️  Found element: '{best['text']}' [{best['type']}] at {best['center']}")
        return best["center"]

    # If no UIA match was found, try a dedicated OCR search for just that text
    print(f"👁️  UIA search for '{text}' failed — trying OCR...")
    return _ocr_find_text(text)


def _ocr_find_text(search_text, region=None, confidence_threshold=55):
    """
    Dedicated OCR search for a specific piece of text on screen.
    Returns (x, y) or None.
    """
    try:
        import pytesseract
        img = pyautogui.screenshot(region=region)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        search_lower = search_text.lower().strip()

        # First pass: look for the text in individual words
        for i, word in enumerate(data["text"]):
            word_str = str(word).strip()
            if not word_str:
                continue
            conf = int(data["conf"][i])
            if conf < confidence_threshold:
                continue
            if search_lower in word_str.lower():
                x = data["left"][i] + data["width"][i] // 2
                y = data["top"][i] + data["height"][i] // 2
                if region:
                    x += region[0]
                    y += region[1]
                print(f"📝 OCR found '{word_str}' at ({x},{y}) conf={conf}")
                return (x, y)

        # Second pass: join adjacent words and look for multi-word matches
        full_text_parts = []
        for i, word in enumerate(data["text"]):
            word_str = str(word).strip()
            if word_str and int(data["conf"][i]) >= confidence_threshold:
                full_text_parts.append({
                    "word": word_str,
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "w": data["width"][i],
                    "h": data["height"][i],
                })

        # Build running text to find multi-word phrases
        for start in range(len(full_text_parts)):
            phrase = ""
            for end in range(start, min(start + 8, len(full_text_parts))):
                phrase += (" " if phrase else "") + full_text_parts[end]["word"]
                if search_lower in phrase.lower():
                    # Return center of the matching span
                    left = full_text_parts[start]["x"]
                    top = min(p["y"] for p in full_text_parts[start:end + 1])
                    right = full_text_parts[end]["x"] + full_text_parts[end]["w"]
                    bottom = max(p["y"] + p["h"] for p in full_text_parts[start:end + 1])
                    cx = (left + right) // 2
                    cy = (top + bottom) // 2
                    if region:
                        cx += region[0]
                        cy += region[1]
                    print(f"📝 OCR phrase match: '{phrase}' at ({cx},{cy})")
                    return (cx, cy)

    except ImportError:
        print("ℹ️  pytesseract not installed — OCR search unavailable.")
    except Exception as e:
        print(f"⚠️  OCR search error: {e}")

    print(f"❌ Could not find '{search_text}' on screen via UIA or OCR.")
    return None


def click_on_text(text):
    """
    Finds text on screen (UIA + OCR fallback) and clicks it.
    Returns True on success, False if not found.
    """
    coords = find_element_by_text(text)
    if coords:
        x, y = coords
        print(f"🖱️  Clicking '{text}' at ({x}, {y})...")
        pyautogui.moveTo(x, y, duration=0.4)
        time.sleep(0.2)
        pyautogui.click()
        return True
    return False


def find_all_buttons(active_window_only=True):
    """
    Convenience function: returns only interactive/clickable elements
    (buttons, menu items, tabs, links, etc.) — no static text.
    """
    return scan_ui_elements(
        active_window_only=active_window_only,
        include_text=False,
    )


def get_screen_summary(active_window_only=True):
    """
    Return a human-readable summary of visible UI elements,
    grouped by control type. Suitable for speaking or logging.
    """
    elements = scan_ui_elements(active_window_only=active_window_only)
    if not elements:
        return "I can't see any buttons or elements on the screen right now."

    # Group by type
    by_type = {}
    for el in elements:
        ctrl_type = el["type"]
        by_type.setdefault(ctrl_type, []).append(el["text"])

    lines = [f"Visible UI Elements ({len(elements)} total):"]
    for ctrl_type, texts in by_type.items():
        label = ctrl_type.replace("Item", " Item")
        items = ", ".join(f"'{t}'" for t in texts[:10])
        if len(texts) > 10:
            items += f" ... and {len(texts) - 10} more"
        lines.append(f"  {label}: {items}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Vision Engine Test ===")
    print("Scanning active window in 2 seconds...\n")
    time.sleep(2)

    elements = scan_ui_elements()
    print(f"\nFound {len(elements)} elements:\n")
    for e in elements:
        print(f"  [{e['type']:15}] '{e['text']}'  →  {e['center']}")

    print("\n" + "=" * 60)
    print(get_screen_summary())
