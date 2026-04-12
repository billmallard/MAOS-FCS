#ifndef MAOS_ACTUATOR_PROTOCOL_H
#define MAOS_ACTUATOR_PROTOCOL_H

#include <stdint.h>

#define ACTUATOR_CMD_FRAME_LEN 18U
#define ACTUATOR_FB_FRAME_LEN  22U

/* Fault flag bit masks — match Python FaultFlags bit assignments in actuator_codec.py */
#define ACTUATOR_FAULT_OVERCURRENT        0x01U
#define ACTUATOR_FAULT_OVERTEMPERATURE    0x02U
#define ACTUATOR_FAULT_POSITION_MISMATCH  0x04U
#define ACTUATOR_FAULT_COMM_TIMEOUT       0x08U

/* Default monitoring thresholds — match ActuatorHealthThresholds defaults in sim/actuator_runtime.py */
#define ACTUATOR_TEMP_LIMIT_X10         ((int16_t)950)   /* 95.0 °C */
#define ACTUATOR_POS_ERROR_LIMIT_X10000 ((uint16_t)2000) /* normalised 0.20 */

/* Degradation reason codes returned by actuator_evaluate_feedback() */
typedef enum {
    ACTUATOR_DEGRADE_NONE              = 0,
    ACTUATOR_DEGRADE_POSITION_MISMATCH = 1,
    ACTUATOR_DEGRADE_OVERTEMPERATURE   = 2,
    ACTUATOR_DEGRADE_COMM_TIMEOUT      = 3,
    ACTUATOR_DEGRADE_MULTI_FAULT       = 4
} actuator_degrade_reason_t;

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

/**
 * Evaluate a decoded feedback struct and return a degradation reason code.
 *
 * Checks (in priority order): overtemperature (bit + threshold), position
 * error (arithmetic + bit), comm_timeout bit.  Returns MULTI_FAULT when
 * more than one condition is active simultaneously.
 *
 * @param fb                        Decoded feedback struct (must not be NULL).
 * @param expected_position_x10000  Commanded position scaled x10000.
 * @param position_error_limit_x10000  Acceptable position error scaled x10000.
 * @return  Degradation reason or ACTUATOR_DEGRADE_NONE.
 */
actuator_degrade_reason_t actuator_evaluate_feedback(
    const actuator_feedback_t *fb,
    int16_t expected_position_x10000,
    uint16_t position_error_limit_x10000
);

#endif
