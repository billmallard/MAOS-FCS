#ifndef MAOS_FCC_SCHEDULER_H
#define MAOS_FCC_SCHEDULER_H

#include <stdint.h>

typedef struct {
    uint32_t tick_hz;
    uint32_t inner_loop_hz;
    uint32_t outer_loop_hz;
    uint32_t tick_count;
} fcc_scheduler_t;

void fcc_scheduler_init(
    fcc_scheduler_t *scheduler,
    uint32_t tick_hz,
    uint32_t inner_loop_hz,
    uint32_t outer_loop_hz
);

void fcc_scheduler_step(fcc_scheduler_t *scheduler);

uint8_t fcc_scheduler_should_run_inner(const fcc_scheduler_t *scheduler);
uint8_t fcc_scheduler_should_run_outer(const fcc_scheduler_t *scheduler);

#endif
