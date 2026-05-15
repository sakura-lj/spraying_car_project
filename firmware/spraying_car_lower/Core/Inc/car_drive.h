#ifndef __car_drive_H__
#define __car_drive_H__

#include <stdint.h>

// 声明外部变量
extern volatile uint8_t uart_control_mode; // 0: 遥控器控制, 1: 串口控制

// 初始化函数
void Car_Init(void);

// 串口控制接口（会更新状态并设置控制模式）
void carSpeed_set(uint8_t duty);
void spray_set(uint8_t state);
void direction_set(uint8_t direction);

// 遥控器控制函数（定期调用）
void speed_control(void);
void direction_control(void);
void spray_control(void);

// 状态查询和控制模式管理
uint8_t get_control_mode(void);
void set_control_mode(uint8_t mode);

// 紧急停止功能
void emergency_stop(void);


#endif
