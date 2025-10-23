# Changelog Waksense

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

## [1.0.0] - 2025-10-23

### ✨ Ajouté
- **Application principale** : Interface de détection des classes avec design moderne
- **Tracker Iop** : Suivi complet des ressources PA/PM/PW et buffs (Concentration, Courroux, Préparation)
- **Tracker Crâ** : Suivi complet des ressources PA/PM/PW et buffs (Concentration, Affûtage, Précision)
- **Système de combo Iop** : Suivi des combos avec animations et effets visuels
- **Timeline des sorts** : Historique des sorts lancés avec coûts en temps réel
- **Overlay de détection** : Interface compacte pour afficher les classes détectées
- **Sauvegarde persistante** : Paramètres et personnages sauvegardés automatiquement
- **Gestion des personnages** : Ajout/suppression de personnages avec boutons dédiés
- **Détection automatique** : Scan des logs Wakfu pour détecter les classes
- **Repositionnement** : Overlays repositionnables avec sauvegarde des positions

### 🔧 Amélioré
- **Interface utilisateur** : Design minimaliste et moderne avec animations fluides
- **Gradients animés** : Transitions de couleurs plus douces et naturelles
- **Barre de progression** : Chargement continu au lieu de sauts de pourcentage
- **Responsive design** : Interface adaptative pour différentes tailles d'écran
- **Performance** : Optimisations pour réduire la consommation de ressources

### 🐛 Corrigé
- **Détection Préparation** : Support des formats avec Concentration/Compulsion
- **Logique de précision Crâ** : Gestion correcte du talent "Esprit affûté" (limite à 200)
- **Coûts variables Iop** : Détection précise des procs Impétueux, Charge, Étendard de bravoure
- **Affichage des images** : Résolution des problèmes de chargement des icônes
- **Sauvegarde des paramètres** : Persistance des chemins de logs et préférences
- **Gestion des erreurs** : Amélioration de la robustesse face aux erreurs de logs

### 🎯 Fonctionnalités Spéciales
- **Détection de focus Wakfu** : Overlays masqués quand Wakfu n'est pas la fenêtre active
- **Coûts dynamiques** : Adaptation automatique des coûts selon les procs détectés
- **États visuels** : Indicateurs d'état actif/inactif pour les trackers
- **Collapse/Expand** : Possibilité de réduire l'overlay de détection
- **Suppression de personnages** : Boutons de suppression dans l'overlay de détection

### 📦 Technique
- **Exécutable standalone** : Version compilée sans dépendances externes
- **Structure modulaire** : Code organisé par classes (Iop/Crâ)
- **Gestion des ressources** : Intégration des images et icônes dans l'exécutable
- **Configuration PyInstaller** : Build optimisé pour la distribution
- **Gestion des chemins** : Support des chemins relatifs et absolus

### 🎮 Compatibilité
- **Wakfu** : Compatible avec la version actuelle du jeu
- **Windows** : Testé sur Windows 10/11
- **Logs** : Support des logs de chat Wakfu standard
- **Résolution** : Compatible avec différentes résolutions d'écran

### 📝 Documentation
- **README complet** : Guide d'installation et d'utilisation
- **Structure du projet** : Documentation de l'architecture
- **Dépannage** : Solutions aux problèmes courants
- **Changelog** : Historique détaillé des modifications
