# Waksense

Suite tout-en-un pour piloter vos instances Wakfu : détection automatique des personnages, overlays dédiés aux classes, inventaire unifié et automatisations in‑game (autofocus, raccourcis d’objets, etc.).

## 🎯 Objectifs
- Centraliser toutes vos fenêtres Wakfu, même en multi‑compte.
- Remonter les informations de combat (tour actif, états, inventaires) sans modifier les fichiers du jeu.
- Fournir des outils actionnables (overlay, keybinds, auto-focus)

## 🚀 Installation rapide
1. Téléchargez `Waksense.exe` depuis les releases.
2. Placez `Waksense.exe`, `inventory.dll`, `combatlog.dll` et `wakfujdi.dll` dans le même dossier.
3. Lancez l’exécutable (administrateur recommandé).
4. Au premier démarrage, pointez vers votre dossier de logs Wakfu si demandé.

## 🧰 Fonctionnalités principales

### Gestion multi-instances
- Scan automatique des `java.exe` Wakfu en cours.
- Attribution d’un **master** : un seul client pilote les hotkeys/globales pour éviter les conflits.
- Synchronisation via mémoire partagée (inventaires, commandes d’utilisation d’objet, état des personnages).

### Autofocus façon WinActivate
- Détection du début de tour via la timeline interne du client.
- Mise au premier plan de la fenêtre du personnage suivi (SwitchToThisWindow + AttachThreadInput + SetForegroundWindow).
- Cooldown anti-spam et verrouillage par mutex pour éviter les clignotements en multi-écrans.

### Overlay inventaire & états (F11)
- Vue consolidée de toutes les instances actives avec leurs inventaires et états/buffs.
- Sélection de personnage par simple clic, onglets **Inventaire** / **États**.
- Bouton **Use** pour lancer immédiatement un objet. Si le personnage est sur une autre instance, la commande lui est envoyée à distance.
- Fenêtre flottante repositionnable, transparente et persistante entre les sessions.

### Raccourcis d’objets personnalisés
- Cliquer sur la colonne **Bind** ouvre un mini-dialogue : choisissez la combinaison (Ctrl/Shift/Alt + touche principale, F1–F12 inclus).
- Sélectionnez les personnages autorisés (checkbox / bouton “Select All”).
- Appuyer sur le raccourci utilise l’objet pour chaque personnage admissible, même si son client est minimisé.
- Bouton ❌ pour retirer un bind, sauvegarde auto dans `%APPDATA%\Waksense`.

### Trackers de classes
- **Iop** : PA/PM/PW, combos, Charges, Étendard, Bond, Préparation/Courroux en temps réel.
- **Crâ** : Affûtage, Précision (avec détection d’Esprit Affûté), Balises, Tir précis.
- **Ouginak** : Rage, Proie, Meute, suivi des sorts principaux et alertes visuelles.
- Chaque module se lance depuis l’interface principale, possède sa propre configuration (positions, profils) et suit le personnage actif détecté.

### Journalisation & diagnostic
- Fichier principal : `C:\Users\<vous>\AppData\Local\Temp\wakfu-inventory.log`.
- Traces `[Reflection]` détaillant toutes les classes/méthodes tentées (utile après un patch Ankama).
- Filtres `[TurnDetect]`, `[Overlay]`, `[Hotkey]`, `[BreedDetect]` pour comprendre rapidement ce qui se passe.

## ⌨️ Raccourcis & interactions
- `F11` : afficher/masquer l’overlay inventaire (seulement sur l’instance master).
- `F12` : réservé pour de futures actions (actuellement sans effet volontaire).
- `END` : coupe proprement la DLL (mode débogage).
- `Bind` : cliquer sur la cellule pour ouvrir la fenêtre de capture, appuyer sur la combinaison souhaitée puis valider.
- `Use` : exécute l’objet immédiatement pour le personnage sélectionné.
- `Tabs Inventaire / États` : switcher entre sacs et effets actifs.
- `Molette` : faire défiler les items ; glisser la barre supérieure pour repositionner l’overlay.

## 🔄 Flux type
1. Lancer Waksense, puis vos clients Wakfu (peu importe l’ordre).
2. À l’injection (`inventory.dll`), la fenêtre active affiche le nom extrait du titre (`Nom - WAKFU`).
3. Dès qu’un combat est détecté, le tracker de classe s’affiche et les tours sont suivis.
4. À chaque début de tour d’un personnage suivi, sa fenêtre est automatiquement activée et l’overlay peut être utilisé pour lancer consommables/bindings.
5. Les logs et états sont rafraîchis en continu ; aucune action manuelle supplémentaire n’est requise.

## 📁 Fichiers utiles
- `wakfu-inventory.log` : journal temps réel.
- `%APPDATA%\Waksense\` : positions d’overlays, keybinds, préférences.
- `lock_states.json`, `positions_config.json` : exemples de profils pour les différents modules de classe.

## 🤝 Support

<div align="left">

[![Discord](https://img.shields.io/badge/Discord-Bellucci%231845-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/users/Bellucci#1845)

</div>

Besoin d’aide, envie de proposer une nouvelle classe ou de signaler un changement de nom obfusqué ? Contactez-moi sur Discord avec votre `wakfu-inventory.log`.

