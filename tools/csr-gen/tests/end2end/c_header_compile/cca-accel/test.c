/* SPDX-License-Identifier: MIT-0 */
/* C header compile test for cca_accel.md (CSR Registers). */

#include "c_header_test.h"
#include "reg_access_mock.h"
#include "regs.h"

static void test_wpref_control_register(void)
{
    uint32_t value;

    printf("INFO: test_wpref_control_register\n");

    reg_write(
        CSR_REGISTERS_WPREF_CONTROL_ADDR,
        CSR_REGISTERS_WPREF_CONTROL_RESET);
    value = reg_read(CSR_REGISTERS_WPREF_CONTROL_ADDR);
    CHECK(value == CSR_REGISTERS_WPREF_CONTROL_RESET);
    CHECK(CSR_REGISTERS_WPREF_CONTROL_RUN_GET(value) == 0u);
    CHECK(CSR_REGISTERS_WPREF_CONTROL_IRQ_EN_GET(value) == 0u);

    value = CSR_REGISTERS_WPREF_CONTROL_RUN_SET(value, 1u);
    value = CSR_REGISTERS_WPREF_CONTROL_IRQ_EN_SET(value, 1u);
    reg_write(CSR_REGISTERS_WPREF_CONTROL_ADDR, value);

    value = reg_read(CSR_REGISTERS_WPREF_CONTROL_ADDR);
    CHECK(CSR_REGISTERS_WPREF_CONTROL_RUN_GET(value) == 1u);
    CHECK(CSR_REGISTERS_WPREF_CONTROL_IRQ_EN_GET(value) == 1u);
}

static void test_wdisp_status_idle_reset(void)
{
    uint32_t value;

    printf("INFO: test_wdisp_status_idle_reset\n");

    reg_write(
        CSR_REGISTERS_WDISP_STATUS_ADDR,
        CSR_REGISTERS_WDISP_STATUS_RESET);
    value = reg_read(CSR_REGISTERS_WDISP_STATUS_ADDR);
    CHECK(value == CSR_REGISTERS_WDISP_STATUS_RESET);
    CHECK(value == 0x00000002u);
    CHECK(CSR_REGISTERS_WDISP_STATUS_STOPPED_IDLE_GET(value) == 1u);
    CHECK(CSR_REGISTERS_WDISP_STATUS_BUSY_GET(value) == 0u);
}

static void test_wpref_status_register(void)
{
    uint32_t value;

    printf("INFO: test_wpref_status_register\n");

    reg_write(
        CSR_REGISTERS_WPREF_STATUS_ADDR,
        CSR_REGISTERS_WPREF_STATUS_RESET);
    value = reg_read(CSR_REGISTERS_WPREF_STATUS_ADDR);
    CHECK(value == CSR_REGISTERS_WPREF_STATUS_RESET);
    CHECK(CSR_REGISTERS_WPREF_STATUS_IRQ_GET(value) == 0u);

    value = CSR_REGISTERS_WPREF_STATUS_IRQ_SET(value, 1u);
    reg_write(CSR_REGISTERS_WPREF_STATUS_ADDR, value);
    value = reg_read(CSR_REGISTERS_WPREF_STATUS_ADDR);
    CHECK(CSR_REGISTERS_WPREF_STATUS_IRQ_GET(value) == 1u);
}

int main(void)
{
    double start = c_header_test_monotonic_seconds();

    printf("INFO: cca-accel C header compile test starting\n");

    g_failures = 0;
    reg_store_clear();
    test_wpref_control_register();
    test_wdisp_status_idle_reset();
    test_wpref_status_register();

    return c_header_test_finish("cca-accel", start);
}
