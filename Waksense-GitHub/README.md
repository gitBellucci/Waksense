# Waksense

**Waksense** est une application de suivi de ressources pour les classes Iop et Crâ dans le jeu Wakfu. L'application surveille les logs de combat en temps réel et affiche des overlays informatifs pour optimiser votre gameplay.

## 🎯 Fonctionnalités

### 🗡️ Tracker Iop
- **Suivi des ressources** : PA, PM, PW en temps réel
- **Compteurs de buffs** : Concentration, Courroux, Préparation
- **Timeline des sorts** : Historique des sorts lancés avec coûts
- **Système de combo** : Suivi des combos Iop avec animations
- **Détection intelligente** : Coûts variables selon les procs (Impétueux, Charge, etc.)

### 🏹 Tracker Crâ
- **Suivi des ressources** : PA, PM, PW en temps réel
- **Compteurs de buffs** : Concentration, Affûtage, Précision
- **Timeline des sorts** : Historique des sorts lancés avec coûts
- **Logique de précision** : Gestion du talent "Esprit affûté" (limite à 200)
- **Détection de combat** : Affichage automatique en combat

### 🎮 Interface Principale
- **Détection automatique** : Scan des logs Wakfu
- **Overlay compact** : Affichage minimaliste des classes détectées
- **Sauvegarde persistante** : Paramètres et personnages sauvegardés
- **Gestion des personnages** : Ajout/suppression de personnages suivis
- **Design moderne** : Interface fluide avec animations

## 🚀 Installation

### Version Standalone (Recommandée)
1. Téléchargez `Waksense.exe` depuis la section [Releases](../../releases)
2. Lancez l'exécutable
3. Sélectionnez le dossier de logs Wakfu lors du premier lancement
4. L'application détectera automatiquement vos personnages en combat

### Version Source
1. Clonez le dépôt
2. Installez les dépendances :
   ```bash
   pip install PyQt6 pywin32 psutil
   ```
3. Lancez `src/main.py`

## 📁 Structure du Projet

```
Waksense/
├── src/                    # Code source
│   ├── main.py            # Application principale
│   └── classes/           # Trackers par classe
│       ├── iop/          # Tracker Iop
│       │   ├── tracker.py
│       │   └── *.png     # Icônes des sorts
│       └── cra/          # Tracker Crâ
│           ├── tracker.py
│           └── *.png     # Icônes des sorts
├── assets/                # Ressources
│   ├── images/           # Images générales
│   │   └── breeds/      # Icônes des classes
│   └── Waksense.ico     # Icône de l'application
└── releases/             # Exécutables compilés
    └── Waksense.exe     # Version standalone
```

## 🎮 Utilisation

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

## 🐛 Dépannage

### L'application ne détecte pas les logs
- Vérifiez que Wakfu génère bien des logs de chat
- Assurez-vous que le chemin vers les logs est correct
- Redémarrez l'application après avoir lancé Wakfu

### Les overlays ne s'affichent pas
- Vérifiez que vous êtes bien en combat
- Assurez-vous que Wakfu est la fenêtre active
- Redémarrez le tracker depuis l'overlay principal

### Problèmes de performance
- Fermez les autres applications gourmandes
- Vérifiez que les logs ne sont pas trop volumineux
- Redémarrez l'application si nécessaire

## 📝 Changelog

### Version Actuelle
- ✅ **Détection Préparation améliorée** : Support des formats avec Concentration/Compulsion
- ✅ **Interface modernisée** : Design minimaliste et fluide
- ✅ **Overlay de détection** : Affichage compact des classes avec gestion d'état
- ✅ **Sauvegarde persistante** : Paramètres et personnages sauvegardés automatiquement
- ✅ **Logique de précision Crâ** : Gestion intelligente du talent "Esprit affûté"
- ✅ **Coûts variables Iop** : Détection des procs Impétueux, Charge, Étendard de bravoure
- ✅ **Détection de focus** : Overlays masqués quand Wakfu n'est pas actif
- ✅ **Gestion des personnages** : Ajout/suppression avec boutons dédiés

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Signaler des bugs
- Proposer des améliorations
- Ajouter de nouvelles fonctionnalités
- Améliorer la documentation

## 🙏 Remerciements

- **Ankama Games** pour le jeu Wakfu
- **Communauté Wakfu** pour les retours et suggestions
