#include "Encoder.h"
#include "main.h"
#include "tim.h"

void Encoder_open(void)
{
    // 启动编码器
    HAL_TIM_Encoder_Start(&htim5, TIM_CHANNEL_ALL);
}


int16_t Get_Encoder_Value(void)
{
    // 获取编码器的值
    return (int16_t)__HAL_TIM_GET_COUNTER(&htim5);
}
