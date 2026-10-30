/* SPDX-License-Identifier: MIT-0 */
/* C header compile test for optional_no_reset_column.md (default field reset 0). */

#include "c_header_test.h"
#include "reg_access_mock.h"
#include "regs.h"

static void test_ctrl_register(void)
{
    uint32_t value;

    printf("INFO: test_ctrl_register\n");

    reg_write(CSR_REGISTERS_CTRL_ADDR, CSR_REGISTERS_CTRL_RESET);
    value = reg_read(CSR_REGISTERS_CTRL_ADDR);
    CHECK(value == 0u);
    CHECK(CSR_REGISTERS_CTRL_ENABLE_GET(value) == 0u);
    CHECK(CSR_REGISTERS_CTRL_MODE_GET(value) == 0u);

    value = CSR_REGISTERS_CTRL_ENABLE_SET(value, 1u);
    value = CSR_REGISTERS_CTRL_MODE_SET(value, 2u);
    reg_write(CSR_REGISTERS_CTRL_ADDR, value);

    value = reg_read(CSR_REGISTERS_CTRL_ADDR);
    CHECK(CSR_REGISTERS_CTRL_ENABLE_GET(value) == 1u);
    CHECK(CSR_REGISTERS_CTRL_MODE_GET(value) == 2u);
}

int main(void)
{
    double start = c_header_test_monotonic_seconds();

    printf("INFO: optional-no-reset-column C header compile test starting\n");

    g_failures = 0;
    reg_store_clear();
    test_ctrl_register();

    return c_header_test_finish("optional-no-reset-column", start);
}
