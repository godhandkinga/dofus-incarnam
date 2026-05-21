import mss
import numpy as np
import cv2
import time
import os
import win32api
import win32con

# =========================
# CONFIG CARTES
# =========================

# Nombre de cartes
MAP_COUNT = 7

# Séquence ping-pong : 1 2 3 4 5 6 7 6 5 4 3 2 1
def build_ping_pong_sequence(n):
    forward  = list(range(n))            # [0, 1, 2, 3, 4, 5, 6]
    backward = list(range(n - 2, 0, -1)) # [5, 4, 3, 2, 1]
    return forward + backward             # [0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1]

PING_PONG_SEQUENCE = build_ping_pong_sequence(MAP_COUNT)

# -------------------------------------------------------
# Région de l'écran à capturer pour la détection
# Doit correspondre exactement à COORDS_REGION dans calibrate_maps.py
# ⚠️ À calibrer avec get_coords.py
# -------------------------------------------------------
COORDS_REGION = {
    "left":   1,    # ⚠️ à calibrer
    "top":    88,    # ⚠️ à calibrer
    "width":  147,  # ⚠️ à calibrer
    "height": 20,   # ⚠️ à calibrer
}

# -------------------------------------------------------
# Dossier contenant les templates générés par calibrate_maps.py
# Fichiers attendus : map1.png, map2.png, ..., map7.png
# -------------------------------------------------------
TEMPLATES_DIR = "map_templates"

# Seuil de correspondance pour le template matching
# 0.8 = robuste, baisser à 0.7 si des cartes ne sont pas détectées
MAP_THRESHOLD = 0.80

# Nombre de tentatives si la détection échoue
DETECT_MAX_ATTEMPTS = 3
DETECT_RETRY_DELAY  = 0.4

# -------------------------------------------------------
# Coordonnées de changement de carte
# -------------------------------------------------------
MAP_NEXT_CLICK = ((1761, 486))  # ⚠️ à calibrer — clic pour avancer (→)
MAP_PREV_CLICK = (276, 457)  # ⚠️ à calibrer — clic pour reculer (←)

# Délai max pour attendre le chargement d'une nouvelle carte (secondes)
MAP_LOAD_TIMEOUT        = 30
MAP_LOAD_CHECK_INTERVAL = 0.5

# =========================
# CHARGEMENT TEMPLATES
# =========================
def _load_templates():
    """Charge les templates map1.png → map7.png depuis TEMPLATES_DIR."""
    templates = {}
    for i in range(MAP_COUNT):
        path = os.path.join(TEMPLATES_DIR, f"map{i + 1}.png")
        img = cv2.imread(path)
        if img is None:
            print(f"⚠️  Template manquant : {path} — lance calibrate_maps.py")
        else:
            templates[i] = img
    return templates

_TEMPLATES = {}

def _ensure_templates():
    global _TEMPLATES
    if not _TEMPLATES:
        _TEMPLATES = _load_templates()

# =========================
# ETAT INTERNE
# =========================
_sequence_index = 0

# =========================
# CAPTURE
# =========================
def _capture_region(region):
    with mss.MSS() as sct:
        img = np.array(sct.grab(region))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

# =========================
# DETECTION DE CARTE
# =========================
def detect_current_map():
    """
    Compare la capture actuelle de COORDS_REGION contre les templates
    de chaque carte. Retourne l'index (0-based) de la carte détectée,
    ou None si aucune ne dépasse le seuil.
    """
    _ensure_templates()

    screen = _capture_region(COORDS_REGION)
    sh, sw = screen.shape[:2]

    best_map   = None
    best_score = -1

    for map_idx, template in _TEMPLATES.items():
        th, tw = template.shape[:2]

        if sh < th or sw < tw:
            print(f"⚠️  Zone trop petite pour le template map{map_idx + 1}")
            continue

        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)

        print(f"  [map{map_idx + 1}] score={max_val:.3f} (seuil={MAP_THRESHOLD})")

        if max_val >= MAP_THRESHOLD and max_val > best_score:
            best_score = max_val
            best_map   = map_idx

    if best_map is not None:
        print(f"✅ Carte détectée : carte {best_map + 1} (score={best_score:.3f})")
    else:
        print("❌ Aucune carte reconnue")

    return best_map

# =========================
# CLIC
# =========================
def _click(x, y):
    win32api.SetCursorPos((x, y))
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
    print(f"  🖱️  Clic ({x}, {y})")

# =========================
# ATTENTE CHARGEMENT CARTE
# =========================
def wait_for_map(expected_map_idx):
    """
    Attend que la carte expected_map_idx soit confirmée par template matching.
    Retourne True si trouvée dans le délai, False si timeout.
    """
    print(f"⏳ Attente chargement carte {expected_map_idx + 1}...")
    start = time.time()

    while time.time() - start < MAP_LOAD_TIMEOUT:
        current = detect_current_map()
        if current == expected_map_idx:
            print(f"✅ Carte {expected_map_idx + 1} confirmée !")
            return True
        time.sleep(MAP_LOAD_CHECK_INTERVAL)

    print(f"⚠️  Timeout — carte {expected_map_idx + 1} non confirmée après {MAP_LOAD_TIMEOUT}s")
    return False

# =========================
# INITIALISATION
# =========================
def init_map_position():
    """
    Détecte la carte actuelle et positionne _sequence_index.
    À appeler une seule fois au démarrage du launcher.
    """
    global _sequence_index

    print("\n🗺️  Initialisation — détection carte de départ...")
    _ensure_templates()

    current_map = None
    for attempt in range(1, DETECT_MAX_ATTEMPTS + 1):
        current_map = detect_current_map()
        if current_map is not None:
            break
        print(f"  Tentative {attempt}/{DETECT_MAX_ATTEMPTS} échouée, retry dans {DETECT_RETRY_DELAY}s...")
        time.sleep(DETECT_RETRY_DELAY)

    if current_map is None:
        print("❌ Impossible de détecter la carte de départ.")
        print("   → Vérifie COORDS_REGION et relance calibrate_maps.py si besoin")
        return False

    for i, map_idx in enumerate(PING_PONG_SEQUENCE):
        if map_idx == current_map:
            _sequence_index = i
            print(f"📍 Position initiale : index séquence {i} (carte {current_map + 1})")
            return True

    print(f"❌ Carte {current_map + 1} absente de la séquence ping-pong.")
    return False

# =========================
# CHANGEMENT DE CARTE
# =========================
def go_to_next_map():
    """
    Avance dans la séquence ping-pong et effectue le changement de carte.
    Attend la confirmation visuelle du chargement.
    Retourne True si réussi, False sinon.
    """
    global _sequence_index

    current_map_idx = PING_PONG_SEQUENCE[_sequence_index]
    next_seq_index  = (_sequence_index + 1) % len(PING_PONG_SEQUENCE)
    next_map_idx    = PING_PONG_SEQUENCE[next_seq_index]

    direction = "→" if next_map_idx > current_map_idx else "←"
    print(f"\n🗺️  Changement : carte {current_map_idx + 1} {direction} carte {next_map_idx + 1}")

    if next_map_idx > current_map_idx:
        x, y = MAP_NEXT_CLICK
        print(f"  ➡️  Clic NEXT ({x}, {y})")
    else:
        x, y = MAP_PREV_CLICK
        print(f"  ⬅️  Clic PREV ({x}, {y})")

    _click(x, y)

    loaded = wait_for_map(next_map_idx)
    if loaded:
        _sequence_index = next_seq_index

    return loaded

# =========================
# GETTER ÉTAT
# =========================
def get_current_map_number():
    """Retourne le numéro de carte actuel (1-based) selon la séquence."""
    return PING_PONG_SEQUENCE[_sequence_index] + 1

# =========================
# MAIN (test standalone)
# =========================
if __name__ == "__main__":
    print("=" * 40)
    print("  🗺️  Test template matching cartes")
    print("=" * 40)
    print("⏳ Lancement dans 3 secondes...")
    time.sleep(3)

    _ensure_templates()
    print(f"\n📂 {len(_TEMPLATES)}/{MAP_COUNT} template(s) chargé(s)\n")

    result = detect_current_map()
    if result is not None:
        print(f"\n📍 Carte actuelle : {result + 1}")
    else:
        print("\n❌ Détection échouée")
        print("   → Vérifie COORDS_REGION et relance calibrate_maps.py")