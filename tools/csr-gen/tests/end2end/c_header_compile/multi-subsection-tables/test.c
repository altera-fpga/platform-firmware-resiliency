/* SPDX-License-Identifier: MIT-0 */
/* C header compile test for multi_subsection_tables.md (merged subsection tables). */

#include "c_header_test.h"
#include "reg_access_mock.h"
#include "regs.h"

static void test_ctrl_register(void)
{
    uint32_t value;

    printf("INFO: test_ctrl_register\n");

    reg_write(CSR_REGISTERS_CTRL_ADDR, CSR_REGISTERS_CTRL_RESET);
    value = reg_read(CSR_REGISTERS_CTRL_ADDR);
    CHECK(value == CSR_REGISTERS_CTRL_RESET);

    value = CSR_REGISTERS_CTRL_ENABLE_SET(value, 1u);
    reg_write(CSR_REGISTERS_CTRL_ADDR, value);

    value = reg_read(CSR_REGISTERS_CTRL_ADDR);
    CHECK(CSR_REGISTERS_CTRL_ENABLE_GET(value) == 1u);
}

static void test_events_register(void)
{
    uint32_t value;

    printf("INFO: test_events_register\n");

    reg_write(CSR_REGISTERS_EVENTS_ADDR, CSR_REGISTERS_EVENTS_RESET);
    value = reg_read(CSR_REGISTERS_EVENTS_ADDR);
    CHECK(value == CSR_REGISTERS_EVENTS_RESET);

    value = CSR_REGISTERS_EVENTS_PENDING_SET(value, 0x3cu);
    reg_write(CSR_REGISTERS_EVENTS_ADDR, value);

    value = reg_read(CSR_REGISTERS_EVENTS_ADDR);
    CHECK(CSR_REGISTERS_EVENTS_PENDING_GET(value) == 0x3cu);
}

int main(void)
{
    double start = c_header_test_monotonic_seconds();

    printf("INFO: multi-subsection-tables C header compile test starting\n");

    g_failures = 0;
    reg_store_clear();
    test_ctrl_register();
    test_events_register();

    return c_header_test_finish("multi-subsection-tables", start);
}
