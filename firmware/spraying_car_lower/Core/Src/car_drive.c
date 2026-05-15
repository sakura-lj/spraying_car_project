#include "dac.h"
#include "OLED.h"
#include "Remote_control.h"
#include "gpio.h"
#include "car_drive.h"

extern volatile uint8_t is_open;
extern volatile uint8_t CH3, CH4, CH5, CH6, CH7;
volatile uint8_t direction_state = 0, spray_state = 0,vehicle_speed=0; // 0: 停止, 1: 前进, 2: 后退
volatile uint8_t uart_control_mode = 0; // 0: 遥控器控制, 1: 串口控制

void Car_Init(void) {
    HAL_DAC_Start(&hdac, DAC_CHANNEL_1);
}

/**
 * @brief  硬件层：直接设置DAC输出电压（不更新状态变量）
 * @param  duty: 电机速度，范围0-102
 * @retval 无
 */
static void hw_set_motor_speed(uint8_t duty) {
    double temp;
    if(duty == 1){temp = 0;}
    else if(duty >= 2 && duty <= 101){temp = 100 + (duty - 2) * 2;}
    else if(duty == 102){temp = 310;}
    else{temp = 0;} // 默认值，防止意外情况
    temp /= 100;  
    temp = temp * 4096 / 3.3;
    if (temp > 4096) {
        temp = 0;
    }
    HAL_DAC_SetValue(&hdac, DAC_CHANNEL_1, DAC_ALIGN_12B_R, (uint32_t)temp);
}

/**
 * @brief  硬件层：直接控制喷雾GPIO（不更新状态变量）
 * @param  state: 喷雾状态 0-关闭 1-开启
 * @retval 无
 */
static void hw_set_spray(uint8_t state) {
    if (state == 1) {
        HAL_GPIO_WritePin(GPIOE, GPIO_PIN_2, GPIO_PIN_SET); // 打开喷雾
    } else {
        HAL_GPIO_WritePin(GPIOE, GPIO_PIN_2, GPIO_PIN_RESET); // 关闭喷雾
    }
}

/**
 * @brief  硬件层：直接控制方向GPIO（不更新状态变量）
 * @param  direction: 方向 0-停止 1-前进 2-后退
 * @retval 无
 */
static void hw_set_direction(uint8_t direction) {
    if (direction == 0) {
        HAL_GPIO_WritePin(backward_GPIO_Port, backward_Pin, GPIO_PIN_RESET);
        HAL_GPIO_WritePin(forward_GPIO_Port, forward_Pin, GPIO_PIN_RESET);
    } else if (direction == 1) {
        HAL_GPIO_WritePin(backward_GPIO_Port, backward_Pin, GPIO_PIN_SET);
        HAL_GPIO_WritePin(forward_GPIO_Port, forward_Pin, GPIO_PIN_RESET);
    } else if (direction == 2) {
        HAL_GPIO_WritePin(backward_GPIO_Port, backward_Pin, GPIO_PIN_RESET);
        HAL_GPIO_WritePin(forward_GPIO_Port, forward_Pin, GPIO_PIN_SET);
    }
}
/**
 * @brief  控制层：设置电机速度（串口调用，更新状态并设置控制模式）
 * @param  duty: 电机速度，范围0-102
 * @retval 无
 */
void carSpeed_set(uint8_t duty) {
    vehicle_speed = duty; // 更新状态变量
    uart_control_mode = 1; // 标记为串口控制模式
    hw_set_motor_speed(duty); // 调用硬件层函数
}

/**
 * @brief  控制层：设置喷雾状态（串口调用，更新状态并设置控制模式）
 * @param  state: 喷雾状态 0-关闭 1-开启
 * @retval 无
 */
void spray_set(uint8_t state) {
    spray_state = state; // 更新状态变量
    uart_control_mode = 1; // 标记为串口控制模式
    hw_set_spray(state); // 调用硬件层函数
}

/**
 * @brief  控制层：设置方向（串口调用，更新状态并设置控制模式）
 * @param  direction: 方向 0-停止 1-前进 2-后退
 * @retval 无
 */
void direction_set(uint8_t direction) {
    direction_state = direction; // 更新状态变量
    uart_control_mode = 1; // 标记为串口控制模式
    hw_set_direction(direction); // 调用硬件层函数
}

/**
 * @brief  遥控器模式下的状态更新（直接更新状态和硬件，不触发串口控制模式）
 * @param  speed: 速度值
 * @param  direction: 方向值
 * @param  spray: 喷雾状态
 * @retval 无
 */
static void update_rc_control(uint8_t speed, uint8_t direction, uint8_t spray) {
    // 更新状态变量（不触发串口控制模式）
    vehicle_speed = speed;
    direction_state = direction;
    spray_state = spray;
    
    // 直接控制硬件
    hw_set_motor_speed(speed);
    hw_set_direction(direction);
    hw_set_spray(spray);
}

void speed_control(void) {
    static uint8_t prev_CH3 = 0;
    
    if (is_open == 1){
        CH3 = CH3_GetDuty();
        
        // 只有在遥控器控制模式下才处理遥控器逻辑
        if (uart_control_mode == 0) {
            // 在遥控器模式下，如果方向为停止状态，则速度也设为0
            if (direction_state == 0) {
                update_rc_control(0, direction_state, spray_state);
            }
            // 检测遥控器输入变化
            else if (CH3 != prev_CH3) {
                update_rc_control(CH3, direction_state, spray_state);
                
                // 显示调试信息
                #if DEBUG_MODE
                OLED_Printf(64,0,OLED_6X8,"RC:%04d", CH3);
                OLED_Update();
                #endif
                
                prev_CH3 = CH3; // 更新上一次的CH3值
            }
        } else {
            // 在串口控制模式下，检测遥控器是否有新的输入
            if (CH3 != prev_CH3) {
                uart_control_mode = 0; // 遥控器有输入时，切换为遥控器控制模式
                update_rc_control(CH3, direction_state, spray_state);
                
                // 显示调试信息
                #if DEBUG_MODE
                OLED_Printf(64,0,OLED_6X8,"RC:%04d", CH3);
                OLED_Update();
                #endif
                
                prev_CH3 = CH3; // 更新上一次的CH3值
            }
            // 如果没有遥控器输入变化，保持串口控制模式，不做任何操作
        }
    }else{
        update_rc_control(0, 0, 0); // 关闭所有功能
    }
}

void direction_control(void) {
    static uint8_t prev_CH5 = 0;
    
    if (is_open == 1) {
        CH5 = CH5_GetDuty();
        
        // 只有在遥控器控制模式下或检测到遥控器输入变化时才处理
        if (CH5 != prev_CH5) {
            uart_control_mode = 0; // 遥控器有输入时，切换为遥控器控制模式
            
            uint8_t new_direction = direction_state; // 默认保持当前方向
            
            if (CH5 == 51) {
                new_direction = 0; // 停止状态
            } else if (CH5 == 86 && direction_state == 0) {
                new_direction = 1; // 前进状态（只有在停止状态下才能切换）
            } else if (CH5 == 19 && direction_state == 0) {
                new_direction = 2; // 后退状态（只有在停止状态下才能切换）
            }
            
            // 使用统一的遥控器控制函数
            update_rc_control(vehicle_speed, new_direction, spray_state);
            
            prev_CH5 = CH5; // 更新上一次的CH5值
        }
        // 在串口控制模式下且没有遥控器输入变化时，不做任何操作
    }else{
        update_rc_control(0, 0, 0); // 关闭所有功能
    }
}

void spray_control(void) {
    static uint8_t prev_CH6 = 0;
    
    if (is_open == 1) {
        CH6 = CH6_GetDuty();
        
        // 只有检测到遥控器输入变化时才处理
        if (CH6 != prev_CH6) {
            uart_control_mode = 0; // 遥控器有输入时，切换为遥控器控制模式
            
            uint8_t new_spray_state = (CH6 >= 10) ? 1 : 0;
            
            // 使用统一的遥控器控制函数
            update_rc_control(vehicle_speed, direction_state, new_spray_state);
            
            prev_CH6 = CH6;
        }
        // 在串口控制模式下且没有遥控器输入变化时，不做任何操作
    }else{
        update_rc_control(0, 0, 0); // 关闭所有功能
    }
}

/**
 * @brief  获取当前控制模式
 * @retval 0-遥控器控制, 1-串口控制
 */
uint8_t get_control_mode(void) {
    return uart_control_mode;
}

/**
 * @brief  强制切换控制模式（用于调试或特殊情况）
 * @param  mode: 0-遥控器控制, 1-串口控制
 * @retval 无
 */
void set_control_mode(uint8_t mode) {
    uart_control_mode = (mode > 0) ? 1 : 0;
}

/**
 * @brief  紧急停止功能 - 立即停止所有运动和喷洒
 * @retval 无
 */
void emergency_stop(void) {
    // 立即停止所有硬件动作，不依赖状态变量
    
    // 1. 立即停止方向控制（最关键）
    HAL_GPIO_WritePin(backward_GPIO_Port, backward_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(forward_GPIO_Port, forward_Pin, GPIO_PIN_RESET);
    
    // 2. 立即设置最小速度
    HAL_DAC_SetValue(&hdac, DAC_CHANNEL_1, DAC_ALIGN_12B_R, 0);
    
    // 3. 立即关闭喷雾
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_2, GPIO_PIN_RESET);
    
    // 4. 更新状态变量确保一致性
    direction_state = 0;  // 停止
    vehicle_speed = 1;    // 最小速度
    spray_state = 0;      // 关闭喷雾
    uart_control_mode = 1; // 切换到串口控制模式防止遥控器干扰
    
    // 注意：转向控制需要通过步进电机函数处理，这里不直接控制
}


