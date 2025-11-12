# Intégration Aldes pour Home Assistant

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![GitHub release](https://img.shields.io/github/v/release/saniho/homeassistant-aldes)](https://github.com/saniho/homeassistant-aldes/releases/latest)

Cette intégration permet de piloter votre système de chauffage et de rafraîchissement Aldes depuis Home Assistant.

## Avertissement

Cette intégration est un projet communautaire et n'est ni développée ni soutenue officiellement par Aldes. Son utilisation se fait à vos propres risques. L'auteur ne saurait être tenu responsable de tout dysfonctionnement ou dommage résultant de son usage.

## Prérequis

- Une installation fonctionnelle de Home Assistant.
- Un système Aldes compatible (par exemple, T.One® AquaAir).
- Vos identifiants pour l'application AldesConnect®.

## Installation

### Méthode 1 : HACS (Recommandé)

1.  Si ce n'est pas déjà fait, installez [HACS](https://hacs.xyz/).
2.  Dans HACS, allez dans **Intégrations**.
3.  Cliquez sur les trois points en haut à droite et sélectionnez **"Dépôts personnalisés"**.
4.  Collez l'URL de ce dépôt (`https://github.com/saniho/homeassistant-aldes`) dans le champ "Dépôt".
5.  Sélectionnez la catégorie **"Intégration"**.
6.  Cliquez sur **"Ajouter"**, puis trouvez et installez l'intégration Aldes.
7.  Redémarrez Home Assistant pour finaliser l'installation.

### Méthode 2 : Manuelle

1.  Téléchargez la dernière version depuis la page [Releases](https://github.com/saniho/homeassistant-aldes/releases/latest).
2.  Copiez le dossier `custom_components/aldes` dans le dossier `custom_components` de votre Home Assistant.
3.  Redémarrez Home Assistant.

## Configuration

1.  Allez dans **Paramètres > Appareils et services**.
2.  Cliquez sur **"Ajouter une intégration"** et recherchez **"Aldes"**.
3.  Suivez les instructions à l'écran pour entrer vos identifiants Aldes (email et mot de passe).

## Entités créées

L'intégration crée un appareil Aldes qui regroupe les entités suivantes :

- **Climate** : Une entité par zone/thermostat pour contrôler la température et le mode (ex: `climate.salon`).
- **Sensor** :
    - Température principale du système (`sensor.aldes_main_temperature`).
    - Quantité d'eau chaude sanitaire (`sensor.aldes_hot_water_quantity`).
    - Mode de fonctionnement de l'air (`sensor.aldes_air_mode`).
- **Binary Sensor** :
    - État de la connexion au cloud Aldes (`binary_sensor.aldes_connectivity`).
    - Indicateur du mode vacances (`binary_sensor.aldes_vacation_mode`).
    - Indicateur du mode hors gel (`binary_sensor.aldes_away_mode`).
- **Switch** :
    - Interrupteur pour le mode vacances (`switch.aldes_vacation_mode`). **(Bêta)**
    - Interrupteur pour le mode hors gel (`switch.aldes_away_mode`). **(Bêta)**

## Services

### Service `aldes.set_vacation_dates`

Ce service permet de programmer une période de vacances.

- **Paramètres :**
    - `device_id`: (Obligatoire) Votre appareil Aldes.
    - `start_date`: (Optionnel) Date de début des vacances (`YYYY-MM-DD HH:MM:SS`).
    - `end_date`: (Optionnel) Date de fin des vacances (`YYYY-MM-DD HH:MM:SS`).

- **Exemple :**
    ```yaml
    service: aldes.set_vacation_dates
    data:
      device_id: VOTRE_DEVICE_ID
      start_date: "2024-12-20 08:00:00"
      end_date: "2024-12-27 18:00:00"
    ```

- **Pour annuler**, appelez le service sans les dates de début et de fin.

## Dépannage

Si vous rencontrez des problèmes :
1.  Vérifiez que vos identifiants sont corrects et fonctionnent dans l'application officielle.
2.  Consultez les journaux de Home Assistant (**Paramètres > Système > Journaux**).

Pour obtenir des logs plus détaillés, ajoutez ceci à votre fichier `configuration.yaml` :

```yaml
logger:
  default: info
  logs:
    custom_components.aldes: debug
```

## <details><summary>Informations pour les développeurs</summary>

### Données API avancées : Le planning hebdomadaire

L'API Aldes expose les données du planning hebdomadaire via les clés `week_planning` et `week_planning4`. Ces données sont une liste de commandes qui définissent le mode de fonctionnement pour chaque heure de la semaine.

**Structure des commandes**

Chaque commande a un format de 3 caractères, par exemple `71B` :
- **Premier caractère (`7`)** : Jour de la semaine.
- **Deuxième caractère (`1`)** : Bloc horaire.
- **Troisième caractère (`B`)** : Mode à activer (`A`: Off, `B`: Heat, `E`: Auto, `F`: Cool, etc.).

**Note :** L'intégration ne permet pas de modifier ce planning pour le moment.

### Scripts de Test

Des scripts de test sont fournis pour interagir avec l'API en dehors de Home Assistant.

**Test général de l'API**
```sh
python scripts/test_api.py votre_email votre_mot_de_passe
```

**Test du mode vacances**
```sh
# Activer
python scripts/test_vacation_mode.py email pass --start "YYYY-MM-DD HH:MM:SS" --end "YYYY-MM-DD HH:MM:SS"

# Désactiver
python scripts/test_vacation_mode.py email pass --disable
```

</details>
