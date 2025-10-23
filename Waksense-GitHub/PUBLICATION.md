# Instructions pour la publication GitHub

## 🚀 Étapes de publication

### 1. Créer le dépôt GitHub
- Aller sur [GitHub.com](https://github.com)
- Cliquer sur "New repository"
- Nom : `Waksense`
- Description : `Application de suivi de ressources pour les classes Iop et Crâ dans Wakfu`
- Visibilité : Public
- Ne pas initialiser avec README (on a déjà nos fichiers)

### 2. Uploader les fichiers
```bash
# Cloner le dépôt (après création)
git clone https://github.com/VOTRE_USERNAME/Waksense.git
cd Waksense

# Copier tous les fichiers du dossier Waksense-GitHub
# Puis commiter
git add .
git commit -m "Initial commit - Waksense v1.0.0"
git push origin main
```

### 3. Créer une release
- Aller dans l'onglet "Releases"
- Cliquer sur "Create a new release"
- Tag : `v1.0.0`
- Titre : `Waksense v1.0.0 - Première version stable`
- Description : Copier le contenu de `RELEASE.md`
- Attacher `releases/Waksense.exe`
- Marquer comme "Latest release"

## 📁 Structure du dépôt

```
Waksense/
├── README.md              # Documentation principale
├── CHANGELOG.md          # Historique des modifications
├── LICENSE               # Licence MIT
├── requirements.txt      # Dépendances Python
├── Waksense.spec         # Configuration PyInstaller
├── BUILD.md              # Instructions de build
├── GITHUB.md             # Configuration GitHub
├── RELEASE.md            # Configuration des releases
├── build.bat             # Script de build Windows
├── build.ps1             # Script de build PowerShell
├── .gitignore            # Fichiers à ignorer
├── src/                  # Code source
│   ├── main.py          # Application principale
│   └── classes/         # Trackers par classe
│       ├── iop/         # Tracker Iop
│       └── cra/         # Tracker Crâ
├── assets/              # Ressources
│   ├── images/         # Images générales
│   └── Waksense.ico    # Icône de l'application
└── releases/           # Exécutables compilés
    └── Waksense.exe    # Version standalone
```

## 🎯 Points importants

### ✅ Avantages de cette structure
- **Professionnelle** : Structure claire et organisée
- **Maintenable** : Code modulaire et bien documenté
- **Distribuable** : Exécutable standalone inclus
- **Documentée** : README complet et changelog détaillé
- **Licenciée** : Licence MIT pour usage libre

### 🔧 Gestion des accents
- Le dossier "Crâ" a été renommé en "cra" pour éviter les problèmes d'encodage
- Tous les fichiers sont en UTF-8
- Les chemins sont gérés dynamiquement dans le code

### 📦 Distribution
- **Source** : Pour les développeurs qui veulent modifier
- **Exécutable** : Pour les utilisateurs finaux
- **Documentation** : Complète et en français
- **Scripts de build** : Automatisés pour faciliter la maintenance

## 🎮 Utilisation finale

Les utilisateurs pourront :
1. **Télécharger** l'exécutable depuis les releases
2. **Lancer** Waksense.exe directement
3. **Configurer** le chemin des logs Wakfu
4. **Utiliser** les trackers Iop et Crâ en combat
5. **Contribuer** au développement via GitHub

## 📝 Maintenance future

- **Nouvelles versions** : Mettre à jour le CHANGELOG.md
- **Bugs** : Utiliser l'onglet Issues de GitHub
- **Améliorations** : Proposer des Pull Requests
- **Documentation** : Maintenir le README.md à jour
