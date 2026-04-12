#ifndef MAOS_ACTUATOR_PROTOCOL_H
#define MAOS_ACTUATOR_PROTOCOL_H

#include <stdint.h>

typedef struct {
    uint8_t protocol_version;
    uint8_t actuator_id;
    uint8_t control_mode;
    uint8_t enable_flags;
    uint32_t sequence;
    int16_t target_position_norm_x10000;
    uint16_t target_rate_norm_per_s_x1000;
    uint16_t max_effort_norm_x1000;
} actuator_command_t;

uint32_t actuator_crc32(const uint8_t *data, uint32_t len);

uint8_t actuator_pack_command(
    const actuator_command_t *cmd,
    uint8_t out_frame[18]
);

#endif
