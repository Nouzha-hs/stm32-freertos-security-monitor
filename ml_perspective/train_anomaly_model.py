#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entraînement du modèle de détection d'anomalies pour STM32 (Perspective TinyML)
Projet Sécurité Systèmes Embarqués Temps Réel
"""

import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

BASE_DIR = os.path.dirname(__file__)
DATASET_PATH = os.path.join(BASE_DIR, "dataset_sample.csv")
MODEL_OUTPUT_PATH = os.path.join(BASE_DIR, "anomaly_model.h5")

def generate_augmented_data(samples=1000):
    """Génère un jeu de données synthétique basé sur les distributions du sujet."""
    np.random.seed(42)
    # 80% normal, 20% anomalie
    n_normal = int(samples * 0.8)
    n_anom = samples - n_normal

    # Normal : faible conso, faible CPU, faible RAM, syscalls normaux
    norm_power = np.random.normal(0.25, 0.05, n_normal)
    norm_cpu = np.random.uniform(0.5, 5.0, n_normal)
    norm_mem = np.random.normal(12.5, 1.0, n_normal)
    norm_syscalls = np.eye(7)[np.random.choice(4, n_normal)] # utilise surtout les 4 1ers
    norm_procs = np.eye(5)[np.random.choice(4, n_normal)]
    norm_labels = np.zeros((n_normal, 1))

    # Anomalie : forte conso, CPU élevé (>80%), RAM en hausse, syscalls anormaux (ex: execve/mprotect)
    anom_power = np.random.normal(1.0, 0.1, n_anom)
    anom_cpu = np.random.uniform(80.0, 100.0, n_anom)
    anom_mem = np.random.normal(50.0, 5.0, n_anom)
    anom_syscalls = np.eye(7)[np.random.choice([4, 5, 6], n_anom)]
    anom_procs = np.eye(5)[np.random.choice([3, 4], n_anom)]
    anom_labels = np.ones((n_anom, 1))

    X_norm = np.hstack([norm_power.reshape(-1, 1), norm_cpu.reshape(-1, 1), norm_mem.reshape(-1, 1), norm_syscalls, norm_procs])
    X_anom = np.hstack([anom_power.reshape(-1, 1), anom_cpu.reshape(-1, 1), anom_mem.reshape(-1, 1), anom_syscalls, anom_procs])

    X = np.vstack([X_norm, X_anom])
    y = np.vstack([norm_labels, anom_labels])
    return X, y

def main():
    print("[INFO] Préparation des données d'entraînement (15 caractéristiques)...")
    X, y = generate_augmented_data(2000)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Modèle ultra-léger adapté aux microcontrôleurs STM32 (TinyML)
    model = keras.Sequential([
        keras.layers.Input(shape=(15,)),
        keras.layers.Dense(16, activation='relu'),
        keras.layers.Dense(8, activation='relu'),
        keras.layers.Dense(1, activation='sigmoid')
    ])

    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    model.summary()

    print("[INFO] Début de l'entraînement...")
    model.fit(X_train, y_train, epochs=20, batch_size=32, validation_data=(X_test, y_test), verbose=1)

    loss, acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"[RÉSULTAT] Précision sur le jeu de test : {acc * 100:.2f}%")

    model.save(MODEL_OUTPUT_PATH)
    print(f"[SUCCÈS] Modèle sauvegardé dans {MODEL_OUTPUT_PATH}")
    print("[SUITE] Lancez 'python convert_tflite.py' pour convertir vers STM32.")

if __name__ == "__main__":
    main()
