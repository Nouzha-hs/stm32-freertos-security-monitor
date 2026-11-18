# Perspective TinyML : détection d'anomalies noyau

Cette partie du projet (Membre 3) montre comment un petit réseau de neurones
peut détecter des comportements anormaux sur un microcontrôleur STM32 (Cortex-M).

> **Statut : perspective.** Le modèle est entraîné sur des données simulées.
> Il n'est pas encore branché en temps réel sur la carte.

## 1. Données

Fichier : `dataset_sample.csv` (20 lignes réelles du projet) + 300 lignes **synthétiques**
générées par le script d'entraînement (option `--augment 300`).

| Groupe | Colonnes | Nombre |
|---|---|---|
| Mesures | `Power_W`, `CPU_Usage_%`, `Mem_Usage_MB` | 3 |
| Appels système | `Syscall_1` à `Syscall_7` (0/1) | 7 |
| Processus | `Proc_1` à `Proc_5` (0/1) | 5 |
| **Entrées totales** | | **15** |
| Label | 0 = normal, 1 = anormal | 1 |

Les lignes synthétiques ajoutent des cas intermédiaires (forte charge normale,
anomalie discrète) pour que le problème ne soit pas trop facile.

## 2. Modèle

Réseau de neurones dense : `15 → 16 → 8 → 1` (activation ReLU, sortie sigmoïde).

- Séparation des données : 70 % entraînement, 15 % validation, 15 % test (stratifiée)
- Normalisation des 3 mesures numériques uniquement (moyenne et écart-type dans `scaler_params.h`)

## 3. Résultats (jeu de test : 48 lignes)

| Mesure | Valeur |
|---|---|
| Précision globale | 97,9 % |
| Normal : rappel | 100 % (25 / 25) |
| Anormal : rappel | 95,7 % (22 / 23) |
| Fausses alertes | 0 |
| Anomalies manquées | 1 |

Matrice de confusion : `[[25, 0], [1, 22]]`

## 4. Empreinte mémoire (quantification int8)

| Mesure | Valeur |
|---|---|
| Paramètres | 401 |
| Taille Flash (modèle int8) | 3 400 octets (3,32 Ko) |
| RAM (tensor arena) | à mesurer avec TFLite Micro |

Le modèle est assez petit pour un Cortex-M.

## 5. Utilisation

```bash
pip install tensorflow pandas scikit-learn numpy
python train_anomaly_model_membre3.py --csv dataset_sample.csv --augment 300
python convert_tflite_membre3.py
```

Fichiers produits :
- `model_data.h` : modèle int8 sous forme de tableau C, avec `scale` et `zero_point`
- `scaler_params.h` : moyennes et écarts-types des 3 mesures
- `anomaly_model_int8.tflite` : modèle TFLite

## 6. Intégration firmware

1. Normaliser les 3 premières entrées avec `scaler_params.h`.
2. Quantifier les 15 entrées en int8 avec `MODEL_INPUT_SCALE` et `MODEL_INPUT_ZERO_POINT`.
3. Lancer l'inférence, puis comparer la sortie à 0,5 après déquantification.

## 7. Limites

- Données en grande partie synthétiques : les 97,9 % ne sont pas une preuve de performance réelle.
- Les appels système et les processus ne sont pas fournis directement par FreeRTOS.
- Le modèle doit être validé sur de vraies mesures avant tout usage réel.
