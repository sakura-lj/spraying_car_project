#include "main.h"
#include "turn.h"
#include "tim.h"
#include "Encoder.h"
#include <stdlib.h>
#include <stdbool.h>
#include "OLED.h"
#include "Remote_control.h"
extern volatile uint8_t is_open;   // 0: 关闭, 1: 打开
/* 全局变量 */
static volatile int32_t target_position     = 0;  // 目标位置
static volatile int32_t current_position    = 0;  // 当前位置
static volatile int32_t differ_position     = 0;  // 当前位置与目标位置的步数差值 因为电机为4000细分，同时编码器也为4000细分，所以一个脉冲编码器就会变化一个位置
static volatile uint8_t motor_running       = 0;  // 电机运行状态
static volatile uint8_t using_CH4           = 51; // 当前CH4值，默认为中间值
static volatile uint32_t motor_speed        = 0;  // 当前电机速度，可动态调整
static volatile uint32_t last_encoder_value = 0;  // 上次编码器值，用于计算速度

/* PID控制相关参数 */
#define PID_KP         0.5f  // 比例系数
#define PID_KI         0.00f // 积分系数
#define PID_KD         0.1f  // 微分系数
#define PID_MAX_OUTPUT 50000  // PID最大输出限制

static float pid_error      = 0; // 当前误差
static float pid_last_error = 0; // 上次误差
static float pid_integral   = 0; // 积分项
static float pid_derivative = 0; // 微分项
static float pid_output     = 0; // PID输出值


/* 加减速控制相关参数 */
#define ACCEL_RATE       50    // 加速率 (Hz/每个中断周期)
#define DECEL_RATE       100   // 减速率 (Hz/每个中断周期)
#define MIN_SPEED        5000   // 最小速度 (Hz)
#define MAX_SPEED        80000 // 最大速度 (Hz)
#define DECEL_START_DIFF 200   // 开始减速的位置差值

/* 定义步进电机方向 */
#define CAR_LIFT  GPIO_PIN_RESET  // 对应脉宽51-101 车轮往左
#define CAR_RIGHT GPIO_PIN_SET    // 对应脉宽1-51  车轮往右
// 当前转动方向

static volatile uint8_t using_direction = 0; // 0:左 1:右

/* 电机控制相关变量 */
#define PWM_DUTY_CYCLE 50   // PWM占空比(%)

/**
 * @brief  初始化步进电机参数
 * @retval 无
 */
void Step_Motor_Init(void)
{
    /* 计算ARR值 - TIM频率为72MHz/72=1MHz */
    uint16_t arr = 1000000 / MIN_SPEED - 1;

    /* 设置定时器参数 */
    htim8.Instance->PSC = 72 - 1; // PSC=72，分频系数
    htim8.Instance->ARR = arr;    // ARR值

    /* 设置CCR值，对应占空比 */
    htim8.Instance->CCR1 = (arr + 1) * PWM_DUTY_CYCLE / 100;

    /* 启用ARR和CCR预装载 */
    htim8.Instance->CR1 |= TIM_CR1_ARPE;      // 使能ARR预装载
    htim8.Instance->CCMR1 |= TIM_CCMR1_OC1PE; // 使能CCR1预装载
}

/**
 * @brief  根据CH4值计算目标位置
 * @param  CH4_value: 遥控器CH4通道的值(1-101)
 * @retval 编码器目标位置
 */
int32_t Calculate_Target_Position(uint8_t CH4_value)
{
    return (int32_t)(((int16_t)CH4_value - 51) * 500);
}

/**
 * @brief  更新电机速度，调整TIM8的ARR和CCR值
 * @param  speed: 新的电机速度 (Hz)
 * @retval 无
 */
void Update_Motor_Speed(uint32_t speed)
{
    if (speed < MIN_SPEED) speed = MIN_SPEED;
    if (speed > MAX_SPEED) speed = MAX_SPEED;

    uint16_t arr = 1000000 / speed - 1;

    /* 更新定时器参数 */
    htim8.Instance->ARR  = arr;
    htim8.Instance->CCR1 = (arr + 1) * PWM_DUTY_CYCLE / 100;

    motor_speed = speed;
}

/**
 * @brief  计算PID控制输出
 * @param  target: 目标位置
 * @param  current: 当前位置
 * @retval PID输出值
 */
float Calculate_PID(int32_t target, int32_t current)
{
    pid_error = target - current;
    pid_integral += pid_error;
    pid_derivative = pid_error - pid_last_error;

    /* 积分限幅 */
    if (pid_integral > 1000) pid_integral = 1000;
    if (pid_integral < -1000) pid_integral = -1000;

    /* 计算PID输出 */
    float output = PID_KP * pid_error + PID_KI * pid_integral + PID_KD * pid_derivative;

    /* 输出限幅 */
    if (output > PID_MAX_OUTPUT) output = PID_MAX_OUTPUT;
    if (output < -PID_MAX_OUTPUT) output = -PID_MAX_OUTPUT;

    pid_last_error = pid_error;
    return output;
}

/**
 * @brief  当电机到位后通过函数来控制电机时，通过这个函数启动电机
 * @retval 无
 */
void Step_Motor_New_Run(void)
{
    GPIO_PinState direction = (differ_position > 0) ? CAR_LIFT : CAR_RIGHT;
    using_direction         = direction;
    HAL_GPIO_WritePin(step_dir_GPIO_Port, step_dir_Pin, direction);

    /* 设置初始速度为低速 */
    Update_Motor_Speed(MIN_SPEED);

    /* 重置PID控制器 */
    pid_integral   = 0;
    pid_last_error = 0;

    /* 设置电机运行状态 */
    motor_running = 1;

    /* 启动TIM8 PWM输出 */
    HAL_TIM_PWM_Start_IT(&htim8, TIM_CHANNEL_1);
}

/**
 * @brief  控制步进电机根据CH4值转到对应位置，当电机正在运行是通过中断来控制电机，当电机停止时通过此函数来控制电机
 * @param  CH4_value: 遥控器CH4通道的值
 * @retval 无
 */
void Step_Motor_Control(void)
{
    // 滤波，只有3次CH4的值都相等时才会更新
    //  static uint8_t CH4_buffer[3] = {51, 51, 51};  // 保存最近5次的CH4值，初始为中间值51
    //  static uint8_t buffer_index = 0;              // 缓冲区索引
    //  static uint8_t CH4_value = 51;               // 稳定后的CH4值
    //  CH4_buffer[buffer_index] = CH4;
    //  buffer_index = (buffer_index + 1) % 3;        // 循环更新缓冲区索引
    //  //滤波 检查三个值是否相等
    //  if(CH4_buffer[0] == CH4_buffer[1] && CH4_buffer[1] == CH4_buffer[2]){
    //      CH4_value = CH4_buffer[0];
    //  }else{
    //      return;
    //  }

    // 滤波 检查五个值是否相等
    /*bool values_equal = true;
    for (int i = 1; i < 3; i++) {
        if (CH4_buffer[0] != CH4_buffer[i]) {
            values_equal = false;
            break;
        }
    }
    if (values_equal) {
        CH4_value = CH4_buffer[0];        // 获取稳定后的值
    } else {
        return;  // 五个值不全部相等，不更新
    }*/
   //判断is_open的值，决定是否需要转动电机
    uint8_t CH4_value = CH4_GetDuty(); // 获取CH4的值
    if (is_open == 0) {
        // 如果继电器关闭，直接返回，不需要转动电机
        CH4_value = 51; // 设置为中间值
    }
    // 如果CH4值没有变化，不需要往下运行了，通过中断来控制
    if (CH4_value == using_CH4) {
        return;
    }
    if (motor_running) {
        Step_Motor_Stop();
    }
    /* 更新当前CH4值 */
    using_CH4 = CH4_value;
    set_target_position(using_CH4);
}

void set_target_position(uint8_t target)
{
    /* 获取当前编码器位置 */
    current_position = Get_Encoder_Value();
    /* 计算目标位置 */
    target_position = Calculate_Target_Position(target);
    /* 计算步数差值 */
    differ_position = target_position - current_position;
    /* 如果足够小，不需要转动 */
    if (abs(differ_position) <= 5) {
        return;
    }
    /* 启动电机 */
    Step_Motor_New_Run();
}

/**
 * @brief  紧急停止步进电机
 * @retval 无
 */
void Step_Motor_Stop(void)
{
    /* 停止TIM8 PWM输出 */
    HAL_TIM_PWM_Stop_IT(&htim8, TIM_CHANNEL_1);

    /* 重置电机运行状态 */
    motor_running = 0;
}

/**
 * @brief  TIM8pwm中断回调函数
 * @retval 无
 */
void HAL_TIM_PWM_PulseFinishedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM8) {
        /* 获取当前编码器位置 */
        current_position = Get_Encoder_Value();

        /* 计算到目标位置的实际步数差值 */
        differ_position = target_position - current_position;
        uint32_t abs_diff = abs(differ_position);
        /* 如果距离目标位置足够接近，停止电机 */
        if (abs_diff <= 2 && motor_speed <= MIN_SPEED + ACCEL_RATE * 2) {
            HAL_TIM_PWM_Stop_IT(&htim8, TIM_CHANNEL_1);
            motor_running = 0;
            // 重置PID控制器
            pid_integral   = 0;
            pid_last_error = 0;
            return;
        }

        /* 计算PID输出 */
        pid_output = Calculate_PID(target_position, current_position);

        /* 根据PID输出决定方向和调整速度 */
        GPIO_PinState direction;
        if (pid_output > 0) {
            direction = CAR_LIFT;
        } else {
            direction  = CAR_RIGHT;
            pid_output = -pid_output; // 取绝对值用于调速
        }

        /* 方向变化时，先减速再切换方向 */
        if (direction != using_direction) {
            // 速度低于阈值后再切换方向，防止机械冲击
            if (motor_speed <= MIN_SPEED * 1.5) {
                HAL_GPIO_WritePin(step_dir_GPIO_Port, step_dir_Pin, direction);
                using_direction = direction;
            } else {
                // 方向需要切换但速度仍高，先减速
                Update_Motor_Speed(motor_speed - DECEL_RATE * 2);
                return;
            }
        }

        /* 使用PID输出直接调速 */
        
        
        // 计算基于PID的目标速度
        uint32_t pid_target_speed;
        
        // 将PID输出映射到速度范围
        pid_target_speed = MIN_SPEED + (pid_output * (MAX_SPEED - MIN_SPEED) / PID_MAX_OUTPUT);
        
        // 加减速控制，在PID目标速度基础上考虑位置差
        if (abs_diff < DECEL_START_DIFF) {
            // 接近目标位置，限制最高速度
            uint32_t pos_max_speed = MIN_SPEED + (abs_diff * (MAX_SPEED - MIN_SPEED) / DECEL_START_DIFF);
            if (pid_target_speed > pos_max_speed) {
                pid_target_speed = pos_max_speed;  // 不要超过基于位置的最高速度
            }
        }
        
        // 平滑调速 - 逐步接近目标速度
        if (motor_speed < pid_target_speed) {
            Update_Motor_Speed(motor_speed + ACCEL_RATE);
        } else if (motor_speed > pid_target_speed) {
            Update_Motor_Speed(motor_speed - DECEL_RATE);
        }
    }
}
