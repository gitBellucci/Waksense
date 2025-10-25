# Waksense

**Waksense** est une application de suivi de ressources dans le jeu Wakfu. L'application surveille les logs de votre chat et affiche des overlays informatifs pour optimiser votre gameplay.

## 📞 Contact

<div align="left">

[![Discord](https://img.shields.io/badge/Discord-Bellucci%231845-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/users/Bellucci#1845)


</div>

</div>

</div>

</div>

</div>

</div>

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
3. Lancez `wakfu_class_launcher.py`


## Fonctionnalités

### Tracker Iop
- **Suivi des ressources** : PA, PM, PW en temps réel
- **Compteurs de buffs** : Concentration, Courroux, Préparation
- **Timeline des sorts** : Historique des sorts lancés avec coûts
- **Système de combo** : Suivi des combos Iop avec animations

![Iopressources-ezgif com-speed (2) (2)](https://github.com/user-attachments/assets/9c7feb55-ee75-45e1-b894-2cd392925a2c)

# Gestion des Sorts Spéciaux Iop - Charge, Étendard, Bond avec Talents

## Vue d'ensemble

Le tracker Iop gère intelligemment les sorts avec des mécaniques de coût variables basées sur les talents et les conditions de jeu. Ces sorts nécessitent une analyse en deux étapes : **détection initiale du sort**, puis **ajustement du coût** selon les informations supplémentaires.

## Charge - Coût basé sur la distance

### Mécanisme de détection
```python
# Détection initiale
if spell_name == "Charge":
    self.last_charge_cast = True
    self.spell_cost_map["Charge"] = "1 PA"  # Coût par défaut
    # Affichage immédiat à 1PA dans la timeline
```

### Ajustement selon la distance
Le tracker surveille la ligne suivante pour déterminer la distance parcourue :

- **1 case** : `"Se rapproche de 1 case"` → **2 PA**
- **2 cases** : `"Se rapproche de 2 cases"` → **3 PA**
- **Distance par défaut** : **1 PA** (si aucune info de distance)

### Logique d'implémentation
```python
if self.last_charge_cast and "[Information (combat)]" in line:
    if "Se rapproche de 1 case" in line:
        self.timeline_entries[-1]['cost'] = "2PA"
        self.spell_cost_map["Charge"] = "2 PA"
    elif "Se rapproche de 2 cases" in line:
        self.timeline_entries[-1]['cost'] = "3PA"
        self.spell_cost_map["Charge"] = "3 PA"
```

![2025-10-2318-49-07-ezgif com-speed (1)](https://github.com/user-attachments/assets/3cdce712-cff2-4a08-bcf7-8fc8b8424811)

# Guide du Tracker Crâ - Système de Gestion des Ressources

## 📋 Vue d'ensemble

Suivi de l'**Affûtage**, la **Précision**, les **Pointes affûtées**, les **Balises affûtées** et le buff **Tir précis**.

![2025-10-2320-47-03-ezgif com-crop (1)](https://github.com/user-attachments/assets/ef3ca2ac-5f00-4dd5-a13d-b97f4f444a35)

## Système de Détection

#### 📊 Passif "Esprit Affûté"
```python
# Détection automatique du passif qui limite la Précision à 200
if "Valeur maximale de Précision atteinte !" in line and self.precision > 200:
    if not self._was_recent_300_gain():
        # Talent détecté - limite à 200
        self.precision = 200
        self.precision_bar.setMaxValue(200)
        self.has_esprit_affute = True
```

**Logique de détection :**
- ✅ **Détecte** : Message "Valeur maximale de Précision atteinte !" + Précision > 200
- ✅ **Exclut** : Les gains normaux de +300 Précision
- ✅ **Adapte** : La barre de Précision passe automatiquement de 300 à 200 max

### Détection des Tours

#### 🔄 Système de Visibilité Basé sur les Tours
```python
# Détection du tour du Crâ
if is_cra_spell and caster_name == self.tracked_player_name:
    self.is_cra_turn = True
    self.overlay_visible = True

# Fin de tour détectée
if "secondes reportées pour le tour suivant" in line:
    if turn_owner == self.tracked_player_name:
        self.overlay_visible = False
```

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

























