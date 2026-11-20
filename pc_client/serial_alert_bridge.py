#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Passerelle Série (UART) & Supervision de Sécurité Temps Réel
Projet Sécurité Systèmes Embarqués Temps Réel (STM32 + FreeRTOS)
Responsabilité : Membre 2 (Ingénieur Logiciel PC & Supervision Télémétrie)

Fonctionnalités :
1. Écoute UART temps réel (COM3 / 115200 bauds) ou mode Simulation autonome (--simulate)
2. Détection instantanée d'anomalies et d'attaques DoS (trames ALERT,<cpu>)
3. Affichage terminal interactif avec jauge visuelle de charge CPU
4. Notification d'urgence distante par e-mail SMTP sécurisé (TLS) avec cooldown anti-spam
5. Journalisation des incidents dans un fichier CSV d'audit (alerts_history.csv)
"""

import os
import sys
import json
import time
import smtplib
import argparse
import csv
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    import serial
except ImportError:
    serial = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
CONFIG_EXAMPLE = os.path.join(BASE_DIR, "config.json.example")
LOG_CSV_FILE = os.path.join(BASE_DIR, "alerts_history.csv")


def load_config():
    """Charge la configuration depuis config.json ou config.json.example."""
    target = CONFIG_FILE if os.path.exists(CONFIG_FILE) else CONFIG_EXAMPLE
    try:
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ATTENTION] Impossible de lire {target} ({e}). Paramètres par défaut appliqués.")
        return {
            "serial": {"port": "COM3", "baudrate": 115200, "timeout": 1.0},
            "smtp": {
                "enabled": False,
                "host": "smtp.gmail.com",
                "port": 587,
                "use_tls": True,
                "user": "",
                "password": "",
                "recipient": ""
            },
            "alert": {"cooldown_seconds": 30, "threshold_pct": 50}
        }


def init_alert_log():
    """Initialise le fichier CSV d'audit des alertes s'il n'existe pas."""
    if not os.path.exists(LOG_CSV_FILE):
        try:
            with open(LOG_CSV_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "CPU_Usage_Pct", "Jitter_Max_us",
                    "Deadline_Miss", "Raw_UART_Line", "Email_Status"
                ])
        except Exception as e:
            print(f"[LOG] Erreur d'initialisation du fichier CSV : {e}")


def log_alert_to_csv(cpu_val, jitter_val, miss_val, raw_line, email_status):
    """Enregistre un incident dans le fichier d'audit CSV."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([now_str, cpu_val, jitter_val, miss_val, raw_line, email_status])
    except Exception as e:
        print(f"[LOG] Impossible d'écrire dans {LOG_CSV_FILE} : {e}")


def render_cpu_bar(cpu_pct, width=25):
    """Génère une barre de progression visuelle pour la console."""
    try:
        val = int(cpu_pct)
    except (ValueError, TypeError):
        val = 0
    val = max(0, min(100, val))
    filled = int(width * val / 100)
    bar = "█" * filled + "░" * (width - filled)
    if val >= 80:
        return f"\033[91m[{bar}] {val:3d}%\033[0m"  # Rouge
    elif val >= 50:
        return f"\033[93m[{bar}] {val:3d}%\033[0m"  # Jaune
    else:
        return f"\033[92m[{bar}] {val:3d}%\033[0m"  # Vert


def send_alert_email(config, cpu_value, log_line):
    """Envoie une notification d'alerte critique par e-mail via SMTP."""
    smtp_cfg = config.get("smtp", {})
    if not smtp_cfg.get("enabled", False):
        print(f"   ℹ️  [MODE SIMULATION EMAIL] Alerte CPU {cpu_value}% (SMTP désactivé dans config.json).")
        return "SIMULATED (SMTP disabled)"

    sender = smtp_cfg.get("user")
    recipient = smtp_cfg.get("recipient")
    if not sender or not recipient:
        print("   ⚠️  [SMTP NON CONFIGURÉ] Renseignez 'user' et 'recipient' dans config.json.")
        return "FAILED (missing credentials)"

    subject = f"🚨 [ALERTE SÉCURITÉ STM32] Surcharge critique détectée (CPU: {cpu_value}%)"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    body = f"""Bonjour,

Une anomalie critique / attaque par saturation DoS a été détectée sur le nœud embarqué STM32 temps réel !

Détails de l'incident de sécurité :
----------------------------------------------------------------------
• Horodatage      : {now_str}
• Utilisation CPU : {cpu_value} % (Seuil dépassé)
• Télémétrie UART : {log_line}
• Action matérielle : Buzzer piézoélectrique activé sur broche GPIO PB0
• Déterminisme RTOS : Tâche critique prioritaire préservée (FreeRTOS)
----------------------------------------------------------------------

Statut : Incident consigné dans le journal d'audit local ({os.path.basename(LOG_CSV_FILE)}).
Veuillez vérifier l'état du processeur et des communications réseau.

--
Système IDS Embarqué STM32 / FreeRTOS
Passerelle de Supervision (Membre 2)
"""

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP(smtp_cfg.get("host", "smtp.gmail.com"), smtp_cfg.get("port", 587), timeout=10)
        if smtp_cfg.get("use_tls", True):
            server.starttls()
        server.login(sender, smtp_cfg.get("password", ""))
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        print(f"   📧 [EMAIL ENVOYÉ] Notification transmise avec succès à {recipient} !")
        return "SENT"
    except Exception as err:
        print(f"   ❌ [ERREUR EMAIL] Échec d'envoi SMTP : {err}")
        return f"ERROR ({err})"


def run_simulation(config, cooldown):
    """Simulateur de flux UART autonome pour tester la passerelle sans carte physique."""
    print("--------------------------------------------------------------")
    print("   MODE SIMULATION AUTONOME ACTIF (Sans carte STM32 physique)  ")
    print("   Génération automatique du scénario : Nominal -> Attaque -> Retour")
    print("--------------------------------------------------------------\n")

    scenario_ticks = 0
    last_alert_time = 0

    try:
        while True:
            scenario_ticks += 1
            now_ts = datetime.now().strftime("%H:%M:%S")

            # Scénario : Attaque toutes les 12 secondes pendant 2 secondes
            is_attack = (scenario_ticks % 14 in [8, 9])

            if is_attack:
                cpu = 100 if scenario_ticks % 14 == 8 else 85
                jitter = 12
                miss = 0
                line = f"cpu={cpu}%  idle=597733416  ref=279346  jitter_max={jitter} us  miss={miss}"
                alert_trame = f"ALERT,{cpu}"

                bar = render_cpu_bar(cpu)
                print(f"[{now_ts}] {bar}  jitter={jitter}us  miss={miss}  | {alert_trame}")

                current_time = time.time()
                if (current_time - last_alert_time) > cooldown:
                    print(f"\n🚨 [DÉTECTION INCIDENT] CPU saturé à {cpu}% ! Déclenchement alerte...")
                    status = send_alert_email(config, cpu, line)
                    log_alert_to_csv(cpu, jitter, miss, alert_trame, status)
                    last_alert_time = current_time
                    print()
                else:
                    print(f"   ⏳ [COOLDOWN] Notification ignorée (fenêtre anti-spam active)\n")
            else:
                cpu = 1
                jitter = 1
                miss = 0
                idle_val = 590000000 + (scenario_ticks * 280000)
                line = f"cpu={cpu}%  idle={idle_val}  ref=279346  jitter_max={jitter} us  miss={miss}"
                bar = render_cpu_bar(cpu)
                print(f"[{now_ts}] {bar}  jitter={jitter}us  miss={miss}")

            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[ARRÊT] Simulation terminée.")


def run_serial_listener(config, port, baudrate, cooldown):
    """Écoute le port série matériel de la carte STM32."""
    if serial is None:
        print("[ERREUR] Module 'pyserial' absent. Installez-le avec : pip install pyserial")
        sys.exit(1)

    print("--------------------------------------------------------------")
    print(f"   ÉCOUTE DU PORT SÉRIE PHYSIQUE : {port} ({baudrate} bauds)")
    print("--------------------------------------------------------------")

    try:
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=1.0)
        print(f"[CONNECTÉ] En attente de télémétrie depuis {port}...\n")
    except Exception as e:
        print(f"\n[ERREUR] Impossible d'ouvrir le port {port} : {e}")
        print("💡 Astuce : Si la carte n'est pas branchée, lancez avec l'option --simulate !")
        return

    last_alert_time = 0
    last_cpu = 0
    last_jitter = 0
    last_miss = 0

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

            now_ts = datetime.now().strftime("%H:%M:%S")

            # Parsing des lignes de télémétrie cpu=...
            if "cpu=" in line:
                try:
                    parts = line.split()
                    for p in parts:
                        if p.startswith("cpu="):
                            last_cpu = int(p.split("=")[1].replace("%", ""))
                        elif p.startswith("jitter_max="):
                            last_jitter = int(p.split("=")[1])
                        elif p.startswith("miss="):
                            last_miss = int(p.split("=")[1])
                except Exception:
                    pass

                bar = render_cpu_bar(last_cpu)
                print(f"[{now_ts}] {bar}  jitter={last_jitter:2d}us  miss={last_miss}  | {line}")

            elif line.startswith("ALERT"):
                parts = line.split(",")
                cpu_val = parts[1] if len(parts) > 1 else str(last_cpu)
                print(f"\n⚠️  [{now_ts}] TRAME REÇUE : {line}")

                current_time = time.time()
                if (current_time - last_alert_time) > cooldown:
                    print(f"🚨 [ALERTE SÉCURITÉ] CPU = {cpu_val}% ! Déclenchement de la notification...")
                    status = send_alert_email(config, cpu_val, line)
                    log_alert_to_csv(cpu_val, last_jitter, last_miss, line, status)
                    last_alert_time = current_time
                    print()
                else:
                    print(f"⏳ [COOLDOWN] Alerte CPU {cpu_val}% mémorisée mais e-mail ignoré (cooldown actif).\n")
                    log_alert_to_csv(cpu_val, last_jitter, last_miss, line, "IGNORED_COOLDOWN")
            else:
                print(f"[{now_ts}] {line}")

    except KeyboardInterrupt:
        print("\n[ARRÊT] Arrêt du moniteur série par l'utilisateur.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("[INFO] Port série fermé proprement.")


def test_smtp_connection(config):
    """Test rapide de diagnostic SMTP."""
    print("==============================================================")
    print("          DIAGNOSTIC DE CONNEXION SMTP (Membre 2)             ")
    print("==============================================================")
    smtp_cfg = config.get("smtp", {})
    host = smtp_cfg.get("host", "smtp.gmail.com")
    port = smtp_cfg.get("port", 587)
    user = smtp_cfg.get("user", "")
    pwd = smtp_cfg.get("password", "")
    recipient = smtp_cfg.get("recipient", "")

    print(f"• Serveur   : {host}:{port}")
    print(f"• Émetteur  : {user or '(non renseigné)'}")
    print(f"• Destinataire : {recipient or '(non renseigné)'}")
    print(f"• TLS actif : {smtp_cfg.get('use_tls', True)}")

    if not user or not pwd:
        print("\n❌ [ÉCHEC] Les champs 'user' et 'password' sont vides dans config.json.")
        print("💡 Créez un mot de passe d'application dans votre compte Google :")
        print("   https://myaccount.google.com/apppasswords")
        return

    print("\nConnexion en cours au serveur SMTP...")
    try:
        server = smtplib.SMTP(host, port, timeout=10)
        if smtp_cfg.get("use_tls", True):
            server.starttls()
        server.login(user, pwd)
        print("✅ [SUCCÈS] Authentification SMTP réussie !")

        if recipient:
            print(f"Envoi d'un e-mail de test à {recipient}...")
            msg = MIMEText("Ceci est un e-mail de test de la passerelle STM32 / FreeRTOS (Membre 2).", "plain", "utf-8")
            msg["Subject"] = "🧪 [TEST RÉUSSI] Passerelle de Sécurité STM32"
            msg["From"] = user
            msg["To"] = recipient
            server.sendmail(user, recipient, msg.as_string())
            print(f"✅ [SUCCÈS] E-mail de test délivré avec succès à {recipient} !")

        server.quit()
    except Exception as e:
        print(f"\n❌ [ERREUR SMTP] : {e}")


def main():
    parser = argparse.ArgumentParser(description="Passerelle Série & Supervision STM32/FreeRTOS")
    parser.add_argument("--port", type=str, default=None, help="Port COM (ex: COM3 ou /dev/ttyACM0)")
    parser.add_argument("--baudrate", type=int, default=None, help="Vitesse en bauds (ex: 115200)")
    parser.add_argument("--simulate", action="store_true", help="Lance la simulation sans carte physique")
    parser.add_argument("--test-email", action="store_true", help="Teste la connexion SMTP configurée")

    args = parser.parse_args()

    config = load_config()
    init_alert_log()

    if args.test_email:
        test_smtp_connection(config)
        return

    ser_cfg = config.get("serial", {})
    port = args.port or ser_cfg.get("port", "COM3")
    baudrate = args.baudrate or ser_cfg.get("baudrate", 115200)
    cooldown = config.get("alert", {}).get("cooldown_seconds", 30)

    print("==============================================================")
    print("   PASSERELLE DE SUPERVISION SÉRIE & DÉTECTION D'ATTAQUE      ")
    print("   Module Membre 2 : Télémétrie, Alerte SMTP & Journalisation ")
    print("==============================================================")
    print(f"• Port cible  : {port} | Vitesse : {baudrate} bauds")
    print(f"• Cooldown    : {cooldown} secondes anti-spam")
    print(f"• Journal CSV : {os.path.basename(LOG_CSV_FILE)}")
    print("==============================================================\n")

    if args.simulate:
        run_simulation(config, cooldown)
    else:
        run_serial_listener(config, port, baudrate, cooldown)


if __name__ == "__main__":
    main()
