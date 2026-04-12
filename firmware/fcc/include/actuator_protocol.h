#ifndef MAOS_ACTUATOR_PROTOCOL_H
#define MAOS_ACTUATOR_PROTOCOL_H

#include <stdint.h>

#define ACTUATOR_CMD_FRAME_LEN 18U
#define ACTUATOR_FB_FRAME_LEN 22U

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

typedef struct {
    uint8_t protocol_version;
    uint8_t actuator_id;
    uint8_t feedback_mode;
    uint8_t fault_flags;
    uint32_t sequence_echo;
    int16_t measured_position_norm_x10000;
    int16_t measured_rate_norm_per_s_x1000;
    uint16_t motor_current_a_x100;
    int16_t temperature_c_x10;
    uint16_t supply_voltage_v_x100;
} actuator_feedback_t;

uint32_t actuator_crc32(const uint8_t *data, uint32_t len);

uint8_t actuator_pack_command(
    const actuator_command_t *cmd,
    uint8_t out_frame[ACTUATOR_CMD_FRAME_LEN]
);

uint8_t actuator_unpack_command(
    const uint8_t frame[ACTUATOR_CMD_FRAME_LEN],
    actuator_command_t *out_cmd
);

uint8_t actuator_unpack_feedback(
    const uint8_t frame[ACTUATOR_FB_FRAME_LEN],
    actuator_feedback_t *out_fb
);

#endif
