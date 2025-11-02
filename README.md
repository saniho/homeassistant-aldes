# Intégration Aldes pour Home Assistant

Cette intégration permet de contrôler votre système Aldes depuis Home Assistant.

## Installation

1. Copiez le dossier `custom_components/aldes` dans le dossier `custom_components` de votre installation Home Assistant
2. Redémarrez Home Assistant
3. Allez dans Configuration > Intégrations
4. Cliquez sur "Ajouter une intégration"
5. Recherchez "Aldes"
6. Entrez vos identifiants Aldes (email et mot de passe)

## Fonctionnalités

- Contrôle des thermostats
- Affichage des températures actuelles
- Réglage des températures de consigne
- Mode air et eau
- Quantité d'eau chaude
- État de connexion

## Entités créées

L'intégration crée plusieurs entités dans Home Assistant :

### Thermostats
- Une entité climate pour chaque thermostat
- Température actuelle
- Température de consigne
- Mode de fonctionnement

### Capteurs
- Mode air actuel
- Mode eau actuel
- Température principale
- Quantité d'eau chaude
- État de connexion

## Configuration

La configuration se fait entièrement via l'interface utilisateur de Home Assistant. Aucune configuration manuelle n'est nécessaire.

### Options de configuration

- **Username** : Votre adresse email Aldes
- **Password** : Votre mot de passe Aldes

## Dépannage

En cas de problème de connexion :
1. Vérifiez vos identifiants
2. Assurez-vous que vous pouvez vous connecter à l'application Aldes
3. Vérifiez les logs de Home Assistant pour plus de détails

## API Test

Un script de test de l'API est fourni pour vérifier votre connexion :

```bash
python scripts/test_api.py votre_email votre_mot_de_passe
```
