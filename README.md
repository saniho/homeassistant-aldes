# Intégration Aldes pour Home Assistant

Cette intégration permet de contrôler votre système Aldes depuis Home Assistant.

## Avertissement

Cette intégration est développée de manière indépendante et n'est pas officiellement soutenue par Aldes. L'auteur ne peut être tenu responsable de tout dysfonctionnement, dommage matériel ou perte de garantie résultant de l'utilisation de ce composant. Utilisez-le à vos propres risques.

## Installation

### Méthode 1 : HACS (Home Assistant Community Store) - Recommandé

1.  Assurez-vous d'avoir [HACS](https://hacs.xyz/) installé.
2.  Dans HACS, allez dans "Intégrations".
3.  Cliquez sur les trois points en haut à droite et sélectionnez "Dépôts personnalisés".
4.  Dans le champ "Dépôt", collez l'URL de ce dépôt GitHub.
5.  Dans la catégorie, sélectionnez "Intégration".
6.  Cliquez sur "Ajouter".
7.  Vous devriez maintenant voir l'intégration "Aldes". Cliquez sur "Installer".
8.  Redémarrez Home Assistant.

### Méthode 2 : Manuelle

1.  Copiez le dossier `custom_components/aldes` dans le dossier `custom_components` de votre installation Home Assistant.
2.  Redémarrez Home Assistant.

### Configuration de l'intégration

Une fois l'installation terminée :

1.  Allez dans **Paramètres > Appareils et services**.
2.  Cliquez sur **"Ajouter une intégration"**.
3.  Recherchez **"Aldes"**.
4.  Entrez vos identifiants Aldes (email et mot de passe).

## Entités créées

L'intégration crée un appareil Aldes dans Home Assistant, qui contient plusieurs entités :

- **Climate** : Une entité pour chaque thermostat, permettant de contrôler la température et le mode.
- **Sensor** : Capteurs pour la température principale, le niveau d'eau chaude, les modes, etc.
- **Binary Sensor** : Capteurs pour l'état de la connexion, le mode vacances et le mode hors gel.
- **Switch** :
    - Un interrupteur pour activer/désactiver le mode vacances. **Note :** Cette fonctionnalité est expérimentale. L'activation définit une période de vacances de 7 jours par défaut.
    - Un interrupteur pour activer/désactiver le mode hors gel. **Note :** Cette fonctionnalité est expérimentale.

## Services

### Service `aldes.set_vacation_dates`

Ce service vous permet de définir une période de vacances personnalisée.

#### Comment l'utiliser

Allez dans **Outils de développement > Services**, recherchez le service `aldes.set_vacation_dates` et remplissez les champs.

#### Paramètres

- **device_id** : (Obligatoire) L'identifiant de votre appareil Aldes. Vous pouvez le trouver dans les détails de l'appareil.
- **start_date** : (Optionnel) La date et l'heure de début des vacances.
- **end_date** : (Optionnel) La date et l'heure de fin des vacances.

#### Exemples

**Pour activer le mode vacances du 20 au 27 décembre 2024 :**

```yaml
service: aldes.set_vacation_dates
data:
  device_id: VOTRE_DEVICE_ID
  start_date: "2024-12-20 08:00:00"
  end_date: "2024-12-27 18:00:00"
```

**Pour désactiver le mode vacances :**

Laissez les champs `start_date` et `end_date` vides.

```yaml
service: aldes.set_vacation_dates
data:
  device_id: VOTRE_DEVICE_ID
```

## Dépannage

En cas de problème de connexion :
1. Vérifiez vos identifiants.
2. Assurez-vous que vous pouvez vous connecter à l'application mobile officielle Aldes.
3. Vérifiez les logs de Home Assistant pour plus de détails (Paramètres > Système > Journaux).

## API Test

Un script de test de l'API est fourni pour vérifier votre connexion en dehors de Home Assistant :

```bash
python scripts/test_api.py votre_email votre_mot_de_passe
```
