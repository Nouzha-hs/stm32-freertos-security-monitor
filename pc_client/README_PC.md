# Module de Supervision PC & Passerelle d'Alerte Réseau

Ce module correspond au travail du **Membre 2** (Ingénieur Logiciel PC & Supervision Télémétrie).

Il fait le pont entre le monde embarqué physique (microcontrôleur STM32 / FreeRTOS) et les systèmes d'alerte et de supervision distants (notification SMTP et journalisation de sécurité).

---

## 1. Architecture Fonctionnelle

```text
[ STM32 NUCLEO-F401RE ]
         │
         │  (Liaison USB / UART2 @ 115200 bauds)
         ▼
[ serial_alert_bridge.py ]  <─── Options CLI : --simulate, --test-email, --port
   ├── 1. Parsing télémétrie en temps réel (charge CPU, Jitter, Deadlines)
   ├── 2. Détection d'anomalie / seuil critique (Trame ALERT,xx)
   ├── 3. Filtrage temporel anti-spam (Fenêtre de Cooldown : 30 s)
   ├── 4. Journal d'audit d'incidents (alerts_history.csv)
   └── 5. Expédition d'e-mail d'urgence chiffré (SMTP / TLS port 587)
         │
         ▼
[ Boîte de Réception Administrateur / Smartphone ]
```

---

## 2. Format des Trames de Télémétrie

La passerelle intercepte deux types de messages émis par le firmware STM32 :

### A. Trames périodiques d'état (toutes les secondes)
```text
cpu=1%  idle=593041923  ref=279346  jitter_max=1 us  miss=0
```
* `cpu` : Pourcentage d'utilisation du microcontrôleur calculé à partir de la tâche d'inactivité (*Idle Hook*).
* `idle` : Nombre cumulé de cycles d'inactivité mesurés par le noyau.
* `jitter_max` : Écart maximal mesuré en microsecondes par le compteur de cycles DWT sur la tâche critique (période de 10 ms).
* `miss` : Nombre d'échéances temporelles manquées (*deadlines misses*). Reste à **0** grâce à l'isolation préemptive de FreeRTOS.

### B. Trame d'alerte prioritaire
```text
ALERT,100
```
Émise immédiatement dès que la charge CPU dépasse le seuil de sécurité (`CPU_SEUIL = 50%`).

---

## 3. Guide de Configuration SMTP (Envoi d'E-mails Réels)

Pour que la passerelle puisse transmettre de vrais e-mails d'alerte sans risque pour votre mot de passe principal :

1. Copiez le gabarit de configuration :
   ```bash
   cp config.json.example config.json
   ```
2. Ouvrez `config.json` et configurez votre boîte d'envoi.

### 💡 Procédure pour un compte Gmail :
Les messageries modernes exigent un **Mot de passe d'application** :
1. Rendez-vous sur votre compte Google : [https://myaccount.google.com/security](https://myaccount.google.com/security).
2. Activez la **Validation en deux étapes** si ce n'est pas déjà fait.
3. Allez dans [Mots de passe d'application](https://myaccount.google.com/apppasswords).
4. Créez un mot de passe nommé par exemple `STM32-Monitor` (Google vous donne une clé de 16 lettres).
5. Renseignez cette clé dans `config.json` :
   ```json
   {
     "smtp": {
       "enabled": true,
       "host": "smtp.gmail.com",
       "port": 587,
       "use_tls": true,
       "user": "votre_adresse@gmail.com",
       "password": "abcd efgh ijkl mnop",
       "recipient": "adresse_destinataire@gmail.com"
     }
   }
   ```

---

## 4. Guide d'Utilisation des Commandes

### A. Tester la configuration SMTP en 2 secondes :
```bash
python serial_alert_bridge.py --test-email
```
Vérifie la connexion au serveur et vous envoie un e-mail de test immédiat.

### B. Lancer en Mode Réel (Carte STM32 branchée en USB) :
```bash
python serial_alert_bridge.py
# ou en précisant le port :
python serial_alert_bridge.py --port COM3 --baudrate 115200
```
Dès que vous pressez le bouton bleu B1 de la carte STM32, l'incident est détecté, tracé dans le terminal et consigné.

### C. Lancer en Mode Simulation Autonome (Sans matériel physique) :
```bash
python serial_alert_bridge.py --simulate
```
Idéal pour les démonstrations de soutenance ou pour valider la chaîne logicielle sans avoir la carte sous la main. Génère automatiquement le cycle complet (régime normal, injection d'attaque DoS, alerte SMTP et retour à la normale).

---

## 5. Journalisation d'Audit de Sécurité (`alerts_history.csv`)

Chaque événement critique est consigné avec horodatage pour traçabilité SOC/SIEM :

| Timestamp | CPU_Usage_Pct | Jitter_Max_us | Deadline_Miss | Raw_UART_Line | Email_Status |
|:---|:---:|:---:|:---:|:---|:---|
| 2026-11-20 12:15:56 | 100 | 12 | 0 | `ALERT,100` | `SENT` |
| 2026-11-20 12:16:01 | 85 | 12 | 0 | `ALERT,85` | `IGNORED_COOLDOWN` |

---

## 6. Synthèse des Résultats Validés

* ✅ Écoute série asynchrone non-bloquante avec reconnexion propre.
* ✅ Interception immédiate des trames d'alerte (< 50 ms après émission STM32).
* ✅ Mécanisme de Cooldown anti-spam validé (évite l'inondation de la messagerie lors des attaques prolongées).
* ✅ Traçabilité des incidents dans un fichier CSV d'audit.
