# Waksense

Suite tout-en-un pour piloter vos instances Wakfu : détection automatique des personnages, overlays dédiés aux classes, inventaire unifié et automatisations in‑game (autofocus, raccourcis d’objets, etc.).

## ⭐ Fonctionnalités phares

### 🎯 Autofocus intelligent
**Activation automatique de la fenêtre au début du tour** — Plus besoin de chercher manuellement quelle fenêtre Wakfu est active ! Dès que c'est le tour de votre personnage, sa fenêtre passe automatiquement au premier plan, même si une autre application est ouverte. Comportement identique à `WinActivate` d'AutoHotkey.

### 🎮 Multi-usage de consommables
**Un seul raccourci pour plusieurs personnages** — Créez un keybind (ex: `Ctrl+F1`) et sélectionnez les personnages concernés. Un simple appui sur le raccourci utilise l'objet **simultanément** sur tous les personnages sélectionnés, même si leurs fenêtres sont minimisées ou sur d'autres instances. Idéal pour le multi-compte !

## 🎯 Objectifs
- Centraliser toutes vos fenêtres Wakfu, même en multi‑compte.
- Remonter les informations de combat (tour actif, états, inventaires) sans modifier les fichiers du jeu.
- Fournir des outils actionnables (overlay, keybinds, auto-focus) avec un comportement identique à **WinActivate**.

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

### ⭐ Autofocus intelligent (comme WinActivate d'AutoHotkey)
**Fonctionnalité phare** : Activation automatique de la fenêtre au début du tour de votre personnage.

- **Détection précise** : Analyse de la timeline interne du client pour identifier le début de tour (pas de polling continu).
- **Comportement identique à WinActivate** : Utilise `SwitchToThisWindow`, `AttachThreadInput`, `SetForegroundWindow` et `SetWindowPos` pour garantir que la fenêtre passe au premier plan, même si une autre application est active.
- **Multi-instances** : Fonctionne parfaitement avec plusieurs clients Wakfu ouverts simultanément, chaque instance gérant son propre autofocus.
- **Protection anti-spam** : Cooldown de 2 secondes et verrouillage par mutex pour éviter les clignotements en multi-écrans.
- **Activation uniquement au début de tour** : L'autofocus ne se déclenche que lorsque c'est vraiment le tour de votre personnage, pas en boucle pendant tout le tour.

**Exemple d'usage** : Vous avez 3 personnages en combat. Dès que c'est le tour de "Bellux", sa fenêtre Wakfu s'active automatiquement et passe au premier plan, vous permettant d'agir immédiatement sans chercher la bonne fenêtre.

### Overlay inventaire & états (F11)
- Vue consolidée de toutes les instances actives avec leurs inventaires et états/buffs.
- Sélection de personnage par simple clic, onglets **Inventaire** / **États**.
- Bouton **Use** pour lancer immédiatement un objet. Si le personnage est sur une autre instance, la commande lui est envoyée à distance.
- Fenêtre flottante repositionnable, transparente et persistante entre les sessions.

### ⭐ Multi-usage de consommables avec un seul raccourci
**Fonctionnalité phare** : Utilisez un seul raccourci clavier pour consommer un objet sur plusieurs personnages simultanément.

- **Configuration simple** : Cliquez sur la colonne **Bind** d'un objet dans l'overlay, choisissez votre combinaison (Ctrl/Shift/Alt + touche principale, F1–F12 inclus).
- **Sélection multi-personnages** : Une fenêtre de sélection apparaît avec tous vos personnages détectés. Cochez ceux qui doivent utiliser l'objet, ou utilisez "Select All" pour tous les sélectionner d'un coup.
- **Exécution simultanée** : Appuyez sur votre raccourci → l'objet est utilisé **en même temps** sur tous les personnages sélectionnés, même si leurs fenêtres sont minimisées ou sur d'autres instances.
- **Fonctionnement cross-instance** : Si un personnage est sur une autre instance Wakfu, la commande lui est envoyée automatiquement via la mémoire partagée.
- **Gestion flexible** : Vous pouvez avoir plusieurs keybinds différents pour le même objet (ex: `Ctrl+1` pour 2 personnages, `Ctrl+2` pour 3 autres). Chaque bind est indépendant.
- **Sauvegarde automatique** : Tous vos raccourcis sont sauvegardés dans `%APPDATA%\Waksense` et persistent entre les sessions.

**Exemple concret** : Vous avez 4 personnages en combat. Vous créez un bind `Ctrl+F1` pour "Potion de soin" et sélectionnez "Bellux", "Tuque" et "Narashima". Pendant le combat, un simple `Ctrl+F1` soigne les 3 personnages en même temps, même si leurs fenêtres sont en arrière-plan ou minimisées. Gain de temps énorme en multi-compte !

**Bouton ❌** : Cliquez sur la croix à côté d'un bind pour le supprimer instantanément.

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

