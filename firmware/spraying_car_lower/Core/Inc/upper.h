#ifndef __UPPER_H__
#define __UPPER_H__

#include "main.h"

#define PACKET_HEAD 0xAA
#define PACKET_TAIL 0x55
#define BUFFER_SIZE 128

typedef enum {
    WAIT_HEAD,
    WAIT_TYPE,
    WAIT_LENGTH,
    WAIT_DATA,
    WAIT_CHECK,
    WAIT_TAIL
} ParseState;

typedef struct {
    ParseState state;
    uint8_t type;
    uint8_t length;
    uint8_t data[BUFFER_SIZE];
    uint8_t checksum;
    int dataIndex;
} PacketParser;


void upper_init(void);
int sendData(uint8_t* data, int length);
void send_imu_data(void);
void send_status_data(void);
/* 扩展状态包 byte[5] 返回最近一次 UART 转向命令，byte[20:22] 临时返回 ext_status_seq。 */
void send_ext_status_data(void);
#endif
