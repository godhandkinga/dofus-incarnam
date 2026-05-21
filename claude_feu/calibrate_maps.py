import mss
import numpy as np
import cv2
import time
import os

# =========================
# CONFIG — même région que dans claude_map.py
# ⚠️ Doit correspondre exactement à COORDS_REGION
# =========================
COORDS_REGION = {
    "left":   1,    # ⚠️ à calibrer
    "top":    88,    # ⚠️ à calibrer
    "width":  147,  # ⚠️ à calibrer
    "height": 20,   # ⚠️ à calibrer
}

OUTPUT_DIR = "map_templates"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# CAPTURE
# =========================
def capture():
    with mss.MSS() as sct:
        img = np.array(sct.grab(COORDS_REGION))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

# =========================
# MAIN
# =========================
def main():
    print("=" * 45)
    print("  📸  Calibration templates cartes")
    print("=" * 45)
    print(f"Les templates seront sauvegardés dans : {OUTPUT_DIR}/")
    print()
    print("Instructions :")
    print("  • Déplace ton personnage sur chaque carte")
    print("  • Appuie sur ENTRÉE pour capturer le template")
    print("  • Tape 'fin' pour terminer")
    print()

    carte = 1
    while True:
        input(f"  → Positionne-toi sur la carte {carte} puis appuie sur ENTRÉE...")

        img = capture()
        path = os.path.join(OUTPUT_DIR, f"map{carte}.png")
        cv2.imwrite(path, img)
        print(f"  ✅ Template carte {carte} sauvegardé : {path}")

        # Aperçu de ce qui a été capturé
        print(f"  📐 Taille : {img.shape[1]}x{img.shape[0]} px")
        print()

        carte += 1
        continuer = input("  Carte suivante ? (ENTRÉE pour oui / 'fin' pour terminer) : ").strip().lower()
        if continuer == "fin":
            break
        print()

    print()
    print("=" * 45)
    print(f"  ✅ {carte - 1} template(s) sauvegardé(s) dans {OUTPUT_DIR}/")
    print("  Copie ce dossier à côté de claude_map.py")
    print("=" * 45)

if __name__ == "__main__":
    print("⏳ Lancement dans 3 secondes — mets Dofus au premier plan...")
    time.sleep(3)
    main()
