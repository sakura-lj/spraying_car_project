/**
 * @file    upper.c
 * @brief   上位机通信模块，支持调试模式和上机模式
 * @note    修改DEBUG_MODE宏来切换模式：
 *          DEBUG_MODE = 1: 调试模式，启用OLED显示（适用于开发调试）
 *          DEBUG_MODE = 0: 上机模式，禁用OLED显示（适用于实际运行）
 */

#include "upper.h"
#include "usart.h"
#include "turn.h"
#include "main.h"
#include "car_drive.h"
#include "usbd_cdc_if.h"
#include "OLED.h"  // 添加OLED头文件
#include <string.h>   // strlen()
#include <stdio.h>    // snprintf()

// 调试模式控制宏 - 设置为1启用OLED调试显示，设置为0禁用OLED
#define DEBUG_MODE 1  // 1: 调试模式(使用OLED), 0: 上机模式(不使用OLED)

// OLED操作宏定义 - 根据调试模式控制OLED显示
#if DEBUG_MODE
    // 辅助宏：通过 USB CDC 发送格式化文本（忽略 BUSY，调试不阻塞）
    #define DEBUG_CDC_SEND(str, len)  CDC_Transmit_FS((uint8_t*)(str), (uint16_t)(len))

    // OLED 清屏 + USB 发送清除标记
    #define DEBUG_OLED_Clear()  do { \
        OLED_Clear(); \
        DEBUG_CDC_SEND("[OLED CLEAR]\r\n", 14); \
    } while(0)

    // OLED 显示字符串 + USB 发送相同文本
    #define DEBUG_OLED_ShowString(x, y, str)  do { \
        OLED_ShowString(x, y, str, OLED_6X8); \
        DEBUG_CDC_SEND(str, strlen(str)); \
        DEBUG_CDC_SEND("\r\n", 2); \
    } while(0)

    // OLED 显示数字 + USB 发送十进制文本
    #define DEBUG_OLED_ShowNum(x, y, num, len)  do { \
        OLED_ShowNum(x, y, num, len, OLED_6X8); \
        char _dbg_buf[24]; \
        int _dbg_n = snprintf(_dbg_buf, sizeof(_dbg_buf), "%d\r\n", (int)(num)); \
        if (_dbg_n > 0) DEBUG_CDC_SEND(_dbg_buf, (uint16_t)_dbg_n); \
    } while(0)

    // OLED 显示十六进制 + USB 发送 "0xXX\r\n"
    #define DEBUG_OLED_ShowHexNum(x, y, num, len)  do { \
        OLED_ShowHexNum(x, y, num, len, OLED_6X8); \
        char _dbg_buf[24]; \
        int _dbg_n = snprintf(_dbg_buf, sizeof(_dbg_buf), "0x%X\r\n", (unsigned int)(num)); \
        if (_dbg_n > 0) DEBUG_CDC_SEND(_dbg_buf, (uint16_t)_dbg_n); \
    } while(0)

    // OLED 刷新（USB 不发送——此调用过于频繁，会淹没串口输出）
    #define DEBUG_OLED_Update()  OLED_Update()

    // OLED 区域刷新（USB 不发送——同上）
    #define DEBUG_OLED_UpdateArea(x, y, w, h)  OLED_UpdateArea(x, y, w, h)
#else
    #define DEBUG_OLED_Clear()                          ((void)0)
    #define DEBUG_OLED_ShowString(x, y, str)            ((void)0)
    #define DEBUG_OLED_ShowNum(x, y, num, len)          ((void)0)
    #define DEBUG_OLED_ShowHexNum(x, y, num, len)       ((void)0)
    #define DEBUG_OLED_Update()                         ((void)0)
    #define DEBUG_OLED_UpdateArea(x, y, w, h)           ((void)0)
#endif

// 数据包标识符
#define PACKET_HEAD 0xAA  // 数据包头
#define PACKET_TAIL 0x55  // 数据包尾

// 命令类型定义
#define CMD_SPRAY_CONTROL     0x01  // 喷洒控制命令
#define CMD_SPEED_CONTROL     0x02  // 速度控制命令
#define CMD_DIRECTION_CONTROL 0x03  // 方向控制命令
#define CMD_TURN_CONTROL      0x04  // 转向控制命令
#define CMD_STATUS_QUERY      0xFF  // 状态查询命令
#define CMD_STATUS_RESPONSE   0x05  // 状态响应命令

// 数据解析器与接收变量
PacketParser parser;
uint8_t received_byte;

// 接收缓冲区 - 定义为全局变量以便外部访问
#define RXBUFFER_LEN 128
uint8_t rxBuffer[RXBUFFER_LEN];
const uint16_t RXBUFFER_LEN_CONST = RXBUFFER_LEN;  // 提供给外部的长度常量

#define TXBUFFER_LEN (BUFFER_SIZE + 6)
static uint8_t txBuffer[TXBUFFER_LEN];
static uint8_t txPendingBuffer[TXBUFFER_LEN];
static volatile uint8_t txBusy = 0;
static volatile uint8_t txPending = 0;
static volatile uint16_t txPendingLength = 0;

// 车辆状态控制变量
extern volatile uint8_t direction_state; // 方向状态：0-停止，1-前进，2-后退
extern volatile uint8_t spray_state;     // 喷洒状态：0-关闭，1-开启
extern volatile uint8_t is_open;         // 电源状态：0-关闭，1-开启
extern volatile uint8_t vehicle_speed;   // 车辆速度：1-102

/**
 * @brief  初始化上位机通信模块
 * @retval 无
 */
void upper_init(void) {
    // 开启DMA接收
    HAL_UARTEx_ReceiveToIdle_DMA(&huart1, rxBuffer, RXBUFFER_LEN);
    // 初始化解析器状态
    parser.state = WAIT_HEAD; 
    
    // 显示初始化信息（仅在调试模式下）
    DEBUG_OLED_Clear();
    DEBUG_OLED_ShowString(0, 0, "UART COMM INIT");
    DEBUG_OLED_ShowString(0, 12, "Waiting for");
    DEBUG_OLED_ShowString(0, 24, "Upper Computer");
    DEBUG_OLED_ShowString(0, 36, "Ready...");
    DEBUG_OLED_Update();
}

/**
 * @brief  打包数据到指定格式的数据包
 * @param  Data: 输出参数，用于存储打包后的数据
 * @param  type: 命令类型
 * @param  data: 数据内容指针
 * @param  length: 数据内容长度
 * @retval 打包后的数据长度，错误返回-1
 */
int packData(uint8_t* Data, uint8_t type, uint8_t* data, int length) { 
    // 检查数据长度是否超出限制
    if (length > BUFFER_SIZE) { 
        return -1; 
    }
    
    // 创建临时缓冲区
    uint8_t buffer[BUFFER_SIZE + 6]; 
    uint8_t checksum = 0;
    
    // 填充数据包头部信息
    buffer[0] = PACKET_HEAD; 
    buffer[1] = type; 
    buffer[2] = length; 
    
    // 复制数据内容
    for (int i = 0; i < length; i++) {
        buffer[3 + i] = data[i];
    }
    
    // 计算校验和
    for (int i = 0; i < length; i++) { 
        checksum += data[i]; 
    } 
    
    // 添加校验和和尾部
    buffer[length + 3] = checksum; 
    buffer[length + 4] = PACKET_TAIL; 
    
    // 将临时缓冲区复制到输出
    for (int i = 0; i < length + 5; i++) {
        Data[i] = buffer[i];
    }
    
    return length + 5; 
}

/**
 * @brief  发送数据到上位机
 * @param  data: 要发送的数据指针
 * @param  length: 数据长度
 * @retval 发送的数据长度，错误返回-1
 */
int sendData(uint8_t* data, int length) {
    if (data == NULL || length <= 0 || length > TXBUFFER_LEN) {
        return -1;
    }

    // USB CDC 调试：将 STM32 发出的原始数据镜像到虚拟串口。
    // 若 CDC 正忙则由 CDC_Transmit_FS 直接返回，不阻塞 USART1 DMA 发送。
    CDC_Transmit_FS(data, (uint16_t)length);

    if (txBusy) {
        memcpy(txPendingBuffer, data, (size_t)length);
        txPendingLength = (uint16_t)length;
        txPending = 1;
        return length;
    }

    memcpy(txBuffer, data, (size_t)length);
    txBusy = 1;

    // 使用DMA方式发送数据
    HAL_StatusTypeDef status = HAL_UART_Transmit_DMA(&huart1, txBuffer, (uint16_t)length);
    if (status != HAL_OK) {
        txBusy = 0;
        if (status == HAL_BUSY) {
            memcpy(txPendingBuffer, data, (size_t)length);
            txPendingLength = (uint16_t)length;
            txPending = 1;
            return length;
        }
        return -1; // 发送失败返回-1
    }
    return length;
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart->Instance != USART1) {
        return;
    }

    if (txPending) {
        uint16_t length = txPendingLength;
        memcpy(txBuffer, txPendingBuffer, (size_t)length);
        txPending = 0;
        txPendingLength = 0;

        HAL_StatusTypeDef status = HAL_UART_Transmit_DMA(&huart1, txBuffer, length);
        if (status == HAL_OK) {
            txBusy = 1;
        } else {
            txBusy = 0;
        }
    } else {
        txBusy = 0;
    }
}

/**
 * @brief  显示数据包解析错误信息
 * @param  error_type: 错误类型
 * @param  error_value: 错误值
 * @retval 无
 */
static void display_parse_error(const char* error_type, uint8_t error_value)
{
    DEBUG_OLED_Clear();
    DEBUG_OLED_ShowString(0, 0, "PARSE ERROR:");
    DEBUG_OLED_ShowString(0, 12, (char*)error_type);
    DEBUG_OLED_ShowString(0, 24, "Value:");
    DEBUG_OLED_ShowHexNum(36, 24, error_value, 2);
    DEBUG_OLED_ShowString(0, 36, "Restart Parse");
    DEBUG_OLED_Update();
}

/**
 * @brief  显示数据包接收进度
 * @param  state: 当前状态
 * @param  progress: 进度信息
 * @retval 无
 */
static void display_parse_progress(const char* state, uint8_t progress)
{
    // 只在屏幕第一行显示接收状态，不清除整个屏幕（仅在调试模式下）
    DEBUG_OLED_ShowString(0, 0, "RX:");
    DEBUG_OLED_ShowString(18, 0, (char*)state);
    if (progress > 0) {
        DEBUG_OLED_ShowNum(60, 0, progress, 2);
    }
    DEBUG_OLED_UpdateArea(0, 0, 128, 12); // 只更新第一行，6x8字体高度为8，加4像素间距
}

/**
 * @brief  处理接收到的数据包中的命令
 * @param  type: 命令类型
 * @param  data: 命令数据
 * @param  length: 数据长度
 * @retval 无
 */
static void processData(uint8_t type, uint8_t* data, int length)
{
    if (length < 1) {
        // 数据长度不足，显示错误信息（仅在调试模式下）
        DEBUG_OLED_Clear();
        DEBUG_OLED_ShowString(0, 0, "CMD ERROR:");
        DEBUG_OLED_ShowString(0, 12, "Data Length < 1");
        DEBUG_OLED_Update();
        return;
    }

    // 清除屏幕并显示命令接收提示（仅在调试模式下）
    DEBUG_OLED_Clear();
    DEBUG_OLED_ShowString(0, 0, "CMD Received:");
    
    switch (type) {
        case CMD_SPRAY_CONTROL: // 喷洒控制命令
            is_open = 1; // 串口控制时自动开启电源
            spray_set(data[0]); // 0:关闭 1:开启
            DEBUG_OLED_ShowString(0, 12, "SPRAY:");
            if (data[0] == 0) {
                DEBUG_OLED_ShowString(36, 12, "OFF");
            } else {
                DEBUG_OLED_ShowString(36, 12, "ON");
            }
            DEBUG_OLED_ShowString(0, 24, "Status: OK");
            break;
            
        case CMD_SPEED_CONTROL: // 速度控制命令
            is_open = 1; // 串口控制时自动开启电源
            // 当设置速度>0且当前为停止状态时，自动设置为前进状态
            if (data[0] > 0 && direction_state == 0) {
                direction_set(1); // 设置为前进状态
            }
            carSpeed_set(data[0]); // 1-102档位
            DEBUG_OLED_ShowString(0, 12, "SPEED:");
            DEBUG_OLED_ShowNum(36, 12, data[0], 3);
            DEBUG_OLED_ShowString(0, 24, "Status: OK");
            // 显示自动设置的方向状态
            if (data[0] > 0 && direction_state == 1) {
                DEBUG_OLED_ShowString(0, 36, "Auto FWD");
            }
            break;
            
        case CMD_DIRECTION_CONTROL: // 方向控制命令
            is_open = 1; // 串口控制时自动开启电源
            direction_set(data[0]); // 0:停止 1:前进 2:后退
            DEBUG_OLED_ShowString(0, 12, "DIR:");
            switch(data[0]) {
                case 0:
                    DEBUG_OLED_ShowString(24, 12, "STOP");
                    break;
                case 1:
                    DEBUG_OLED_ShowString(24, 12, "FORWARD");
                    break;
                case 2:
                    DEBUG_OLED_ShowString(24, 12, "BACK");
                    break;
                default:
                    DEBUG_OLED_ShowString(24, 12, "UNKNOWN");
                    break;
            }
            DEBUG_OLED_ShowString(0, 24, "Status: OK");
            break;
            
        case CMD_TURN_CONTROL: // 转向控制命令
            is_open = 1; // 串口控制时自动开启电源
            set_target_position(data[0]); // 1-101档位
            DEBUG_OLED_ShowString(0, 12, "TURN:");
            DEBUG_OLED_ShowNum(30, 12, data[0], 3);
            if (data[0] < 51) {
                DEBUG_OLED_ShowString(54, 12, "L");
            } else if (data[0] > 51) {
                DEBUG_OLED_ShowString(54, 12, "R");
            } else {
                DEBUG_OLED_ShowString(54, 12, "C");
            }
            DEBUG_OLED_ShowString(0, 24, "Status: OK");
            break;
            
        case CMD_STATUS_QUERY: // 状态查询命令
            send_status_data(); // 发送当前状态数据
            DEBUG_OLED_ShowString(0, 12, "STATUS QUERY");
            DEBUG_OLED_ShowString(0, 24, "Sending...");
            break;

        default:
            DEBUG_OLED_ShowString(0, 12, "UNKNOWN CMD:");
            DEBUG_OLED_ShowHexNum(0, 24, type, 2);
            DEBUG_OLED_ShowString(0, 36, "Status: ERROR");
            break;
    }
    
    // 显示时间戳（仅在调试模式下）
    DEBUG_OLED_ShowString(72, 36, "RX");
    
    // 更新OLED显示（仅在调试模式下）
    DEBUG_OLED_Update();
}

/**
 * @brief  数据包解析状态机
 * @param  parser: 解析器指针
 * @param  byte: 当前接收到的字节
 * @retval 无
 */
static void parseData(PacketParser* parser, uint8_t byte) {
    switch (parser->state) {
        case WAIT_HEAD:  // 等待包头
            if (byte == PACKET_HEAD) {
                parser->state = WAIT_TYPE;
                display_parse_progress("HEAD", 0);
            }
            break;       
            
        case WAIT_TYPE:  // 等待命令类型
            parser->type = byte;
            parser->state = WAIT_LENGTH;
            display_parse_progress("TYPE", parser->type);
            break;
            
        case WAIT_LENGTH:  // 等待数据长度
            parser->length = byte;
            parser->dataIndex = 0;
            parser->checksum = 0;
            display_parse_progress("LEN", parser->length);
            
            if (parser->length > BUFFER_SIZE) {
                // 数据长度超出限制
                display_parse_error("LEN > MAX", parser->length);
                parser->state = WAIT_HEAD;
                break;
            }
            
            if (parser->length > 0) {
                parser->state = WAIT_DATA;
            } else {
                parser->state = WAIT_CHECK;
            }
            break;
            
        case WAIT_DATA:  // 等待数据内容
            parser->data[parser->dataIndex] = byte;
            parser->checksum += byte;
            parser->dataIndex++;
            display_parse_progress("DATA", parser->dataIndex);
            
            if (parser->dataIndex >= parser->length) {
                parser->state = WAIT_CHECK;
            }
            break;        
            
        case WAIT_CHECK:  // 等待校验和
            if (byte == parser->checksum) {
                parser->state = WAIT_TAIL;
                display_parse_progress("CHK OK", parser->checksum);
            } else {
                display_parse_error("CHK ERR", byte);
                DEBUG_OLED_ShowString(0, 48, "Exp:");
                DEBUG_OLED_ShowHexNum(24, 48, parser->checksum, 2);
                DEBUG_OLED_Update();
                parser->state = WAIT_HEAD;  // 校验和错误，重新开始
            }
            break;
            
        case WAIT_TAIL:  // 等待包尾
            if (byte == PACKET_TAIL) {
                // 数据包接收完成，处理命令
                display_parse_progress("TAIL OK", 0);
                processData(parser->type, parser->data, parser->length);
            } else {
                display_parse_error("TAIL ERR", byte);
            }
            parser->state = WAIT_HEAD;  // 无论如何，回到等待包头状态
            break;
    }
}

/**
 * @brief  UART接收完成回调函数
 * @param  huart: UART句柄
 * @param  Size: 接收到的数据大小
 * @retval 无
 */
void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Size){
    if (huart->Instance == USART1) {
        // USB CDC 调试：将 USART1 收到的原始数据镜像到虚拟串口。
        // 若 CDC 正忙则由 CDC_Transmit_FS 直接返回，调试转发允许丢帧。
        uint8_t cdc_result = CDC_Transmit_FS(rxBuffer, Size);
        (void)cdc_result;

        // 处理接收到的每个字节
        for (uint8_t i = 0; i < Size; i++) {
            received_byte = rxBuffer[i];
            parseData(&parser, received_byte);
        }
        
        // 重新启动DMA接收
        HAL_UARTEx_ReceiveToIdle_DMA(huart, rxBuffer, RXBUFFER_LEN); 
    }
}

/**
 * @brief  发送状态数据到上位机
 * @retval 无
 */
void send_status_data(void) {
    // 准备状态数据
    uint8_t data[4];
    data[0] = spray_state;     // 喷洒状态：0-关闭，1-开启
    data[1] = vehicle_speed;   // 车辆速度：1-102
    data[2] = direction_state; // 方向状态：0-停止，1-前进，2-后退
    data[3] = is_open;         // 电源状态：0-关闭，1-开启

    // 打包并发送状态数据
    uint8_t packet[BUFFER_SIZE + 6];
    int length = packData(packet, CMD_STATUS_RESPONSE, data, 4);
    
    if (length > 0) {
        int result = sendData(packet, length);
        if (result > 0) {
            // 发送成功，更新OLED显示（仅在调试模式下）
            DEBUG_OLED_ShowString(0, 48, "TX: SUCCESS");
            DEBUG_OLED_UpdateArea(0, 48, 128, 12);
        } else {
            // 发送失败（仅在调试模式下显示）
            DEBUG_OLED_Clear();
            DEBUG_OLED_ShowString(0, 0, "TX ERROR:");
            DEBUG_OLED_ShowString(0, 12, "Failed to send");
            DEBUG_OLED_ShowString(0, 24, "status data");
            DEBUG_OLED_Update();
        }
    } else {
        // 打包失败（仅在调试模式下显示）
        DEBUG_OLED_Clear();
        DEBUG_OLED_ShowString(0, 0, "PACK ERROR:");
        DEBUG_OLED_ShowString(0, 12, "Failed to pack");
        DEBUG_OLED_ShowString(0, 24, "status data");
        DEBUG_OLED_Update();
    }
}
