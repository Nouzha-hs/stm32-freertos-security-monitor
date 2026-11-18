# Documentation & Ressources Visuelles

Ce dossier est destiné à stocker les diagrammes d'architecture, schémas de câblage et captures d'écran des essais.

## Sous-dossiers
- `putty_results/` : Déposez ici les captures d'écran de votre terminal série PuTTY montrant les logs :
  1. `normal_execution.png` : Jitter faible, 0 deadline miss.
  2. `attack_without_priority.png` : Dégradation avec deadline_miss = 202.
  3. `attack_detected_alert.png` : Détection du pic CPU (ALERT,100 puis ALERT,87) et retour à 1%.
- `diagrams/` : Schémas fonctionnels et organigrammes des tâches FreeRTOS.
