try:
    import pytesseract
except ImportError:
    pytesseract = None

from PIL import Image
import re
import os

# Common paths for Tesseract on Windows
TESSERACT_CMD_CANDIDATES = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    r'C:\Tesseract-OCR\tesseract.exe',
    r'C:\Users\Administrator\AppData\Local\Tesseract-OCR\tesseract.exe',
    os.path.expandvars(r'%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe'),
    os.path.expandvars(r'%APPDATA%\Tesseract-OCR\tesseract.exe'),
]

def setup_tesseract():
    """Try to find tesseract.exe if not in PATH"""
    if pytesseract is None:
        return False, "pytesseract library not installed"
        
    if os.name == 'nt':
        try:
            # Check if it's already in path
            pytesseract.get_tesseract_version()
            return True, "Found in PATH"
        except Exception:
            searched = []
            for path in TESSERACT_CMD_CANDIDATES:
                actual_path = os.path.expandvars(path)
                searched.append(actual_path)
                if os.path.exists(actual_path):
                    pytesseract.pytesseract.tesseract_cmd = actual_path
                    return True, f"Found at {actual_path}"
            return False, f"Not found in common paths: {', '.join(searched)}"
    return True, "Non-Windows system"

def extract_data_from_image(image):
    """
    Extract digital wellbeing data from a screenshot using OCR.
    """
    if pytesseract is None:
        return None, "The 'pytesseract' library is not installed. Please run 'pip install pytesseract Pillow' to enable OCR."
        
    ok, msg = setup_tesseract()
    if not ok:
        return None, f"Tesseract engine error: {msg}"

    try:
        # Perform OCR
        text = pytesseract.image_to_string(image)
        
        # Initialize results
        results = {
            'total_screen_time': 0.0,
            'notifications_per_day': 0,
            'phone_pickups_per_hour': 0,
            'raw_text': text
        }

        # 1. Extract Screen Time
        time_match = re.search(r'(\d+)\s*h\s*(\d+)\s*m', text, re.IGNORECASE)
        if not time_match:
            time_match = re.search(r'(\d+)\s*hr\s*(\d+)\s*min', text, re.IGNORECASE)
        
        if time_match:
            h, m = map(int, time_match.groups())
            results['total_screen_time'] = round(h + (m / 60.0), 2)
        else:
            colon_match = re.search(r'(\d+):(\d{2})', text)
            if colon_match:
                h, m = map(int, colon_match.groups())
                if h < 24:
                    results['total_screen_time'] = round(h + (m / 60.0), 2)

        # 2. Extract Notifications
        notif_match = re.search(r'(\d+)\s*notifications', text, re.IGNORECASE)
        if not notif_match:
            notif_match = re.search(r'notifications[:\s]*(\d+)', text, re.IGNORECASE)
        
        if notif_match:
            results['notifications_per_day'] = int(notif_match.group(1))

        # 3. Extract Unlocks/Pickups
        unlock_match = re.search(r'(\d+)\s*unlocks', text, re.IGNORECASE)
        if not unlock_match:
            unlock_match = re.search(r'unlocks[:\s]*(\d+)', text, re.IGNORECASE)
        
        if unlock_match:
            total_unlocks = int(unlock_match.group(1))
            results['phone_pickups_per_hour'] = round(total_unlocks / 16.0, 1)

        return results, None

    except Exception as e:
        return None, f"OCR Error: {str(e)}"

def build_profile_from_ocr(ocr_data):
    """
    Convert OCR results into a full phone_profile dictionary.
    """
    profile = {
        "total_screen_time":       ocr_data.get('total_screen_time', 0.0),
        "nighttime_usage":         round(ocr_data.get('total_screen_time', 0.0) * 0.2, 1),
        "notifications_per_day":   ocr_data.get('notifications_per_day', 0),
        "binge_sessions_per_week": 5,
        "fomo_score":              5.0,
        "anxiety_score":           5.0,
        "phone_pickups_per_hour":  ocr_data.get('phone_pickups_per_hour', 0.0),
        "sleep_disruption_score":  5.0,
        "sleep_hours":             7.0,
        "productivity_score":      5.0,
    }
    return profile
