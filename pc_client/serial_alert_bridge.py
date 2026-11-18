#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Passerelle Série (UART) -> Alerte Email
Projet Sécurité Systèmes Embarqués Temps Réel (STM32 + FreeRTOS)

Ce script écoute le port série de la carte STM32 (ex: COM3) et déclenche
l'envoi d'un e-mail d'alerte lors de la détection d'une anomalie/attaque.
"""

import os
import sys
import json
import time
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    import serial
except ImportError:
    print("[ERREUR] pyserial n'est pas installé. Exécutez : pip install -r requirements.txt")
    sys.exit(1)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
CONFIG_EXAMPLE = os.path.join(os.path.dirname(__file__), "config.json.example")

def load_config():
    target = CONFIG_FILE if os.path.exists(CONFIG_FILE) else CONFIG_EXAMPLE
    try:
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ATTENTION] Impossible de lire {target} ({e}). Utilisation des valeurs par défaut.")
        return {
            "serial": {"port": "COM3", "baudrate": 115200, "timeout": 1.0},
            "smtp": {"enabled": False},
            "alert": {"cooldown_seconds": 30}
        }

def send_alert_email(config, cpu_value, log_line):
    smtp_cfg = config.get("smtp", {})
    if not smtp_cfg.get("enabled", False):
        print(f"[SIMULATION EMAIL] Alerte CPU {cpu_value}% détectée (SMTP désactivé dans la config).")
        return

    sender = smtp_cfg.get("user")
    recipient = smtp_cfg.get("recipient")
    subject = f"🚨 [ALERTE SÉCURITÉ STM32] Surcharge critique détectée (CPU: {cpu_value}%)"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    body = f"""Bonjour,

Une anomalie critique / attaque par saturation a été détectée sur le nœud embarqué STM32 temps réel !

Détails de l'incident :
--------------------------------------------------
• Horodatage      : {now_str}
• Utilisation CPU : {cpu_value} %
• Dernier log UART: {log_line}
• Action locale   : Buzzer/LED d'alarme activé sur GPIO
• État RTOS       : Tâche critique sous protection de priorité

Veuillez inspecter le système ou consulter le tableau de bord de télémétrie.

--
Système IDS Embarqué FreeRTOS STM32
"""

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP(smtp_cfg.get("host"), smtp_cfg.get("port"))
        if smtp_cfg.get("use_tls", True):
            server.starttls()
        server.login(sender, smtp_cfg.get("password"))
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        print(f"[EMAIL ENVOYÉ] Notification transmise avec succès à {recipient}")
    except Exception as err:
        print(f"[ERREUR EMAIL] Échec lors de l'envoi du message : {err}")

def main():
    config = load_config()
    ser_cfg = config.get("serial", {})
    port = ser_cfg.get("port", "COM3")
    baudrate = ser_cfg.get("baudrate", 115200)
    cooldown = config.get("alert", {}).get("cooldown_seconds", 30)

    last_alert_time = 0

    print("==============================================================")
    print("   MONITEUR SÉRIE & DÉTECTEUR D'ANOMALIE STM32 / FreeRTOS     ")
    print(f"   Port : {port} | Vitesse : {baudrate} bauds")
    print("==============================================================")

    try:
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=ser_cfg.get("timeout", 1.0))
        print(f"[CONNECTÉ] En attente de télémétrie depuis {port}...\n")
    except Exception as e:
        print(f"[ERREUR] Impossible d'ouvrir le port {port} : {e}")
        print("-> Vérifiez le branchement du câble USB et le numéro de port dans config.json.")
        return

    try:
        while True:
            raw_line = ser.readline()
            if not raw_line:
                continue

            try:
                line = raw_line.decode("utf-8", errors="replace").strip()
            except Exception:
                continue

            if not line:
                continue

            # Affichage console avec horodatage
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {line}")

            # Détection d'alerte envoyée par la STM32 (ex: "ALERT,100" ou "ALERT,87")
            if line.startswith("ALERT"):
                parts = line.split(",")
                cpu_val = parts[1] if len(parts) > 1 else "Inconnu"

                current_time = time.time()
                if (current_time - last_alert_time) > cooldown:
                    print(f"\n⚠️  [ALERTE DÉCLENCHÉE] CPU = {cpu_val}% - Envoi d'une alerte email...")
                    send_alert_email(config, cpu_val, line)
                    last_alert_time = current_time
                else:
                    print(f"ℹ️  [ALERTE] CPU = {cpu_val}% (Notification ignorée: cooldown actif)")

    except KeyboardInterrupt:
        print("\n[ARRÊT] Arrêt du moniteur par l'utilisateur.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("[INFO] Port série fermé.")

if __name__ == "__main__":
    main()
