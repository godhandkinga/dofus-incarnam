import time
from claude_detect import run_detect
from claude_combat import run_combat
from claude_map import init_map_position, go_to_next_map, get_current_map_number

# =========================
# CONFIG
# =========================
DELAY_AFTER_DETECT = 2.0   # secondes d'attente après détection avant de lancer le combat
DELAY_AFTER_COMBAT = 3.0   # secondes d'attente après combat avant de relancer la détection
MAX_LOOPS          = 0     # 0 = boucle infinie, sinon nombre de combats max

# Nombre de tentatives de détection sur une carte avant de la considérer vide
MAX_DETECT_ATTEMPTS = 3

# Délai entre deux tentatives de détection sur la même carte
DETECT_RETRY_DELAY = 2.0

# =========================
# BOUCLE PRINCIPALE
# =========================
def main():
    print("=" * 40)
    print("  🚀 LAUNCHER — Dofus Bot")
    print("=" * 40)
    print("Ctrl+C pour arrêter à tout moment.\n")

    # --- Initialisation position carte ---
    print("[INIT] 🗺️  Détection carte de départ...")
    if not init_map_position():
        print("❌ Impossible de détecter la carte initiale. Vérifiez vos templates map*.png et MAP_REGION.")
        return

    print(f"📍 Départ sur la carte {get_current_map_number()}")

    loop = 0

    try:
        while True:
            loop += 1
            print(f"\n{'='*40}")
            print(f"  🔄 Boucle #{loop} — Carte actuelle : {get_current_map_number()}")
            print(f"{'='*40}")

            # --- ÉTAPE 1 : Détection du monstre (avec retry) ---
            print("\n[1/2] 🔎 Détection monstre...")

            result = "no_monsters"
            for attempt in range(1, MAX_DETECT_ATTEMPTS + 1):
                print(f"  Tentative {attempt}/{MAX_DETECT_ATTEMPTS}...")
                result = run_detect()
                if result == "combat_started":
                    break
                if result == "combat_failed":
                    # Infobulles trouvées mais combat non lancé — on retente sur la même carte
                    print(f"  ⚠️  Combat non déclenché — nouvelle tentative dans {DETECT_RETRY_DELAY}s...")
                    time.sleep(DETECT_RETRY_DELAY)
                elif result == "no_monsters":
                    # Pas d'infobulles du tout — inutile de retenter, on change de carte
                    break

            if result != "combat_started":
                if result == "no_monsters":
                    print(f"\n🗺️  Aucun monstre sur la carte {get_current_map_number()} → changement de carte...")
                else:
                    print(f"\n🗺️  Combat non déclenché après {MAX_DETECT_ATTEMPTS} tentatives → changement de carte...")
                success = go_to_next_map()
                if not success:
                    print("⚠️  Changement de carte échoué — nouvelle tentative dans 5s...")
                    time.sleep(5)
                else:
                    print(f"✅ Maintenant sur la carte {get_current_map_number()}")
                continue

            # Délai pour laisser le combat s'ouvrir
            print(f"\n⏳ Attente {DELAY_AFTER_DETECT}s avant combat...")
            time.sleep(DELAY_AFTER_DETECT)

            # --- ÉTAPE 2 : Combat ---
            print("\n[2/2] ⚔️  Lancement du combat...")
            run_combat()

            # Délai avant de chercher un nouveau monstre
            print(f"\n⏳ Attente {DELAY_AFTER_COMBAT}s avant prochaine détection...")
            time.sleep(DELAY_AFTER_COMBAT)

            # Vérification du nombre max de boucles
            if MAX_LOOPS > 0 and loop >= MAX_LOOPS:
                print(f"\n✅ {MAX_LOOPS} combat(s) effectué(s), arrêt.")
                break

    except KeyboardInterrupt:
        print("\n\n🔴 Arrêt manuel (Ctrl+C)")

if __name__ == "__main__":
    print("⏳ Lancement dans 5 secondes — mets Dofus au premier plan...")
    time.sleep(5)
    main()