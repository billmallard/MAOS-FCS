#include <stdint.h>
#include <stdio.h>

#include "actuator_protocol.h"

static int test_unpack_command_ok(void) {
    /* Vector generated from sim/actuator_codec.py */
    const uint8_t frame[ACTUATOR_CMD_FRAME_LEN] = {
        0x01, 0x03, 0x00, 0x03, 0x4d, 0x00, 0x00, 0x00,
        0xc4, 0x09, 0xdc, 0x05, 0x20, 0x03, 0x6f, 0x91,
        0x75, 0xe2
    };
    actuator_command_t cmd;

    if (actuator_unpack_command(frame, &cmd) == 0U) {
        return 0;
    }
    if (cmd.protocol_version != 1U || cmd.actuator_id != 3U || cmd.control_mode != 0U) {
        return 0;
    }
    if (cmd.sequence != 77U || cmd.target_position_norm_x10000 != 2500) {
        return 0;
    }
    if (cmd.target_rate_norm_per_s_x1000 != 1500U || cmd.max_effort_norm_x1000 != 800U) {
        return 0;
    }
    return 1;
}

static int test_unpack_feedback_ok(void) {
    /* Vector generated from sim/actuator_codec.py */
    const uint8_t frame[ACTUATOR_FB_FRAME_LEN] = {
        0x01, 0x03, 0x00, 0x00, 0x4d, 0x00, 0x00, 0x00,
        0x60, 0x09, 0x78, 0x05, 0xfa, 0x00, 0xc4, 0x01,
        0xe6, 0x0a, 0x46, 0x26, 0x4c, 0xd9
    };
    actuator_feedback_t fb;

    if (actuator_unpack_feedback(frame, &fb) == 0U) {
        return 0;
    }
    if (fb.protocol_version != 1U || fb.actuator_id != 3U || fb.feedback_mode != 0U) {
        return 0;
    }
    if (fb.sequence_echo != 77U || fb.measured_position_norm_x10000 != 2400) {
        return 0;
    }
    if (fb.measured_rate_norm_per_s_x1000 != 1400 || fb.motor_current_a_x100 != 250U) {
        return 0;
    }
    if (fb.temperature_c_x10 != 452 || fb.supply_voltage_v_x100 != 2790U) {
        return 0;
    }
    return 1;
}

static int test_crc_reject(void) {
    uint8_t frame[ACTUATOR_CMD_FRAME_LEN] = {
        0x01, 0x03, 0x00, 0x03, 0x4d, 0x00, 0x00, 0x00,
        0xc4, 0x09, 0xdc, 0x05, 0x20, 0x03, 0x6f, 0x91,
        0x75, 0xe2
    };
    actuator_command_t cmd;

    frame[2] ^= 0x01U;
    if (actuator_unpack_command(frame, &cmd) != 0U) {
        return 0;
    }
    return 1;
}

int main(void) {
    if (!test_unpack_command_ok()) {
        printf("test_unpack_command_ok FAILED\n");
        return 1;
    }
    if (!test_unpack_feedback_ok()) {
        printf("test_unpack_feedback_ok FAILED\n");
        return 1;
    }
    if (!test_crc_reject()) {
        printf("test_crc_reject FAILED\n");
        return 1;
    }

    printf("actuator protocol tests passed\n");
    return 0;
}
