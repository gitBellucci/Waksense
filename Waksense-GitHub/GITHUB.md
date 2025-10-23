# Configuration GitHub pour Waksense

## Dépôt principal
- **Nom** : `Waksense`
- **Description** : Application de suivi de ressources pour les classes Iop et Crâ dans Wakfu
- **Langage principal** : Python
- **Licence** : MIT

## Branches
- `main` : Code source principal
- `releases` : Exécutables compilés

## Releases
- **Tag** : `v1.0.0`
- **Titre** : `Waksense v1.0.0 - Première version stable`
- **Description** : Version initiale avec toutes les fonctionnalités

## Fichiers importants
- `README.md` : Documentation principale
- `CHANGELOG.md` : Historique des modifications
- `LICENSE` : Licence MIT
- `requirements.txt` : Dépendances Python
- `Waksense.spec` : Configuration PyInstaller

## Structure recommandée pour GitHub
```
Waksense/
├── README.md
├── CHANGELOG.md
├── LICENSE
├── requirements.txt
├── Waksense.spec
├── BUILD.md
├── src/
│   ├── main.py
│   └── classes/
│       ├── iop/
│       └── cra/
├── assets/
│   ├── images/
│   └── Waksense.ico
└── releases/
    └── Waksense.exe
```

## Instructions de publication
1. Créer le dépôt GitHub
2. Uploader tous les fichiers
3. Créer une release avec l'exécutable
4. Ajouter des tags appropriés
5. Configurer les descriptions et README
