import mss
import numpy as np
import cv2
import time
import win32api
import win32con
import pydirectinput

# =========================
# CONFIG — à calibrer
# =========================

FF_REGION = {
    "left":   1447,
    "top":    997,
    "width":  40,
    "height": 40
}

FF_TEMPLATE  = "ff.png"
FF_THRESHOLD = 0.8

TOUR_REGION = {
    "left":   1328,
    "top":    952,
    "width":  140,
    "height": 112
}

TOUR_TEMPLATE  = "tour.png"
TOUR_THRESHOLD = 0.8
TOUR_TIMEOUT   = 60

MONSTER_SLOT_X = 937  # ⚠️ à calibrer
MONSTER_SLOT_Y = 862  # ⚠️ à calibrer

DELAY_BETWEEN_CASTS = 1.0
DELAY_AFTER_F1      = 0.5

pydirectinput.PAUSE = 0.05

# =========================
# ACTIONS CLAVIER / SOURIS
# =========================
def press_key(key):
    pydirectinput.press(key)
    print(f"  ⌨️  {key}")

def click(x, y):
    win32api.SetCursorPos((x, y))
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,   x, y, 0, 0)
    print(f"  🖱️  Clic ({x}, {y})")

# =========================
# DETECTION
# =========================
def capture_region(region):
    with mss.MSS() as sct:
        img = np.array(sct.grab(region))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

def is_combat_active():
    template = cv2.imread(FF_TEMPLATE)
    if template is None:
        print(f"❌ Impossible de charger {FF_TEMPLATE}")
        return False
    screen = capture_region(FF_REGION)
    th, tw = template.shape[:2]
    sh, sw = screen.shape[:2]
    if sh < th or sw < tw:
        print(f"⚠️  [ff.png] Zone ({sw}x{sh}) plus petite que le template ({tw}x{th})")
        return False
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    print(f"  [ff.png] score={max_val:.2f} (seuil={FF_THRESHOLD})")
    return max_val >= FF_THRESHOLD

def is_my_turn():
    template = cv2.imread(TOUR_TEMPLATE)
    if template is None:
        print(f"❌ Impossible de charger {TOUR_TEMPLATE}")
        return False
    screen = capture_region(TOUR_REGION)
    th, tw = template.shape[:2]
    sh, sw = screen.shape[:2]
    if sh < th or sw < tw:
        print(f"⚠️  [tour.png] Zone ({sw}x{sh}) plus petite que le template ({tw}x{th})")
        return False
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    print(f"  [tour.png] score={max_val:.2f} (seuil={TOUR_THRESHOLD})")
    return max_val >= TOUR_THRESHOLD

def wait_for_turn():
    print("\n⏳ En attente du tour du joueur...")
    start = time.time()
    while not is_my_turn():
        if time.time() - start > TOUR_TIMEOUT:
            print("⚠️  Timeout — tour non détecté après 60s, on continue quand même.")
            return
        time.sleep(0.5)
    print("✅ C'est notre tour !")

# =========================
# COMBAT
# =========================
def run_combat():
    """Lance le combat et retourne True si terminé normalement, False si aucun combat détecté."""
    print("\n⚔️  Début du script de combat")

    print("🔍 Vérification combat actif...")
    if not is_combat_active():
        print("❌ Aucun combat détecté, abandon.")
        return False

    print("\n📌 Se mettre prêt (F1)")
    press_key('f1')
    time.sleep(DELAY_AFTER_F1)

    print("📌 Sélection sort (1)")
    press_key('1')
    time.sleep(0.3)

    while is_combat_active():

        print("\n🎯 3 lancers de sort...")
        for i in range(3):
            print(f"  Lancer {i + 1}/3")
            press_key('1')
            time.sleep(0.1)
            click(MONSTER_SLOT_X, MONSTER_SLOT_Y)
            time.sleep(DELAY_BETWEEN_CASTS)

        if not is_combat_active():
            break

        print("\n⏭️  Combat toujours actif → F1 (passer le tour)")
        press_key('f1')
        time.sleep(DELAY_AFTER_F1)

        wait_for_turn()

    print("\n🏆 Combat terminé !")

    # Fermer le menu de victoire
    time.sleep(1.0)
    press_key('escape')
    print("  🚪 Menu de victoire fermé (Échap)")
    return True

# =========================
# MAIN (exécution standalone)
# =========================
if __name__ == "__main__":
    print("⏳ Lancement dans 3 secondes...")
    time.sleep(3)
    run_combat()