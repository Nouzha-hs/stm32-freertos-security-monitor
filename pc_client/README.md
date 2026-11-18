# Passerelle PC (Lecture Série & Alerte Email)

Ce module s'exécute sur le PC de développement. Il se connecte au port virtuel COM (créé par le ST-LINK de la carte STM32) et écoute les trames de télémétrie.

## Fonctionnement
1. Réception en continu des logs (`cpu=%`, `jitter_max`, `deadline_miss`).
2. Interception des trames d'alerte `ALERT,<cpu_val>`.
3. Envoi immédiat d'un e-mail d'alerte SMTP (avec gestion de temporisation anti-spam / cooldown).

## Installation
```bash
cd pc_client
pip install -r requirements.txt
```

## Configuration
Copiez le fichier d'exemple et renseignez vos paramètres :
```bash
cp config.json.example config.json
```
Modifiez `config.json` avec vos identifiants SMTP (ex: mot de passe d'application Google) et le bon port COM (ex: `COM3` sous Windows ou `/dev/ttyACM0` sous Linux).

## Lancement
```bash
python serial_alert_bridge.py
```
