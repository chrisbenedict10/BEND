"""
screen_reader.py — Visual Screen Reading Module for BEND AI

Provides reliable screen-level UI detection using:
  1. COLOR DETECTION — Finds buttons by their fill color (e.g. Spotify green)
  2. OCR TEXT DETECTION — Finds text/labels on screen via Tesseract (optional)
  3. PYWINAUTO ACCESSIBILITY — Accessibility-tree scanning as fallback

Key function:
  find_spotify_play_button() — Finds the green Spotify play button by color #1DB954
"""

import time
import pyautogui
import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Spotify's official brand green: #1DB954 = RGB(29, 185, 84)
SPOTIFY_GREEN = (29, 185, 84)

# How close a pixel color must be to the target (per channel, 0-255)
DEFAULT_TOLERANCE = 30

# Minimum number of matching pixels to be considered a real button
# (avoids false positives from tiny green elements)
MIN_BUTTON_PIXELS = 400
# ---------------------------------------------------------------------------


def _screenshot_to_array(region=None):
    """Take a screenshot and return a numpy uint8 array (H x W x 3 RGB)."""
    img = pyautogui.screenshot(region=region)  # region = (x, y, w, h) or None
    return np.array(img)


def find_color_on_screen(target_rgb, tolerance=DEFAULT_TOLERANCE, region=None,
                          min_pixels=MIN_BUTTON_PIXELS, avoid_bottom_px=150):
    """
    Scan the screen for a cluster of pixels matching `target_rgb`.
    Returns the (x, y) center of the largest matching cluster, or None.

    Args:
        target_rgb:     (R, G, B) tuple to search for.
        tolerance:      Per-channel allowance (30 = within ±30 of each channel).
        region:         (x, y, w, h) to limit the search area, or None for full screen.
        min_pixels:     Minimum cluster size to count as a real button.
        avoid_bottom_px: Ignore matches within this many pixels of the bottom edge
                         (to avoid the Spotify playback bar at the bottom).
    Returns:
        (x, y) absolute screen coordinates, or None if not found.
    """
    img = _screenshot_to_array(region=region)
    r, g, b = target_rgb

    # Build a boolean mask where all three channels are within tolerance
    mask = (
        (np.abs(img[:, :, 0].astype(np.int16) - r) <= tolerance) &
        (np.abs(img[:, :, 1].astype(np.int16) - g) <= tolerance) &
        (np.abs(img[:, :, 2].astype(np.int16) - b) <= tolerance)
    )

    # Ignore the bottom `avoid_bottom_px` rows (playback bar)
    h = img.shape[0]
    if avoid_bottom_px > 0:
        mask[h - avoid_bottom_px:, :] = False

    if not mask.any():
        return None

    ys, xs = np.where(mask)
    if len(xs) < min_pixels:
        print(f"⚠️  Color match found but too small ({len(xs)} px < {min_pixels} min). Ignoring.")
        return None

    cx = int(np.median(xs))
    cy = int(np.median(ys))

    # If region was provided, convert to absolute screen coordinates
    if region:
        cx += region[0]
        cy += region[1]

    print(f"🟢 Color cluster found: {len(xs)} pixels, center=({cx},{cy})")
    return cx, cy


def find_spotify_play_button(window_rect=None):
    """
    Specialist function: finds Spotify's green play button (#1DB954) on screen.

    Searches only the TOP 75% of the Spotify window (or full screen if window_rect
    is not given) to avoid the always-present bottom playback bar.

    Args:
        window_rect: (x, y, w, h) of the Spotify window, or None to search full screen.

    Returns:
        (x, y) absolute screen coordinates of the button center, or None.
    """
    print("🔍 Scanning for Spotify green play button (#1DB954)...")

    if window_rect:
        x, y, w, h = window_rect
        # Only scan the top 75% of the window (avoids the bottom player bar)
        search_region = (x, y, w, int(h * 0.75))
        result = find_color_on_screen(
            SPOTIFY_GREEN,
            tolerance=35,
            region=search_region,
            min_pixels=300,
            avoid_bottom_px=0  # Already limiting by region
        )
    else:
        # Full screen search, avoid bottom 150px
        result = find_color_on_screen(
            SPOTIFY_GREEN,
            tolerance=35,
            min_pixels=300,
            avoid_bottom_px=150
        )

    if result:
        print(f"✅ Spotify play button found at {result}")
    else:
        print("❌ Spotify green play button not found on screen.")
    return result


def click_color_button(target_rgb, tolerance=DEFAULT_TOLERANCE, region=None,
                        min_pixels=MIN_BUTTON_PIXELS, avoid_bottom_px=150):
    """
    Find a button by color and click it.
    Returns True on success, False if not found.
    """
    pos = find_color_on_screen(target_rgb, tolerance, region, min_pixels, avoid_bottom_px)
    if pos:
        x, y = pos
        print(f"🖱️  Clicking color button at ({x}, {y})...")
        pyautogui.moveTo(x, y, duration=0.4)
        time.sleep(0.3)
        pyautogui.click()
        return True
    return False


def click_spotify_play_button(window_rect=None):
    """
    Find and click Spotify's green play button.
    Returns True on success, False if not found.
    """
    pos = find_spotify_play_button(window_rect)
    if pos:
        x, y = pos
        print(f"🖱️  Clicking Spotify play button at ({x}, {y})...")
        pyautogui.moveTo(x, y, duration=0.4)
        time.sleep(0.3)
        pyautogui.click()
        return True
    return False


def find_text_on_screen(search_text, region=None):
    """
    OCR-based text finding (requires pytesseract + Tesseract binary).
    Falls back gracefully if tesseract is not installed.

    Returns (x, y) center of the text, or None.
    """
    try:
        import pytesseract
        img = pyautogui.screenshot(region=region)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        search_lower = search_text.lower()
        for i, word in enumerate(data["text"]):
            if search_lower in str(word).lower() and int(data["conf"][i]) > 50:
                x = data["left"][i] + data["width"][i] // 2
                y = data["top"][i] + data["height"][i] // 2
                if region:
                    x += region[0]
                    y += region[1]
                print(f"📝 OCR found '{word}' at ({x},{y}) conf={data['conf'][i]}")
                return x, y
    except ImportError:
        print("ℹ️  pytesseract not installed — OCR unavailable. Install with: pip install pytesseract")
    except Exception as e:
        print(f"⚠️  OCR error: {e}")
    return None


def scan_screen_summary(region=None):
    """
    Return a quick text summary of what colors and approximate button areas
    are visible on screen. Useful for debugging.
    """
    img = _screenshot_to_array(region=region)
    h, w, _ = img.shape
    summary = [f"Screen area: {w}x{h}"]

    # Check for Spotify green
    pos = find_spotify_play_button()
    if pos:
        summary.append(f"🟢 Spotify green button at {pos}")
    else:
        summary.append("🔴 No Spotify green button visible")

    return "\n".join(summary)


# ---------------------------------------------------------------------------
# Quick test
if __name__ == "__main__":
    print("=== Screen Reader Test ===")
    print("Taking screenshot and looking for Spotify green button...")
    time.sleep(2)  # Give you time to switch to Spotify
    result = find_spotify_play_button()
    if result:
        print(f"\n✅ Found at: {result}")
        ans = input("Click it? (y/n): ")
        if ans.lower() == "y":
            pyautogui.moveTo(result[0], result[1], duration=0.5)
            pyautogui.click()
    else:
        print("\n❌ Not found. Make sure Spotify is open with a search result showing.")
