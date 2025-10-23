# Waksense

**Waksense** est une application de suivi de ressources pour les classes Iop et Crâ dans le jeu Wakfu. L'application surveille les logs de combat en temps réel et affiche des overlays informatifs pour optimiser votre gameplay.

## 🎯 Fonctionnalités

### 🗡️ Tracker Iop
- **Suivi des ressources** : PA, PM, PW en temps réel
- **Compteurs de buffs** : Concentration, Courroux, Préparation
- **Timeline des sorts** : Historique des sorts lancés avec coûts
- **Système de combo** : Suivi des combos Iop avec animations
- **Détection intelligente** : Coûts variables selon les procs (Impétueux, Charge, etc.)

![Iopressources-ezgif com-speed (2) (2)](https://github.com/user-attachments/assets/9c7feb55-ee75-45e1-b894-2cd392925a2c)


### 🏹 Tracker Crâ
- **Suivi des ressources** : PA, PM, PW en temps réel
- **Compteurs de buffs** : Concentration, Affûtage, Précision
- **Timeline des sorts** : Historique des sorts lancés avec coûts
- **Logique de précision** : Gestion du talent "Esprit affûté" (limite à 200)
- **Détection de combat** : Affichage automatique en combat

## 🚀 Installation

### Version Standalone (Recommandée)
1. Téléchargez `Waksense.exe` depuis la section [Releases](../../releases)
2. Lancez l'exécutable
3. Sélectionnez le dossier de logs Wakfu lors du premier lancement
4. L'application détectera automatiquement vos personnages en combat

![2025-10-2318-18-16-ezgif com-video-to-gif-converter](https://github.com/user-attachments/assets/17a0bf2c-608e-45e3-9be6-cfd7a6e22468)

### Version Source
1. Clonez le dépôt
2. Installez les dépendances :
   ```bash
   pip install PyQt6 pywin32 psutil
   ```
3. Lancez `src/main.py`

## Utilisation

1. **Lancement** : Ouvrez `Waksense.exe`
2. **Configuration** : Sélectionnez le dossier de logs Wakfu
3. **Combat** : L'application détecte automatiquement vos personnages
4. **Overlay** : Cliquez sur les classes détectées pour lancer les trackers
5. **Personnalisation** : Les overlays sont repositionnables et sauvegardés

## 🔧 Configuration

### Chemins de Logs
- **Par défaut** : `%APPDATA%\zaap\gamesLogs\wakfu\logs\`
- **Personnalisé** : Sélectionnable via l'interface

### Sauvegarde
- **Paramètres** : Sauvegardés dans `%APPDATA%\Waksense\`
- **Personnages** : Liste des personnages suivis
- **Positions** : Positions des overlays

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Signaler des bugs
- Proposer des améliorations
- Ajouter de nouvelles fonctionnalités
- Améliorer la documentation




