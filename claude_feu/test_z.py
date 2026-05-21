import time
import pydirectinput

pydirectinput.PAUSE = 0.05

print("⏳ Lancement dans 3 secondes — mets le jeu au premier plan...")
time.sleep(3)

print("🟢 Appui sur Z maintenu pendant 1 seconde...")
pydirectinput.keyDown('z')
time.sleep(1.0)
pydirectinput.keyUp('z')
print("✅ Z relâché")

time.sleep(1)

print("🟢 Test press simple Z...")
pydirectinput.press('z')
print("✅ Z pressé")