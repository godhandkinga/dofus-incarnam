import mss
import numpy as np
import cv2
import time

# =========================
# CONFIG CARTES
# =========================

# Nombre de cartes
MAP_COUNT = 7

# Séquence ping-pong : 1 2 3 4 5 6 7 6 5 4 3 2 1 (indices 0-based en interne : 0 1 2 3 4 5 6 5 4 3 2 1 0)
# Générée automatiquement selon MAP_COUNT
def build_ping_pong_sequence(n):
    forward = list(range(n))           # [0, 1, 2, 3, 4, 5, 6]
    backward = list(range(n-2, 0, -1)) # [5, 4, 3, 2, 1]
    return forward + backward           # [0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1]

PING_PONG_SEQUENCE = build_ping_pong_sequence(MAP_COUNT)
# Résultat : [0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1] → boucle infinie sur cette séquence

# -------------------------------------------------------
# Templates : une image par carte pour identifier où on est
# Placez ces fichiers .png dans le même dossier que le script
# -------------------------------------------------------
MAP_TEMPLATES = {
    0: "map1.png",
    1: "map2.png",
    2: "map3.png",
    3: "map4.png",
    4: "map5.png",
    5: "map6.png",
    6: "map7.png",
}

# Seuil de correspondance pour identifier la carte
MAP_THRESHOLD = 0.40

# Zone de l'écran où chercher le template de carte (à calibrer)
# Choisissez une zone stable et unique à chaque carte (ex: minimap, nom de zone, décor)
MAP_REGION = {
    "left":   5,     # ⚠️ à calibrer
    "top":    60,     # ⚠️ à calibrer
    "width":  320,   # ⚠️ à calibrer
    "height": 100,   # ⚠️ à calibrer
}

# -------------------------------------------------------
# Coordonnées de changement de carte
# -------------------------------------------------------

# Clic pour avancer d'une carte (incrémentation : carte N → N+1)
# Même coordonnée pour tous les passages "vers la droite"
MAP_NEXT_CLICK = (1640, 489)   # ⚠️ à calibrer — ex: flèche droite de la carte

# Clic pour reculer d'une carte (décrémentation : carte N → N-1)
# Même coordonnée pour tous les passages "vers la gauche"
MAP_PREV_CLICK = (289, 516)   # ⚠️ à calibrer — ex: flèche gauche de la carte

# Délai max pour attendre le chargement d'une nouvelle carte (secondes)
MAP_LOAD_TIMEOUT = 10

# Délai entre chaque vérification du chargement
MAP_LOAD_CHECK_INTERVAL = 0.5

# =========================
# ETAT INTERNE
# =========================
# Index dans PING_PONG_SEQUENCE (pas l'index de carte directement)
_sequence_index = 0

# =========================
# CAPTURE
# =========================
def _capture_map_region():
    with mss.MSS() as sct:
        img = np.array(sct.grab(MAP_REGION))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

# =========================
# DETECTION DE CARTE
# =========================
def detect_current_map():
    """
    Analyse la région MAP_REGION et retourne l'index (0-based) de la carte détectée.
    Retourne None si aucune carte n'est reconnue.
    """
    screen = _capture_map_region()

    best_map = None
    best_score = -1

    for map_idx, template_path in MAP_TEMPLATES.items():
        template = cv2.imread(template_path)
        if template is None:
            print(f"⚠️  Template introuvable : {template_path}")
            continue

        th, tw = template.shape[:2]
        sh, sw = screen.shape[:2]

        if sh < th or sw < tw:
            print(f"⚠️  Zone trop petite pour {template_path}")
            continue

        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)

        print(f"  [map{map_idx+1}] score={max_val:.2f}")

        if max_val >= MAP_THRESHOLD and max_val > best_score:
            best_score = max_val
            best_map = map_idx

    if best_map is not None:
        print(f"✅ Carte détectée : carte {best_map + 1} (score={best_score:.2f})")
    else:
        print("❌ Aucune carte reconnue")

    return best_map

# =========================
# CLIC
# =========================
import win32api
import win32con

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
    Attend que la carte expected_map_idx soit chargée (template matching).
    Retourne True si trouvée dans le délai, False si timeout.
    """
    print(f"⏳ Attente chargement carte {expected_map_idx + 1}...")
    start = time.time()

    while time.time() - start < MAP_LOAD_TIMEOUT:
        current = detect_current_map()
        if current == expected_map_idx:
            print(f"✅ Carte {expected_map_idx + 1} chargée !")
            return True
        time.sleep(MAP_LOAD_CHECK_INTERVAL)

    print(f"⚠️  Timeout — carte {expected_map_idx + 1} non confirmée après {MAP_LOAD_TIMEOUT}s")
    return False

# =========================
# INITIALISATION
# =========================
def init_map_position():
    """
    Détecte la carte actuelle et positionne _sequence_index en conséquence.
    À appeler une seule fois au démarrage du launcher.
    Retourne True si la carte est reconnue, False sinon.
    """
    global _sequence_index

    print("\n🗺️  Initialisation — détection de la carte de départ...")
    current_map = detect_current_map()

    if current_map is None:
        print("❌ Impossible de détecter la carte de départ.")
        return False

    # Cherche la première occurrence de cette carte dans la séquence ping-pong
    for i, map_idx in enumerate(PING_PONG_SEQUENCE):
        if map_idx == current_map:
            _sequence_index = i
            print(f"📍 Position initiale dans la séquence : index {i} (carte {current_map + 1})")
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
    Retourne True si le changement a réussi, False sinon.
    """
    global _sequence_index

    current_map_idx = PING_PONG_SEQUENCE[_sequence_index]
    next_seq_index  = (_sequence_index + 1) % len(PING_PONG_SEQUENCE)
    next_map_idx    = PING_PONG_SEQUENCE[next_seq_index]

    direction = "→" if next_map_idx > current_map_idx else "←"
    print(f"\n🗺️  Changement de carte : {current_map_idx + 1} {direction} {next_map_idx + 1}")

    if next_map_idx > current_map_idx:
        # Incrémentation → clic "suivant"
        x, y = MAP_NEXT_CLICK
        print(f"  ➡️  Clic NEXT ({x}, {y})")
    else:
        # Décrémentation → clic "précédent"
        x, y = MAP_PREV_CLICK
        print(f"  ⬅️  Clic PREV ({x}, {y})")

    _click(x, y)

    # Attente confirmation visuelle
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
    print("⏳ Test claude_map.py dans 3 secondes...")
    time.sleep(3)

    if init_map_position():
        print(f"\n📍 Carte actuelle : {get_current_map_number()}")
        print("\n🔄 Test changement de carte...")
        go_to_next_map()
        print(f"📍 Nouvelle carte : {get_current_map_number()}")
    else:
        print("❌ Initialisation échouée")