# Module TinyML & Perspective IA Embarquée

Ce module illustre la chaîne complète d'apprentissage automatique embarqué pour la détection d'intrusions / anomalies sur microcontrôleur STM32.

## Entrées du modèle (15 caractéristiques + 1 label)
1. `Power_W` : Consommation électrique instantanée (W)
2. `CPU_Usage_%` : Charge du processeur (%)
3. `Mem_Usage_MB` : Mémoire RAM allouée (Mo)
4. `Syscall` : 7 colonnes binaires (one-hot encoding) correspondant aux appels système clés
5. `Process_Name` : 5 colonnes binaires identifiant les tâches actives
6. `Label` (Sortie) : 0 pour Comportement Normal, 1 pour Anomalie / Attaque

## Workflow d'utilisation
1. **Entraînement :**
   ```bash
   pip install -r requirements.txt
   python train_anomaly_model.py
   ```
2. **Compression et conversion C :**
   ```bash
   python convert_tflite.py
   ```
   Cette commande génère le fichier `model.tflite` et crée automatiquement le tableau C de constantes `model_data.h` dans `firmware/Core/Inc/model_data.h`.
3. **Intégration STM32CubeIDE :**
   Le tableau `g_model_data` est alors directement exploitable par la bibliothèque **TensorFlow Lite for Microcontrollers (TFLM)** ou le framework **X-CUBE-AI** de STMicroelectronics.
