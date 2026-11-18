/**
  ******************************************************************************
  * @file    attack_sim.c
  * @brief   Simulation d'attaque par déni de service (DDoS) / saturation CPU.
  ******************************************************************************
  */

#include "security_tasks.h"

volatile bool g_attack_active = false;

/**
  * @brief Tâche de simulation d'attaque.
  *        Alterne entre phases de repos et phases d'attaque (saturation CPU pendant 2s).
  * 
  * Note d'expérience :
  * - Si priorité = osPriorityBelowNormal : Le CPU monte à 100%, mais la tâche critique
  *   n'est pas perturbée (deadline_miss = 0). L'attaque est "invisible" sans seuil CPU !
  * - Si priorité = osPriorityRealtime ou supérieure à la tâche critique :
  *   La tâche critique est étouffée -> deadline_miss grimpe en flèche.
  */
void StartAttackSimTask(void *argument) {
    /* Délai initial avant la première attaque */
    vTaskDelay(pdMS_TO_TICKS(5000));

    for (;;) {
        /* Phase de repos : 10 secondes */
        g_attack_active = false;
        vTaskDelay(pdMS_TO_TICKS(10000));

        /* Phase d'attaque : Saturation CPU pendant 2000 ms */
        g_attack_active = true;
        TickType_t attack_start = xTaskGetTickCount();
        const TickType_t attack_duration = pdMS_TO_TICKS(2000);

        while ((xTaskGetTickCount() - attack_start) < attack_duration) {
            /* Boucle intensive de calcul mathématique simulant une surcharge */
            volatile uint32_t val = 12345;
            for (int i = 0; i < 1000; i++) {
                val = (val * 1664525 + 1013904223);
            }
        }

        g_attack_active = false;
    }
}
