/**
  ******************************************************************************
  * @file    security_tasks.h
  * @brief   En-tête pour les tâches de sécurité et temps réel FreeRTOS.
  ******************************************************************************
  */

#ifndef INC_SECURITY_TASKS_H_
#define INC_SECURITY_TASKS_H_

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"
#include "cmsis_os.h"
#include <stdint.h>
#include <stdbool.h>

/* --- PARAMETRES DU SYSTEME TEMPS REEL --- */
#define CRITICAL_TASK_PERIOD_MS     10      /* Période de la tâche critique (ex: 10 ms) */
#define MONITOR_TASK_PERIOD_MS      500     /* Période d'évaluation du moniteur CPU (500 ms) */
#define CPU_ALERT_THRESHOLD_PCT     80      /* Seuil de déclenchement d'alerte CPU (%) */

/* --- CONFIGURATION MATERIELLE (GPIO ALERTE) --- */
#define BUZZER_GPIO_PORT            GPIOB
#define BUZZER_PIN                  GPIO_PIN_0

/* --- VARIABLES GLOBALES DE TELEMETRIE --- */
extern volatile uint32_t g_jitter_max_us;
extern volatile uint32_t g_deadline_miss_count;
extern volatile uint8_t  g_cpu_usage_pct;
extern volatile uint32_t g_idle_ticks;
extern volatile uint32_t g_idle_ref_ticks;
extern volatile bool     g_attack_active;

/* --- PROTOTYPES DES TÂCHES --- */
void StartCriticalTask(void *argument);
void StartAttackSimTask(void *argument);
void StartMonitorTask(void *argument);

/* --- FONCTION D'AIDE TEMPORISATION HAUTE PRECISION --- */
void DWT_Init(void);
uint32_t DWT_GetCycles(void);
uint32_t DWT_CyclesToMicroseconds(uint32_t cycles);

/* --- HOOK D'IDLE FREERTOS --- */
void Security_IdleHook(void);

#ifdef __cplusplus
}
#endif

#endif /* INC_SECURITY_TASKS_H_ */
