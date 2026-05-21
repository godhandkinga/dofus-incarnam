import mss
import numpy as np
import cv2
import time
import math
import os

import win32gui
import win32api
import win32con
from pynput.keyboard import Controller

# Import de la détection de combat depuis claude_combat
from claude_combat import is_combat_active

# =========================
# CONFIG
# =========================
THRESHOLD_DIFF = 20
WINDOW_KEYWORD = "Release"

OFFSET_Y = 35

OUTPUT_DIR = "captures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Délai d'attente après un clic avant de vérifier si le combat s'est lancé
COMBAT_CHECK_DELAY = 3.0

# Zone d'exclusion en haut de la fenêtre (coordonnées relatives à la fenêtre)
# Toute infobulle dont le bord supérieur (y) est inférieur à cette valeur sera ignorée
# ⚠️ À calibrer — mettre la valeur Y en dessous de laquelle les infobulles sont valides
EXCLUDE_TOP_ZONE_HEIGHT = 0  # pixels depuis le haut de la fenêtre (0 = désactivé)

keyboard = Controller()

# =========================
# INPUT Z (PYNPUT — fonctionne pour cette touche)
# =========================
def press_z():
    keyboard.press('z')

def release_z():
    keyboard.release('z')

# =========================
# WINDOW
# =========================
def find_window():
    matches = []

    def callback(hwnd, _):
        title = win32gui.GetWindowText(hwnd)
        if title and WINDOW_KEYWORD.lower() in title.lower():
            matches.append(hwnd)

    win32gui.EnumWindows(callback, None)

    if not matches:
        print("❌ Fenêtre introuvable")
        return None

    hwnd = matches[0]
    print(f"✅ Fenêtre : {win32gui.GetWindowText(hwnd)}")
    return hwnd

def get_rect(hwnd):
    x1, y1, x2, y2 = win32gui.GetWindowRect(hwnd)
    return {
        "left": x1,
        "top": y1,
        "width": x2 - x1,
        "height": y2 - y1
    }

# =========================
# CAPTURE
# =========================
def capture(rect):
    with mss.MSS() as sct:
        img = np.array(sct.grab(rect))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

# =========================
# FILTRE INFOBULLES
# =========================
def is_infobulle(w, h):
    area = w * h
    return (
        85 <= w <= 140 and
        70 <= h <= 150 and
        6000 <= area <= 20000
    )

def is_in_excluded_zone(y):
    """Retourne True si l'infobulle est dans la zone exclue en haut de la fenêtre."""
    if EXCLUDE_TOP_ZONE_HEIGHT <= 0:
        return False
    return y < EXCLUDE_TOP_ZONE_HEIGHT

# =========================
# DETECTION
# =========================
def detect_infobulles(img_before, img_after):
    diff = cv2.absdiff(img_before, img_after)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(gray, THRESHOLD_DIFF, 255, cv2.THRESH_BINARY)

    kernel = np.ones((5, 5), np.uint8)
    thresh = cv2.dilate(thresh, kernel, iterations=2)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    infobulles = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if is_infobulle(w, h):
            if is_in_excluded_zone(y):
                print(f"  ⛔ Infobulle ignorée (zone exclue) : ({x}, {y}, {w}, {h})")
                continue
            infobulles.append((x, y, w, h))

    return infobulles

# =========================
# CIBLE
# =========================
def choose_closest(infobulles, shape, blacklist=None):
    """Retourne l'infobulle la plus proche du centre, en excluant les blacklistées."""
    if blacklist is None:
        blacklist = []

    h, w, _ = shape
    cx, cy = w // 2, h // 2

    best = None
    best_d = float("inf")

    for (x, y, w, h) in infobulles:
        if (x, y, w, h) in blacklist:
            continue
        mx = x + w // 2
        my = y + h // 2
        d = math.hypot(mx - cx, my - cy)
        if d < best_d:
            best_d = d
            best = (x, y, w, h)

    return best

# =========================
# CLIC
# =========================
def click_target(abs_x, abs_y):
    win32api.SetCursorPos((abs_x, abs_y))
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, abs_x, abs_y, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, abs_x, abs_y, 0, 0)
    print(f"🖱️ Clic effectué en ({abs_x}, {abs_y})")

# =========================
# DEBUG
# =========================
def draw_cross(img, x, y, size=15):
    cv2.line(img, (x-size, y-size), (x+size, y+size), (0,0,255), 2)
    cv2.line(img, (x-size, y+size), (x+size, y-size), (0,0,255), 2)

# =========================
# MAIN
# =========================
def run_detect():
    """Détecte un monstre et clique dessus.
    Si le clic ne déclenche pas de combat, blackliste l'infobulle et réessaie.

    Retourne :
      "combat_started" — un combat a été lancé avec succès
      "no_monsters"    — aucune infobulle détectée sur cette carte
      "combat_failed"  — infobulles trouvées mais aucun combat déclenché
    """
    print("\n🔎 Recherche fenêtre Release...")

    hwnd = find_window()
    if hwnd is None:
        return "no_monsters"

    rect = get_rect(hwnd)

    print("📸 Capture AVANT")
    img_before = capture(rect)

    print("⌨️ Z")
    press_z()
    time.sleep(0.3)

    print("📸 Capture APRES")
    img_after = capture(rect)
    release_z()

    cv2.imwrite(f"{OUTPUT_DIR}/before.png", img_before)
    cv2.imwrite(f"{OUTPUT_DIR}/after.png", img_after)

    print("🧠 Détection infobulles...")
    infobulles = detect_infobulles(img_before, img_after)

    debug = img_after.copy()
    for (x, y, w, h) in infobulles:
        cv2.rectangle(debug, (x, y), (x+w, y+h), (0, 255, 0), 2)

    if not infobulles:
        print("❌ Aucune infobulle détectée")
        cv2.imwrite(f"{OUTPUT_DIR}/result.png", debug)
        return "no_monsters"

    blacklist = []

    while True:
        best = choose_closest(infobulles, img_after.shape, blacklist)

        if best is None:
            print("❌ Toutes les infobulles ont été essayées sans succès")
            cv2.imwrite(f"{OUTPUT_DIR}/result.png", debug)
            return "combat_failed"

        x, y, w, h = best
        mx = x + w // 2
        my = y + h + OFFSET_Y

        print(f"🎯 Cible : ({mx}, {my})")
        draw_cross(debug, mx, my)

        abs_x = rect["left"] + mx
        abs_y = rect["top"] + my
        click_target(abs_x, abs_y)

        print(f"⏳ Vérification combat dans {COMBAT_CHECK_DELAY}s...")
        time.sleep(COMBAT_CHECK_DELAY)

        if is_combat_active():
            print("✅ Combat détecté — succès !")
            cv2.imwrite(f"{OUTPUT_DIR}/result.png", debug)
            return "combat_started"
        else:
            print(f"⚠️  Pas de combat détecté — infobulle ({x},{y},{w},{h}) blacklistée, on essaie la suivante")
            blacklist.append(best)
            cv2.rectangle(debug, (x, y), (x+w, y+h), (0, 0, 255), 2)


# =========================
# MAIN (exécution standalone)
# =========================
if __name__ == "__main__":
    run_detect()