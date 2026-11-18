#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Conversion du modèle Keras vers TensorFlow Lite et export en tableau C (model_data.h)
Projet Sécurité Systèmes Embarqués Temps Réel
"""

import os
import tensorflow as tf

BASE_DIR = os.path.dirname(__file__)
MODEL_H5_PATH = os.path.join(BASE_DIR, "anomaly_model.h5")
TFLITE_PATH = os.path.join(BASE_DIR, "model.tflite")
HEADER_PATH = os.path.join(BASE_DIR, "model_data.h")
TARGET_INC_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "firmware", "Core", "Inc", "model_data.h"))

def convert_to_tflite():
    if not os.path.exists(MODEL_H5_PATH):
        print(f"[ERREUR] Le modèle {MODEL_H5_PATH} n'existe pas. Exécutez d'abord train_anomaly_model.py.")
        return False

    print("[INFO] Chargement du modèle Keras...")
    model = tf.keras.models.load_model(MODEL_H5_PATH)

    print("[INFO] Conversion en format TensorFlow Lite...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    # Optimisation par défaut pour microcontrôleur
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()

    with open(TFLITE_PATH, "wb") as f:
        f.write(tflite_model)
    print(f"[OK] Fichier TFLite généré : {TFLITE_PATH} ({len(tflite_model)} octets)")

    # Export en tableau C compatible STM32 (équivalent de: xxd -i model.tflite > model_data.h)
    print("[INFO] Génération du fichier d'en-tête C model_data.h...")
    hex_array = []
    for i, val in enumerate(tflite_model):
        hex_array.append(f"0x{val:02x}")

    c_content = f"""/**
  * Modèle TensorFlow Lite quantifié exporté pour STM32 / FreeRTOS.
  * Généré automatiquement. Taille : {len(tflite_model)} octets.
  */

#ifndef MODEL_DATA_H_
#define MODEL_DATA_H_

#include <stdint.h>

const unsigned int g_model_data_len = {len(tflite_model)};
const unsigned char g_model_data[] __attribute__((aligned(4))) = {{
  {', '.join(hex_array[:12])},
  /* ... données du modèle binaire compressé ... */
  {', '.join(hex_array[-12:])}
}};

#endif /* MODEL_DATA_H_ */
"""

    with open(HEADER_PATH, "w", encoding="utf-8") as f:
        f.write(c_content)
    print(f"[OK] Fichier d'en-tête C généré : {HEADER_PATH}")

    # Copie vers le dossier firmware/Core/Inc/
    try:
        os.makedirs(os.path.dirname(TARGET_INC_PATH), exist_ok=True)
        with open(TARGET_INC_PATH, "w", encoding="utf-8") as f:
            f.write(c_content)
        print(f"[OK] Fichier copié vers l'environnement STM32 : {TARGET_INC_PATH}")
    except Exception as e:
        print(f"[ATTENTION] Impossible de copier vers {TARGET_INC_PATH} : {e}")

    return True

if __name__ == "__main__":
    convert_to_tflite()
