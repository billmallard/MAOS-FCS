#include "fcc_scheduler.h"

static uint32_t safe_div(uint32_t a, uint32_t b) {
    if (b == 0U) {
        return 0U;
    }
    return a / b;
}

void fcc_scheduler_init(
    fcc_scheduler_t *scheduler,
    uint32_t tick_hz,
    uint32_t inner_loop_hz,
    uint32_t outer_loop_hz
) {
    if (scheduler == 0) {
        return;
    }

    scheduler->tick_hz = tick_hz;
    scheduler->inner_loop_hz = inner_loop_hz;
    scheduler->outer_loop_hz = outer_loop_hz;
    scheduler->tick_count = 0U;
}

void fcc_scheduler_step(fcc_scheduler_t *scheduler) {
    if (scheduler == 0) {
        return;
    }
    scheduler->tick_count += 1U;
}

uint8_t fcc_scheduler_should_run_inner(const fcc_scheduler_t *scheduler) {
    uint32_t every_n;
    if (scheduler == 0) {
        return 0U;
    }

    every_n = safe_div(scheduler->tick_hz, scheduler->inner_loop_hz);
    if (every_n == 0U) {
        return 0U;
    }
    return (scheduler->tick_count % every_n) == 0U ? 1U : 0U;
}

uint8_t fcc_scheduler_should_run_outer(const fcc_scheduler_t *scheduler) {
    uint32_t every_n;
    if (scheduler == 0) {
        return 0U;
    }

    every_n = safe_div(scheduler->tick_hz, scheduler->outer_loop_hz);
    if (every_n == 0U) {
        return 0U;
    }
    return (scheduler->tick_count % every_n) == 0U ? 1U : 0U;
}
