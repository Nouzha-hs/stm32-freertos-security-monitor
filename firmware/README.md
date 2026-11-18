# Firmware STM32 & FreeRTOS

Ce dossier contient l'implémentation embarquée sur microcontrôleur STM32 avec le système d'exploitation temps réel **FreeRTOS**.

## Architecture des tâches

1. **Tâche Critique (`critical_task.c`)**
   - Priorité : `osPriorityRealtime` (priorité maximale).
   - Période : 10 ms ou 20 ms.
   - Objectif : Traitement temps réel strict. Elle mesure en permanence son **jitter** (via le compteur de cycles DWT) et s'assure qu'aucun délai n'est dépassé (`deadline_miss = 0`).

2. **Tâche d'Attaque / Surcharge (`attack_sim.c`)**
   - Priorité : Modulable (`osPriorityBelowNormal` pour tester l'isolation de priorité, ou `osPriorityRealtime` pour tester la défaillance).
   - Objectif : Simule une attaque par déni de service (DDoS) ou une boucle infinie saturant le CPU à 100% pendant des salves de 2 secondes.

3. **Tâche de Surveillance & IDS (`cpu_monitor.c`)**
   - Priorité : `osPriorityAboveNormal`.
   - Objectif : Calcul de l'utilisation CPU globale (via `vApplicationIdleHook`).
   - Seuil d'alerte : si `CPU > 80%`, déclenche :
     - Alerte matérielle immédiate sur GPIO (Buzzer piézoélectrique ou LED).
     - Trame série UART vers le PC : `ALERT,100` ou `ALERT,87`.

## Matériel supporté
- Cartes de développement STM32 (ex: STM32F4-Discovery, NUCLEO-F401RE, Blue Pill STM32F103).
- Liaison série UART (115200 bauds, 8N1).
- Buzzer ou LED connectée sur un GPIO défini dans `security_tasks.h`.
