import win32api
import time

print("=" * 40)
print("  🖱️  Coordonnées du curseur")
print("=" * 40)
print("Déplace ta souris sur la position voulue.")
print("Appuie sur CTRL gauche pour capturer.")
print("Appuie sur Échap pour quitter.\n")

VK_LCONTROL = 0x11
VK_ESCAPE   = 0x1B

captured = []

def is_pressed(vk):
    return win32api.GetAsyncKeyState(vk) & 0x8000 != 0

last_ctrl = False

while True:
    x, y = win32api.GetCursorPos()

    # Affichage en temps réel sur la même ligne
    print(f"\r  📍 Position actuelle : ({x:>5}, {y:>5})   ", end="", flush=True)

    ctrl_now = is_pressed(VK_LCONTROL)

    # Front montant : CTRL vient d'être pressé
    if ctrl_now and not last_ctrl:
        captured.append((x, y))
        print(f"\n  ✅ Capturé #{len(captured)} : ({x}, {y})")

    last_ctrl = ctrl_now

    if is_pressed(VK_ESCAPE):
        break

    time.sleep(0.05)

print("\n\n" + "=" * 40)
print("  📋 Récapitulatif des coordonnées capturées :")
print("=" * 40)
if captured:
    for i, (x, y) in enumerate(captured, 1):
        print(f"  #{i:>2} : ({x}, {y})")
else:
    print("  (aucune coordonnée capturée)")
print("=" * 40)
