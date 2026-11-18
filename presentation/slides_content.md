# Support de Présentation : Sécurité des Systèmes Embarqués Temps Réel

Ce document contient le texte structuré et les notes d'oral pour les 10 diapositives de votre exposé.

---

### Diapositive 1 : Titre
* **Titre :** Sécurité des Systèmes Embarqués Temps Réel (RTOS) : Détection d'Anomalies et Préservation des Délais Critiques sur STM32
* **Sous-titre :** Projet d'ingénierie / Master SI
* **Présenté par :** [Votre Nom]
* **Encadré par :** [Nom du Professeur]
* **Date :** Année universitaire 2026

---

### Diapositive 2 : Plan de l'exposé
1. **Contexte & Enjeux :** Les systèmes embarqués temps réel et leurs contraintes spécifiques.
2. **Menaces & Vulnérabilités :** Vecteurs d'attaques logiciels, matériels et réseau.
3. **Solutions de Sécurisation :** Isolation mémoire, architecture TrustZone, cryptographie légère.
4. **Démonstration Expérimentale :** Mise en œuvre sur STM32 avec FreeRTOS, détection de surcharge et alertes multi-niveaux.
5. **Conclusion & Perspectives :** TinyML pour la détection intelligente d'intrusions.

---

### Diapositive 3 : Contexte
* **Qu'est-ce qu'un système embarqué temps réel (RTOS) ?**
  * Système où l'exactitude ne dépend pas seulement du résultat logique, mais aussi du respect strict d'échéances temporelles (**deadlines**).
  * Exemples : FreeRTOS, Zephyr, VxWorks.
* **Domaines d'application critiques :**
  * Automobile (freinage ABS, direction assistée, calculateurs ECU).
  * Médical (stimulateurs cardiaques, respirateurs artificiels).
  * Industrie & Aéronautique (contrôle de turbines, avionique).
  * Objets connectés (IoT industriel).
* **Pourquoi la sécurité est devenue critique ?**
  * L'interconnexion croissante des objets embarqués aux réseaux IP ouvre des portes aux attaquants distants avec des risques humains vitaux en cas de compromission.

---

### Diapositive 4 : Contraintes spécifiques de l'embarqué
* **Ressources extrêmement limitées (SWaP) :**
  * Mémoire RAM réduite (quelques dizaines de Ko), puissance CPU limitée, autonomie énergétique sur batterie.
* **Le dilemme Temps Réel vs Sécurité :**
  * Les mécanismes de sécurité (chiffrement lourd, vérifications de signatures) ne doivent **jamais** faire manquer une deadline à une tâche critique.
* **Cycle de vie et maintenance :**
  * Systèmes déployés pour 10 à 20 ans sur le terrain.
  * Mises à jour de firmware (FOTA) difficiles et risquées.

---

### Diapositive 5 : Menaces et problèmes
* **Attaques Logicielles :**
  * Dépassement de tampon (*buffer overflow*), injection de code, falsification de firmware.
* **Attaques Matérielles :**
  * Analyse par canaux auxiliaires (*side-channel attacks* : consommation, rayonnement EM).
  * Sondes de débogage non protégées (JTAG/SWD).
  * Injection de fautes (glitch d'horloge ou de tension).
* **Attaques Réseau & Déni de Service (DoS) :**
  * Rejeu de trames CAN/Ethernet, usurpation d'identité, saturation du bus et du microcontrôleur.
* *(Conseil pour la diapo : insérer un schéma d'architecture montrant l'attaquant envoyant un flux DoS vers le microcontrôleur).*

---

### Diapositive 6 : Modules de sécurité embarqués
* **Éléments matériels dédiés (Hardware Root of Trust) :**
  * **Secure Element (SE)**, **TPM** (Trusted Platform Module), **eHSM**.
  * Stockage inviolable des clés cryptographiques privées.
* **Environnements d'exécution de confiance (TEE) :**
  * **ARM TrustZone** : Séparation matérielle stricte entre Monde Normal (*Non-Secure World*) et Monde Sécurisé (*Secure World*).
* **Rôles fondamentaux :**
  * Démarrage sécurisé (*Secure Boot*), authentification mutuelle, chiffrement et déchiffrement matériel accéléré.

---

### Diapositive 7 : Solutions et bonnes pratiques
* **Démarrage Sécurisé (Secure Boot) :**
  * Vérification de l'intégrité et de la signature cryptographique du firmware au reset avant exécution.
* **Isolation Mémoire (MPU - Memory Protection Unit) :**
  * Configuration de régions mémoires étanches pour empêcher une tâche non sécurisée d'écraser la mémoire d'une tâche critique.
* **Cryptographie Légère (Lightweight Cryptography) :**
  * Utilisation d'algorithmes optimisés pour microcontrôleurs (AES accéléré matériellement, courbes elliptiques ECC / Ed25519).

---

### Diapositive 8 : Démonstration pratique (STM32 & FreeRTOS)
* **Banc d'essai :**
  * Carte de développement STM32 (ex: NUCLEO-F401RE / STM32F4-Discovery) sous FreeRTOS.
* **Scénario testé :**
  1. *Comportement normal :* Tâche critique exécutée à fréquence fixe, jitter < 24 µs, aucune échéance manquée (`deadline_miss = 0`).
  2. *Attaque de surcharge (DoS) :*
     * **Avec priorité basse de l'attaque :** Le RTOS protège la tâche critique, mais l'attaque est **invisible** (CPU saturé à 100% pendant 2s).
     * **Sans protection de priorité :** Dépassements massifs de délais (`deadline_miss = 202`, jitter supérieur à 1,9 seconde !).
  3. *Système de détection par seuil CPU :*
     * Détection instantanée dès que `CPU > 80%`.
     * Alerte sonore/visuelle locale (Buzzer/LED sur broche GPIO).
     * Transmission UART d'une trame `ALERT,100` vers le PC ➔ Script Python ➔ Déclenchement automatique d'un e-mail d'alerte.

---

### Diapositive 9 : Conclusion
* **Ce qu'il faut retenir :**
  * La sécurité dans l'embarqué ne peut pas être un simple ajout après coup : elle doit être intégrée dès la conception (*Security by Design*).
  * Les priorités d'ordonnancement d'un RTOS protègent les tâches critiques, mais ne suffisent pas à elles seules : un monitoring actif de charge ou d'intrusions est indispensable.
* **Équilibre fondamental :** Garantir la sécurité sans compromettre le déterminisme temps réel.

---

### Diapositive 10 : Perspectives & Questions
* **Perspectives futures :**
  * Détection d'anomalies comportementales avancée grâce au **TinyML** (modèle de réseau de neurones quantifié int8 intégré dans FreeRTOS).
  * Déploiement de TrustZone (Cortex-M33 / STM32L5/U5) pour isoler le moteur cryptographique.
* **Questions :**
  * *« Merci pour votre attention. Avez-vous des questions ? »*
