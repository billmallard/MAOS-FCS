#include <stdio.h>

#include "fcc_scheduler.h"

int main(void) {
    fcc_scheduler_t scheduler;
    uint32_t i;

    fcc_scheduler_init(&scheduler, 1000U, 250U, 50U);

    for (i = 0U; i < 20U; ++i) {
        fcc_scheduler_step(&scheduler);
        if (fcc_scheduler_should_run_inner(&scheduler) == 1U) {
            printf("tick=%lu inner\n", (unsigned long)scheduler.tick_count);
        }
        if (fcc_scheduler_should_run_outer(&scheduler) == 1U) {
            printf("tick=%lu outer\n", (unsigned long)scheduler.tick_count);
        }
    }

    return 0;
}
