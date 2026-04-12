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

static uint16_t unpack_u16_le(const uint8_t *in) {
    return (uint16_t)((uint16_t)in[0] | ((uint16_t)in[1] << 8U));
}

static int16_t unpack_i16_le(const uint8_t *in) {
    return (int16_t)unpack_u16_le(in);
}

static uint32_t unpack_u32_le(const uint8_t *in) {
    return ((uint32_t)in[0]) |
           ((uint32_t)in[1] << 8U) |
           ((uint32_t)in[2] << 16U) |
           ((uint32_t)in[3] << 24U);
}

uint8_t actuator_pack_command(
    const actuator_command_t *cmd,
    uint8_t out_frame[ACTUATOR_CMD_FRAME_LEN]
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

uint8_t actuator_unpack_command(
    const uint8_t frame[ACTUATOR_CMD_FRAME_LEN],
    actuator_command_t *out_cmd
) {
    uint32_t crc_expected;
    uint32_t crc_actual;

    if (frame == 0 || out_cmd == 0) {
        return 0U;
    }

    crc_expected = unpack_u32_le(&frame[14]);
    crc_actual = actuator_crc32(frame, 14U);
    if (crc_actual != crc_expected) {
        return 0U;
    }

    out_cmd->protocol_version = frame[0];
    out_cmd->actuator_id = frame[1];
    out_cmd->control_mode = frame[2];
    out_cmd->enable_flags = frame[3];
    out_cmd->sequence = unpack_u32_le(&frame[4]);
    out_cmd->target_position_norm_x10000 = unpack_i16_le(&frame[8]);
    out_cmd->target_rate_norm_per_s_x1000 = unpack_u16_le(&frame[10]);
    out_cmd->max_effort_norm_x1000 = unpack_u16_le(&frame[12]);
    return 1U;
}

uint8_t actuator_unpack_feedback(
    const uint8_t frame[ACTUATOR_FB_FRAME_LEN],
    actuator_feedback_t *out_fb
) {
    uint32_t crc_expected;
    uint32_t crc_actual;

    if (frame == 0 || out_fb == 0) {
        return 0U;
    }

    crc_expected = unpack_u32_le(&frame[18]);
    crc_actual = actuator_crc32(frame, 18U);
    if (crc_actual != crc_expected) {
        return 0U;
    }

    out_fb->protocol_version = frame[0];
    out_fb->actuator_id = frame[1];
    out_fb->feedback_mode = frame[2];
    out_fb->fault_flags = frame[3];
    out_fb->sequence_echo = unpack_u32_le(&frame[4]);
    out_fb->measured_position_norm_x10000 = unpack_i16_le(&frame[8]);
    out_fb->measured_rate_norm_per_s_x1000 = unpack_i16_le(&frame[10]);
    out_fb->motor_current_a_x100 = unpack_u16_le(&frame[12]);
    out_fb->temperature_c_x10 = unpack_i16_le(&frame[14]);
    out_fb->supply_voltage_v_x100 = unpack_u16_le(&frame[16]);
    return 1U;
}

actuator_degrade_reason_t actuator_evaluate_feedback(
    const actuator_feedback_t *fb,
    int16_t expected_position_x10000,
    uint16_t position_error_limit_x10000
) {
    uint8_t fault_count = 0U;
    actuator_degrade_reason_t reason = ACTUATOR_DEGRADE_NONE;
    int32_t pos_err;

    if (fb == 0) {
        return ACTUATOR_DEGRADE_NONE;
    }

    /* Position mismatch: arithmetic check OR reported fault bit */
    pos_err = (int32_t)fb->measured_position_norm_x10000
              - (int32_t)expected_position_x10000;
    if (pos_err < 0) {
        pos_err = -pos_err;
    }
    if ((uint32_t)pos_err > (uint32_t)position_error_limit_x10000
            || (fb->fault_flags & ACTUATOR_FAULT_POSITION_MISMATCH) != 0U) {
        reason = ACTUATOR_DEGRADE_POSITION_MISMATCH;
        fault_count++;
    }

    /* Overtemperature: threshold check OR reported fault bit */
    if (fb->temperature_c_x10 >= ACTUATOR_TEMP_LIMIT_X10
            || (fb->fault_flags & ACTUATOR_FAULT_OVERTEMPERATURE) != 0U) {
        reason = ACTUATOR_DEGRADE_OVERTEMPERATURE;
        fault_count++;
    }

    /* Comm timeout: reported fault bit only (counter is maintained externally) */
    if ((fb->fault_flags & ACTUATOR_FAULT_COMM_TIMEOUT) != 0U) {
        reason = ACTUATOR_DEGRADE_COMM_TIMEOUT;
        fault_count++;
    }

    if (fault_count > 1U) {
        return ACTUATOR_DEGRADE_MULTI_FAULT;
    }
    return reason;
}
