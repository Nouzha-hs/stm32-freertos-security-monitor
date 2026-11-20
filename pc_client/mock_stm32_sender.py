#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulateur de Télémétrie STM32 (Mock Generator)
Projet : Sécurité des Systèmes Embarqués Temps Réel (STM32 + FreeRTOS)
Responsabilité : Membre 2 (Ingénieur Logiciel PC & Supervision Télémétrie)

Ce script permet de tester la chaîne complète de supervision PC sans nécessiter
la carte physique branchée. Il peut soit émettre sur un port série virtuel (ex: com0com / tty),
soit générer un flux dans un fichier ou un tube de test.
"""

import sys
import time
import random
import argparse
from datetime import datetime

try:
    import serial
except ImportError:
    serial = None


def generate_telemetry_stream(port=None, baudrate=115200, attack_interval=15):
    """
    Génère un flux continu de télémétrie conforme au firmware STM32.
    Tous les 'attack_interval' secondes, simule une attaque DoS de 3 secondes.
    """
    ser = None
    if port and serial:
        try:
            ser = serial.Serial(port=port, baudrate=baudrate)
            print(f"[MOCK] Émission active sur le port série : {port} ({baudrate} bauds)")
        except Exception as e:
            print(f"[ATTENTION] Impossible d'ouvrir {port} ({e}). Émission sur la console stdout.")

    print("==============================================================")
    print("   SIMULATEUR DE TÉLÉMÉTRIE STM32 (MOCK EMITTER)              ")
    print(f"   Cycle nominal : 1-3% CPU | Attaque tous les {attack_interval} s   ")
    print("   Appuyez sur Ctrl+C pour arrêter                           ")
    print("==============================================================\n")

    tick = 0
    idle_base = 590000000
    ref_idle = 279346

    try:
        while True:
            tick += 1
            now_ts = datetime.now().strftime("%H:%M:%S")

            # Phase d'attaque DoS (durée 3 secondes tous les attack_interval)
            in_attack = (tick % attack_interval) in [0, 1, 2]

            if in_attack:
                cpu = random.choice([95, 98, 100])
                jitter = random.randint(10, 28)
                miss = 0
                idle_val = idle_base
                line = f"cpu={cpu}% idle={idle_val} ref={ref_idle} jitter_max={jitter} us miss={miss}"
                alert_trame = f"ALERT,{cpu}"

                output = f"[{now_ts}] (ATTACK) {line}\n[{now_ts}] (ATTACK) {alert_trame}"
                to_send = f"{line}\n{alert_trame}\n"
            else:
                cpu = random.choice([1, 2, 3])
                jitter = random.choice([0, 1, 2])
                miss = 0
                idle_val = idle_base + (tick * 280000)
                line = f"cpu={cpu}% idle={idle_val} ref={ref_idle} jitter_max={jitter} us miss={miss}"
                output = f"[{now_ts}] (NOMINAL) {line}"
                to_send = f"{line}\n"

            print(output)

            if ser and ser.is_open:
                ser.write(to_send.encode("utf-8"))

            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n[MOCK] Arrêt du simulateur d'émission.")
    finally:
        if ser and ser.is_open:
            ser.close()


def main():
    parser = argparse.ArgumentParser(description="Simulateur d'émission série STM32 (Mock)")
    parser.add_argument("--port", type=str, default=None, help="Port COM virtuel de sortie (ex: COM4)")
    parser.add_argument("--baudrate", type=int, default=115200, help="Vitesse en bauds")
    parser.add_argument("--interval", type=int, default=15, help="Intervalle entre chaque attaque (secondes)")
    args = parser.parse_args()

    generate_telemetry_stream(port=args.port, baudrate=args.baudrate, attack_interval=args.interval)


if __name__ == "__main__":
    main()
