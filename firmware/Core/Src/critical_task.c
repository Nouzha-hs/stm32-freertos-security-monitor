/**
  ******************************************************************************
  * @file    critical_task.c
  * @brief   Implémentation de la tâche critique temps réel sous FreeRTOS.
  *          Mesure du jitter et détection des dépassements d'échéances (deadlines).
  ******************************************************************************
  */

#include "security_tasks.h"
#include <stdio.h>

/* Variables globales exportées */
volatile uint32_t g_jitter_max_us = 0;
volatile uint32_t g_deadline_miss_count = 0;

/**
  * @brief Initialise le compteur de cycles DWT (Data Watchpoint and Trace).
  */
void DWT_Init(void) {
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
    DWT->CYCCNT = 0;
}

uint32_t DWT_GetCycles(void) {
    return DWT->CYCCNT;
}

uint32_t DWT_CyclesToMicroseconds(uint32_t cycles) {
    return (cycles / (SystemCoreClock / 1000000));
}

/**
  * @brief Tâche critique (Priorité maximale : osPriorityRealtime).
  *        Exécute un traitement périodique strict et mesure le jitter.
  */
void StartCriticalTask(void *argument) {
    TickType_t xLastWakeTime;
    const TickType_t xFrequency = pdMS_TO_TICKS(CRITICAL_TASK_PERIOD_MS);

    uint32_t expected_cycles_per_period = (SystemCoreClock / 1000) * CRITICAL_TASK_PERIOD_MS;
    uint32_t last_cycles = DWT_GetCycles();

    xLastWakeTime = xTaskGetTickCount();

    for (;;) {
        /* Attente de la prochaine période stricte */
        vTaskDelayUntil(&xLastWakeTime, xFrequency);

        uint32_t current_cycles = DWT_GetCycles();
        uint32_t elapsed_cycles = current_cycles - last_cycles;
        last_cycles = current_cycles;

        /* Calcul du Jitter */
        int32_t delta_cycles = (int32_t)elapsed_cycles - (int32_t)expected_cycles_per_period;
        if (delta_cycles < 0) {
            delta_cycles = -delta_cycles;
        }

        uint32_t jitter_us = DWT_CyclesToMicroseconds((uint32_t)delta_cycles);
        if (jitter_us > g_jitter_max_us) {
            g_jitter_max_us = jitter_us;
        }

        /* Vérification du dépassement d'échéance (deadline miss) */
        /* Si le temps d'exécution ou le retard dépasse la période allouée */
        if (jitter_us > (CRITICAL_TASK_PERIOD_MS * 1000)) {
            g_deadline_miss_count++;
        }

        /* Simulation d'un traitement critique (ex: contrôle capteur ou moteur) */
        for (volatile int i = 0; i < 200; i++) {
            __NOP();
        }
    }
}
