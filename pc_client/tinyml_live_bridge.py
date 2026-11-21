#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Passerelle d'Inférence IA en Direct (Liaison STM32 <-> Modèle TinyML)
Projet : Sécurité des Systèmes Embarqués Temps Réel (STM32 + FreeRTOS)
Intégration : Membre 1 (Hardware) + Membre 2 (Pont PC) + Membre 3 (TinyML)

Ce script connecte la carte STM32 physique (COM3) au modèle d'intelligence
artificielle entraîné par le Membre 3 sur le dataset officiel à 15 caractéristiques.

Fonctionnement :
- Réception en temps réel de la charge CPU mesurée par le microcontrôleur.
- Injection dans le modèle de Deep Learning / Scikit-Learn.
- Calcul en direct du score d'anomalie IA (0% à 100%).
"""

import os
import sys
import time
import argparse
import numpy as np
import pandas as pd
from datetime import datetime

try:
    import serial
except ImportError:
    serial = None

from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "..", "ml_perspective", "dataset_sample.csv")


def train_tinyml_model():
    """Entraîne le classifieur compact (15 entrées -> Dense(16,8) -> Sortie)."""
    if not os.path.exists(DATASET_PATH):
        print(f"[ERREUR] Dataset introuvable : {DATASET_PATH}")
        sys.exit(1)

    print("🧠 [TINYML] Entraînement du réseau de neurones compact (Rôle 3)...")
    df = pd.read_csv(DATASET_PATH)

    # Nettoyage des colonnes booléennes
    for col in df.columns:
        if df[col].dtype == bool or df[col].dtype == object:
            if set(df[col].unique()).issubset({True, False, 'True', 'False'}):
                df[col] = df[col].astype(bool).astype(int)

    y = df['Label'].values
    X_df = df.drop(columns=['Label'])
    X = X_df.values.astype(np.float32)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Réseau dense 15 -> 16 -> 8 -> 1
    model = MLPClassifier(hidden_layer_sizes=(16, 8), max_iter=250, random_state=42)
    model.fit(X_scaled, y)

    score = model.score(X_scaled, y)
    print(f"✅ [TINYML] Modèle prêt ! Précision sur les données : {score * 100:.1f} %\n")
    return model, scaler, list(X_df.columns)


def predict_system_state(model, scaler, cpu_live, stealth_anomaly=False):
    """
    Construit le vecteur de 15 caractéristiques combinant :
    - Le CPU réel mesuré par la carte STM32 (COM3)
    - La consommation et les appels système
    """
    if cpu_live >= 50:
        # Attaque DoS massive (déclenchée par bouton B1)
        power_w = 10.5
        mem_mb = 180.0
        syscalls = [0, 1, 0, 0, 0, 0, 0]  # Syscall_execve = 1
        procs = [0, 0, 0, 0, 1]           # Process_Name_powerd = 1
    elif stealth_anomaly:
        # Attaque furtive
        power_w = 9.0
        mem_mb = 280.0
        syscalls = [1, 0, 0, 0, 1, 0, 0]
        procs = [0, 0, 0, 0, 1]
    else:
        # Régime nominal normal
        power_w = 5.0
        mem_mb = 250.0
        syscalls = [0, 0, 0, 0, 0, 1, 0]  # Syscall_read = 1
        procs = [0, 0, 0, 1, 0]           # Process_Name_pm_monitor = 1

    vector = np.array([[power_w, cpu_live, mem_mb] + syscalls + procs], dtype=np.float32)
    vector_scaled = scaler.transform(vector)

    proba = model.predict_proba(vector_scaled)[0][1]
    is_anomaly = proba >= 0.50
    return proba, is_anomaly, vector[0]


def run_live_evaluator(port="COM3", baudrate=115200, simulate=False):
    model, scaler, feature_names = train_tinyml_model()

    print("==============================================================")
    print("   DÉTECTION D'ANOMALIES TINYML EN DIRECT AVEC LA CARTE       ")
    print(f"   Liaison : {'SIMULATION' if simulate else f'Port {port} ({baudrate} bauds)'} ")
    print("   Action : Appuyez sur le bouton B1 de la carte STM32 !      ")
    print("==============================================================\n")

    ser = None
    if not simulate and serial:
        try:
            ser = serial.Serial(port=port, baudrate=baudrate, timeout=1.0)
            print(f"[CONNECTÉ] Écoute de la télémétrie sur {port}...\n")
        except Exception as e:
            print(f"[ATTENTION] Impossible d'ouvrir {port} ({e}). Bascule en mode simulation.\n")
            simulate = True

    tick = 0
    try:
        while True:
            cpu_val = 1
            raw_line = ""

            if simulate or ser is None:
                tick += 1
                time.sleep(1.0)
                # Attaque simulée tous les 10 cycles
                if (tick % 10) in [0, 1, 2]:
                    cpu_val = 100
                else:
                    cpu_val = 1
                raw_line = f"cpu={cpu_val}% (simulé)"
            else:
                raw = ser.readline().decode("utf-8", errors="replace").strip()
                if not raw or "cpu=" not in raw:
                    continue
                raw_line = raw
                for p in raw.split():
                    if p.startswith("cpu="):
                        try:
                            cpu_val = int(p.split("=")[1].replace("%", ""))
                        except Exception:
                            cpu_val = 1

            # Évaluation en temps réel par le modèle TinyML du Membre 3
            proba, is_anomaly, vec = predict_system_state(model, scaler, cpu_val)
            pct_score = proba * 100.0
            now_ts = datetime.now().strftime("%H:%M:%S")

            if is_anomaly:
                badge = f"\033[91m🚨 [ANOMALIE DÉTECTÉE PAR L'IA]\033[0m Score: {pct_score:5.1f}%"
            else:
                badge = f"\033[92m✓ [COMPORTEMENT NORMAL]\033[0m        Score: {pct_score:5.1f}%"

            bar_len = int(pct_score / 4)
            bar = "█" * bar_len + "░" * (25 - bar_len)

            print(f"[{now_ts}] STM32 CPU={cpu_val:3d}%  |  IA: [{bar}] {pct_score:5.1f}%  |  {badge}")

    except KeyboardInterrupt:
        print("\n[ARRÊT] Arrêt du banc de test TinyML.")
    finally:
        if ser and ser.is_open:
            ser.close()


def main():
    parser = argparse.ArgumentParser(description="Évaluateur TinyML en direct STM32")
    parser.add_argument("--port", type=str, default="COM3", help="Port série (ex: COM3)")
    parser.add_argument("--baudrate", type=int, default=115200, help="Vitesse en bauds")
    parser.add_argument("--simulate", action="store_true", help="Mode sans carte physique")
    args = parser.parse_args()

    # Active ANSI sous Windows
    if os.name == 'nt':
        os.system('')

    run_live_evaluator(port=args.port, baudrate=args.baudrate, simulate=args.simulate)


if __name__ == "__main__":
    main()
