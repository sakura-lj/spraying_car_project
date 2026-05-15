#include "stm32f4xx_hal.h"
#include "tim.h"
#include "main.h"

// 通用初始化函数
void TIM_IC_Init(TIM_HandleTypeDef* htim) {
    HAL_TIM_IC_Start(htim, TIM_CHANNEL_1);
    HAL_TIM_IC_Start(htim, TIM_CHANNEL_2);
}

// 通用获取占空比函数
uint8_t GetDuty(TIM_HandleTypeDef* htim) {
    return (__HAL_TIM_GET_COMPARE(htim, TIM_CHANNEL_2) - 1000) / 10;   // 频率
    // return (__HAL_TIM_GET_COMPARE(htim, TIM_CHANNEL_2));   // 频率
}

void CH3_Init(void) {
    TIM_IC_Init(&htim9);
}

void CH4_Init(void) {
    TIM_IC_Init(&htim12);
}

void CH5_Init(void) {
    TIM_IC_Init(&htim2);
}

void CH6_Init(void) {
    TIM_IC_Init(&htim3);
}

void CH7_Init(void) {
    TIM_IC_Init(&htim4);
}


void CH_Init(void) {
    TIM_IC_Init(&htim3);
    TIM_IC_Init(&htim2);
    TIM_IC_Init(&htim12);
    TIM_IC_Init(&htim9);
    TIM_IC_Init(&htim4);
}

uint8_t CH3_GetDuty(void) {
    return GetDuty(&htim9);
}

uint8_t CH4_GetDuty(void) {
    return GetDuty(&htim12);
}

uint8_t CH5_GetDuty(void) {
    return GetDuty(&htim2);
}

uint8_t CH6_GetDuty(void) {
    return GetDuty(&htim3);
}

uint8_t CH7_GetDuty(void) {
    return GetDuty(&htim4);
}

