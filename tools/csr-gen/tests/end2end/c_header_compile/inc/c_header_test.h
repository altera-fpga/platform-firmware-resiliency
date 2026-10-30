/* SPDX-License-Identifier: MIT-0 */
/* Common helpers for c_header_compile test programs. */

#ifndef C_HEADER_TEST_H
#define C_HEADER_TEST_H

#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdio.h>
#include <time.h>

extern int g_failures;

#define CHECK(expr)                                                            \
    do {                                                                       \
        if (!(expr)) {                                                         \
            fprintf(stderr, "  FAIL: %s:%d: %s\n", __FILE__, __LINE__, #expr); \
            g_failures++;                                                      \
        }                                                                      \
    } while (0)

static inline double c_header_test_monotonic_seconds(void)
{
    struct timespec ts;

    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

static inline int c_header_test_finish(const char *suite_name, double start)
{
    double elapsed = c_header_test_monotonic_seconds() - start;
    int rc;

    if (g_failures == 0) {
        printf("INFO: result: PASS (%.3f s)\n", elapsed);
        rc = 0;
    } else {
        printf("INFO: result: FAIL (%d check(s) failed, %.3f s)\n", g_failures, elapsed);
        rc = 1;
    }
    (void)suite_name;
    return rc;
}

#endif /* C_HEADER_TEST_H */
