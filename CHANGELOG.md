# Changelog Waksense

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

## [1.0.1] - 2025-10-29

### Ajouté
- Systeme de logos pour les combos Iop : Ajout d'icones visuelles pour chaque combo (combo1.png a combo5.png)
- Systeme de de-dedoublonnage des logs : Module LogDeduplicator pour gerer les instances multiples de Wakfu ecrivant dans le meme fichier de log
- Sauvegarde des positions dans AppData : Les positions des overlays sont maintenant sauvegardees dans %APPDATA%\Roaming\Waksense\ pour persister entre les executions
- Positions par defaut : Ajout de positions initiales pour les overlays Iop et Cra au lieu de (0, 0)
- Gestion des instances multiples : Utilisation de timestamps pour detecter et ignorer les lignes dupliquees dans les logs (fenetre de 100ms)

### Ameliore
- Design uniforme des barres de progression : Barres arrondies (border-radius: 12px) avec style minimaliste identique entre Iop et Cra
- Suppression des animations de bounce : Retire les animations de rebondissement pour reduire le desordre visuel
- Retrait des effets de glow : Suppression des effets de lueur pulsante sur les barres pour une interface plus propre
- Interface de detection : Overlay de detection avec icones de classes et systeme de collapse/expand
- Fermeture propre de l'application : Amelioration de la gestion de fermeture pour arreter tous les processus trackers
- Barres de progression personalisees : Rendu custom avec borders arrondis et textes outlines en blanc

### Corrige
- Combo repeatable dans le meme tour : Les combos peuvent maintenant etre relances plusieurs fois dans le meme tour (completed_combos_this_turn set)
- Gestion de la Preparation Iop : Systeme de detection de perte de preparation via confirmation de degats
- Consommation du Courroux : Suivi correct de la consommation du courroux apres utilisation
- Fermeture du overlay de detection : Le overlay de detection se ferme correctement a la fermeture de l'application
- Processus trackers orphelins : Tous les processus trackers sont maintenant correctement termines a la fermeture

### Technique
- Class ConcentrationProgressBar : Barre de progression custom avec animation de gradient fluide
- Class MinimalProgressBar : Barre de progression minimaliste pour Cra avec style personnalise
- Class ComboColumnWidget : Widget de colonne pour afficher les combos Iop avec icones
- Class ComboStepWidget : Widget pour chaque etape de combo avec animation de slide
- LogDeduplicator : Systeme de detection des doublons base sur les timestamps et le contenu
- Save paths conditionnels : Utilisation d'AppData pour executable, repertoire script pour developpement
- Force quit mechanism : QApplication.instance().quit() pour assurer la fermeture complete

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
