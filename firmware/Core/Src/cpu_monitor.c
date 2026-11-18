/**
  ******************************************************************************
  * @file    cpu_monitor.c
  * @brief   Tâche de surveillance de charge CPU, détection d'anomalie par seuil
  *          et émission d'alertes matérielles (GPIO) et réseau/série (UART).
  ******************************************************************************
  */

#include "security_tasks.h"
#include <stdio.h>
#include <string.h>

/* Déclaration externe de la liaison UART configurée par CubeMX */
extern UART_HandleTypeDef huart2;

volatile uint8_t  g_cpu_usage_pct = 0;
volatile uint32_t g_idle_ticks = 0;
volatile uint32_t g_idle_ref_ticks = 0; /* Nombre maximal de ticks idle mesuré à vide */

/**
  * @brief Hook d'inactivité de FreeRTOS.
  *        Incrémente un compteur à chaque fois que le processeur n'a rien à faire.
  */
void Security_IdleHook(void) {
    g_idle_ticks++;
}

/**
  * @brief Tâche de surveillance périodique.
  */
void StartMonitorTask(void *argument) {
    char uart_buf[128];
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(MONITOR_TASK_PERIOD_MS);

    /* Étalonnage initial de la tâche d'inactivité au repos pendant 1 période */
    vTaskDelay(pdMS_TO_TICKS(1000));
    g_idle_ticks = 0;
    vTaskDelay(xFrequency);
    g_idle_ref_ticks = g_idle_ticks;
    if (g_idle_ref_ticks == 0) {
        g_idle_ref_ticks = 1; /* Prévention division par 0 */
    }

    for (;;) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);

        uint32_t current_idle = g_idle_ticks;
        g_idle_ticks = 0;

        /* Calcul du pourcentage d'utilisation CPU */
        if (current_idle >= g_idle_ref_ticks) {
            g_cpu_usage_pct = 0;
        } else {
            g_cpu_usage_pct = (uint8_t)(100 - ((current_idle * 100) / g_idle_ref_ticks));
            if (g_cpu_usage_pct > 100) {
                g_cpu_usage_pct = 100;
            }
        }

        /* Test du seuil d'alerte */
        if (g_cpu_usage_pct >= CPU_ALERT_THRESHOLD_PCT) {
            /* 1. Alerte matérielle : Déclenchement du Buzzer / LED */
            HAL_GPIO_WritePin(BUZZER_GPIO_PORT, BUZZER_PIN, GPIO_PIN_SET);

            /* 2. Trame d'alerte prioritaire pour le script Python */
            snprintf(uart_buf, sizeof(uart_buf), "ALERT,%d\r\n", g_cpu_usage_pct);
            HAL_UART_Transmit(&huart2, (uint8_t *)uart_buf, strlen(uart_buf), 100);

            /* 3. Ligne de détail formatée (identique aux captures PuTTY) */
            snprintf(uart_buf, sizeof(uart_buf), 
                     "cpu=%d%% heap=%lu jitter_max=%lu us deadline_miss=%lu\r\n",
                     g_cpu_usage_pct,
                     (unsigned long)xPortGetFreeHeapSize(),
                     (unsigned long)g_jitter_max_us,
                     (unsigned long)g_deadline_miss_count);
            HAL_UART_Transmit(&huart2, (uint8_t *)uart_buf, strlen(uart_buf), 100);
        } else {
            /* Extinction du Buzzer / LED */
            HAL_GPIO_WritePin(BUZZER_GPIO_PORT, BUZZER_PIN, GPIO_PIN_RESET);

            /* Log périodique en état normal */
            snprintf(uart_buf, sizeof(uart_buf), 
                     "cpu=%d%% idle=%lu ref=%lu jitter_max=%lu us deadline_miss=%lu\r\n",
                     g_cpu_usage_pct,
                     (unsigned long)current_idle,
                     (unsigned long)g_idle_ref_ticks,
                     (unsigned long)g_jitter_max_us,
                     (unsigned long)g_deadline_miss_count);
            HAL_UART_Transmit(&huart2, (uint8_t *)uart_buf, strlen(uart_buf), 100);
        }
    }
}
