#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entraînement du modèle de détection d'anomalies sur les données officielles
Projet Sécurité Systèmes Embarqués Temps Réel (Perspective TinyML)
Destiné au Membre 3
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix

BASE_DIR = os.path.dirname(__file__)
DATASET_PATH = os.path.join(BASE_DIR, "dataset_sample.csv")
MODEL_OUTPUT_PATH = os.path.join(BASE_DIR, "anomaly_model.h5")

def main():
    print("==================================================================")
    print("      ENTRAÎNEMENT DU MODÈLE TINYML - DÉTECTION D'ANOMALIES       ")
    print("==================================================================")

    if not os.path.exists(DATASET_PATH):
        print(f"[ERREUR] Fichier introuvable : {DATASET_PATH}")
        sys.exit(1)

    print(f"[1/5] Chargement du jeu de données officiel ({DATASET_PATH})...")
    df = pd.read_csv(DATASET_PATH)
    print(f"      Nombre d'échantillons : {len(df)} lignes")
    print(f"      Colonnes ({len(df.columns)}) : {list(df.columns)}")

    # Conversion des booléens (True/False) en entiers (1/0)
    for col in df.columns:
        if df[col].dtype == bool or df[col].dtype == object:
            if set(df[col].unique()).issubset({True, False, 'True', 'False'}):
                df[col] = df[col].astype(bool).astype(int)

    # Séparation Features (15 colonnes) et Target (Label)
    if 'Label' not in df.columns:
        print("[ERREUR] Colonne 'Label' absente du fichier CSV !")
        sys.exit(1)

    y = df['Label'].values
    X_df = df.drop(columns=['Label'])
    feature_names = list(X_df.columns)
    print(f"[2/5] 15 caractéristiques d'entrée identifiées :")
    for idx, name in enumerate(feature_names, 1):
        print(f"      {idx:02d}. {name}")

    X = X_df.values.astype(np.float32)

    # Répartition Train / Test (80% / 20%)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n[3/5] Découpage des données : Train={len(X_train)}, Test={len(X_test)}")
    print(f"      Proportion anomalies dans Test : {np.sum(y_test)} / {len(y_test)}")

    # Normalisation des caractéristiques
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Construction du réseau de neurones compact pour microcontrôleur
    try:
        import tensorflow as tf
        from tensorflow import keras
    except ImportError:
        print("\n[ATTENTION] TensorFlow n'est pas encore installé.")
        print("Pour l'installer : pip install tensorflow")
        print("\nEntraînement alternatif avec Scikit-Learn (RandomForest / MLPClassifier)...")
        from sklearn.neural_network import MLPClassifier
        clf = MLPClassifier(hidden_layer_sizes=(16, 8), max_iter=200, random_state=42)
        clf.fit(X_train_scaled, y_train)
        score = clf.score(X_test_scaled, y_test)
        print(f"[RÉSULTAT] Précision du modèle Scikit-Learn : {score * 100:.2f}%\n")
        return

    print("\n[4/5] Architecture du réseau de neurones TinyML (Keras) :")
    model = keras.Sequential([
        keras.layers.Input(shape=(15,), name="system_features"),
        keras.layers.Dense(16, activation='relu', name="dense_1"),
        keras.layers.Dropout(0.1),
        keras.layers.Dense(8, activation='relu', name="dense_2"),
        keras.layers.Dense(1, activation='sigmoid', name="anomaly_probability")
    ])

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.005),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    model.summary()

    # Entraînement
    print("\n[5/5] Entraînement sur 30 époques...")
    history = model.fit(
        X_train_scaled, y_train,
        epochs=30,
        batch_size=16,
        validation_data=(X_test_scaled, y_test),
        verbose=1
    )

    loss, acc = model.evaluate(X_test_scaled, y_test, verbose=0)
    print(f"\n==================================================================")
    print(f"   RÉSULTAT FINAL TEST : Précision = {acc * 100:.2f}% | Loss = {loss:.4f}")
    print(f"==================================================================")

    # Sauvegarde du modèle
    model.save(MODEL_OUTPUT_PATH)
    print(f"[OK] Modèle sauvegardé dans : {MODEL_OUTPUT_PATH}")
    print("[SUITE POUR MEMBRE 3] Lancez 'python convert_tflite.py' pour générer model_data.h !")

if __name__ == "__main__":
    main()
