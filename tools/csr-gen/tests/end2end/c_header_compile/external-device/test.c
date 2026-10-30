/* SPDX-License-Identifier: MIT-0 */
/* Compile and exercise csr-gen C header output for external-device. */

#include "c_header_test.h"
#include "reg_access_mock.h"
#include "regs.h"

static void test_status_register(void)
{
    uint32_t value;

    printf("INFO: test_status_register\n");

    reg_write(CSR_REGISTERS_STATUS_ADDR, 0x00000001u);
    value = reg_read(CSR_REGISTERS_STATUS_ADDR);
    CHECK(CSR_REGISTERS_STATUS_FLAG_GET(value) == 1u);
}

static void test_fifo_register(void)
{
    uint32_t value;

    printf("INFO: test_fifo_register\n");

    reg_write(CSR_REGISTERS_FIFO_ADDR, 0x00003400u);
    value = reg_read(CSR_REGISTERS_FIFO_ADDR);
    CHECK(CSR_REGISTERS_FIFO_LEVEL_GET(value) == 0x34u);

    value = CSR_REGISTERS_FIFO_DATA_SET(value, 0xabu);
    reg_write(CSR_REGISTERS_FIFO_ADDR, value);

    value = reg_read(CSR_REGISTERS_FIFO_ADDR);
    CHECK(CSR_REGISTERS_FIFO_DATA_GET(value) == 0xabu);
    CHECK(CSR_REGISTERS_FIFO_LEVEL_GET(value) == 0x34u);
}

static void test_mem_register(void)
{
    uint32_t value;

    printf("INFO: test_mem_register\n");

    value = CSR_REGISTERS_MEM_WINDOW_SET(0u, 0xdeadbeefu);
    reg_write(CSR_REGISTERS_MEM_ADDR, value);

    value = reg_read(CSR_REGISTERS_MEM_ADDR);
    CHECK(CSR_REGISTERS_MEM_WINDOW_GET(value) == 0xdeadbeefu);
}

static void test_rom_register(void)
{
    uint32_t value;

    printf("INFO: test_rom_register\n");

    reg_write(CSR_REGISTERS_ROM_ADDR, 0xcafebabeu);
    value = reg_read(CSR_REGISTERS_ROM_ADDR);
    CHECK(CSR_REGISTERS_ROM_IMAGE_GET(value) == 0xcafebabeu);
}

static void test_wbuf_register(void)
{
    uint32_t value;

    printf("INFO: test_wbuf_register\n");

    value = CSR_REGISTERS_WBUF_BUFFER_SET(0u, 0x12345678u);
    reg_write(CSR_REGISTERS_WBUF_ADDR, value);

    value = reg_read(CSR_REGISTERS_WBUF_ADDR);
    CHECK(CSR_REGISTERS_WBUF_BUFFER_GET(value) == 0x12345678u);
}

int main(void)
{
    double start = c_header_test_monotonic_seconds();

    printf("INFO: external-device C header compile test starting\n");

    g_failures = 0;
    reg_store_clear();
    test_status_register();
    test_fifo_register();
    test_mem_register();
    test_rom_register();
    test_wbuf_register();

    return c_header_test_finish("external-device", start);
}
