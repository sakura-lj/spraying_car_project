#ifndef __TURN_H__
#define __TURN_H__

#include <stdint.h>

/* 函数声明 */
void Step_Motor_Init(void);
int32_t Calculate_Target_Position(uint8_t CH4_value);
void Step_Motor_Control(void);
void Step_Motor_Stop(void);
void Step_Motor_New_Run(void);
void set_target_position(uint8_t target);
uint8_t get_turn_cmd_position(void);
int32_t get_turn_target_encoder(void);
int32_t get_turn_encoder_position(void);
#endif
