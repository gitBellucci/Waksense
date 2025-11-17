# Wakfu Mini-Game Bot

Un bot d'automatisation pour le mini-jeu de fouille dans Wakfu, optimisé pour collecter les Boissons de Frayeur.

## Structure du projet

```
foire_trool/
├── minimal_overlay.py          # Application principale
├── saved_sequence.json         # Séquence enregistrée du mini-jeu
├── start_bot.bat              # Script de lancement
├── README.md                  # Ce fichier
├── images/                    # Images de référence
│   ├── Screenshots.png        # PNJ (jour)
│   ├── Screenshots_nuit.png   # PNJ (nuit)
│   ├── dialogue1.png          # Dialogue 1 (jour)
│   ├── dialogue1_nuit.png     # Dialogue 1 (nuit)
│   ├── dialogue2.png          # Dialogue 2 (jour)
│   ├── dialogue2_nuit.png     # Dialogue 2 (nuit)
│   ├── porte.png              # Porte (jour)
│   ├── porte_nuit.png         # Porte (nuit)
│   ├── porte2.png             # Porte variant 2
│   ├── porte3.png             # Porte variant 3
│   ├── carré1.png             # Carré vert (jour)
│   ├── carré1_nuit.png        # Carré vert (nuit)
│   ├── creuser.png            # Bouton creuser (jour)
│   └── creuser_nuit.png       # Bouton creuser (nuit)
└── dependencies/
    └── requirements.txt        # Dépendances Python
```

## Fonctionnalités

- **Overlay minimaliste** : Interface compacte en haut à droite de Wakfu
- **Boucle automatique** : Cycle complet PNJ → Mini-jeu → Téléportation
- **Statistiques en temps réel** : Comptage des Boissons de Frayeur
- **Contrôle F12** : Toggle Start/Stop avec la touche F12
- **Séquence enregistrée** : Rejoue automatiquement vos clics dans le mini-jeu
- **Monitoring des logs** : Détection automatique des ressources collectées

## Installation et utilisation

1. **Lancer le bot** : Double-clic sur `start_bot.bat`
2. **Première utilisation** : Enregistrez votre séquence de clics dans le mini-jeu
3. **Démarrer** : Appuyez sur F12 ou cliquez sur ▶ F12
4. **Arrêter** : Appuyez sur F12 ou cliquez sur ⏹ F12

## Workflow automatique

### Phase de démarrage
1. Trouve le PNJ d'entrée
2. Lui parle (avec retry automatique)
3. Attend la perte de kamas (logs)
4. Ouvre la porte
5. Clique sur le dialogue final

### Mini-jeu (60 secondes)
- Joue automatiquement votre séquence enregistrée
- Collecte les ressources via monitoring des logs
- Affiche les statistiques en temps réel

### Fin et téléportation
- Attend 3 secondes après la perte de kamas
- Sauvegarde les statistiques de la run
- Relance automatiquement la boucle

## Statistiques

L'overlay affiche :
- **Boissons totales** : Nombre total depuis le début
- **Boissons/run** : Moyenne par run

## Contrôles

- **F12** : Toggle Start/Stop
- **Clic sur bouton** : Alternative au F12
- **Overlay** : Toujours visible au-dessus de Wakfu

## Dépendances

- Python 3.7+
- OpenCV
- CustomTkinter
- PyAutoGUI
- MSS
- Pynput
- Pillow
- NumPy
