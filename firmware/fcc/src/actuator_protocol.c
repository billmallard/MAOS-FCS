#include "actuator_protocol.h"

uint32_t actuator_crc32(const uint8_t *data, uint32_t len) {
    uint32_t crc = 0xFFFFFFFFU;
    uint32_t i;
    uint32_t j;

    if (data == 0) {
        return 0U;
    }

    for (i = 0U; i < len; ++i) {
        crc ^= (uint32_t)data[i];
        for (j = 0U; j < 8U; ++j) {
            if ((crc & 1U) != 0U) {
                crc = (crc >> 1U) ^ 0xEDB88320U;
            } else {
                crc >>= 1U;
            }
        }
    }
    return crc;
}

static void pack_u16_le(uint8_t *out, uint16_t value) {
    out[0] = (uint8_t)(value & 0xFFU);
    out[1] = (uint8_t)((value >> 8U) & 0xFFU);
}

static void pack_u32_le(uint8_t *out, uint32_t value) {
    out[0] = (uint8_t)(value & 0xFFU);
    out[1] = (uint8_t)((value >> 8U) & 0xFFU);
    out[2] = (uint8_t)((value >> 16U) & 0xFFU);
    out[3] = (uint8_t)((value >> 24U) & 0xFFU);
}

uint8_t actuator_pack_command(
    const actuator_command_t *cmd,
    uint8_t out_frame[18]
) {
    uint32_t crc;

    if (cmd == 0 || out_frame == 0) {
        return 0U;
    }

    out_frame[0] = cmd->protocol_version;
    out_frame[1] = cmd->actuator_id;
    out_frame[2] = cmd->control_mode;
    out_frame[3] = cmd->enable_flags;
    pack_u32_le(&out_frame[4], cmd->sequence);
    pack_u16_le(&out_frame[8], (uint16_t)cmd->target_position_norm_x10000);
    pack_u16_le(&out_frame[10], cmd->target_rate_norm_per_s_x1000);
    pack_u16_le(&out_frame[12], cmd->max_effort_norm_x1000);

    crc = actuator_crc32(out_frame, 14U);
    pack_u32_le(&out_frame[14], crc);
    return 1U;
}
