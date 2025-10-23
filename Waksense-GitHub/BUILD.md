# Configuration de build pour Waksense

## Commandes de build

### Build complet
```bash
pyinstaller --clean Waksense.spec
```

### Build de développement (avec console)
```bash
pyinstaller --clean --console Waksense.spec
```

### Build optimisé (sans UPX)
```bash
pyinstaller --clean --noupx Waksense.spec
```

## Structure des fichiers

- `src/main.py` : Point d'entrée principal
- `src/classes/iop/tracker.py` : Tracker Iop
- `src/classes/cra/tracker.py` : Tracker Crâ
- `assets/` : Ressources (images, icônes)
- `releases/` : Exécutables compilés

## Vérifications pré-build

1. ✅ Tous les fichiers source sont présents
2. ✅ Toutes les images sont dans les bons dossiers
3. ✅ Le fichier spec est à jour
4. ✅ Les dépendances sont installées

## Post-build

1. Tester l'exécutable généré
2. Vérifier que toutes les ressources sont incluses
3. Copier dans le dossier releases/
4. Créer une release GitHub
