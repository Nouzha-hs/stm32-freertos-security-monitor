#ifndef SCALER_PARAMS_H
#define SCALER_PARAMS_H

#define MODEL_INPUT_SIZE 15
#define NUM_SCALED_FEATURES 3
/* Ordre : Power_W, CPU_Usage_%, Mem_Usage_MB ; les 12 autres entrées sont binaires */
static const float scaler_mean[3] = {0.577698f, 43.209133f, 25.727079f};
static const float scaler_std[3]  = {0.297249f, 35.259857f, 14.417871f};

#endif
