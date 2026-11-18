#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulateur STM32 (Mock UART) - Permet au Membre 2 de tester sans matériel physique !
Projet Sécurité Systèmes Embarqués Temps Réel

Ce script génère les mêmes trames de télémétrie et d'alerte que la carte STM32 réelle :
- État normal : cpu=1%, jitter_max=23 us, deadline_miss=0
- Phase d'attaque : ALERT,100 puis cpu=87%, jitter_max=12 us, miss=0
"""

import time
import sys

def simulate_stm32_stream():
    print("=== DÉMARRAGE DU SIMULATEUR STM32 (Flux Virtuel) ===")
    print("Génération de trames conformes aux relevés PuTTY réels...\n")

    cycle = 0
    try:
        while True:
            cycle += 1
            # Toutes les 10 itérations, simuler une attaque
            if cycle % 10 in [6, 7]:
                # Envoi d'alerte
                cpu = 100 if cycle % 10 == 6 else 87
                print(f"ALERT,{cpu}")
                time.sleep(0.1)
                print(f"cpu={cpu}% heap=11944 jitter_max=12 us deadline_miss=0")
            else:
                # État normal
                print("cpu=1% idle=279346 ref=279346 jitter_max=23 us deadline_miss=0")
            
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nArrêt du simulateur.")

if __name__ == "__main__":
    simulate_stm32_stream()
