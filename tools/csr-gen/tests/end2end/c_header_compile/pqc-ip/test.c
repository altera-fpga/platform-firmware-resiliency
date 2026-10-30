/* SPDX-License-Identifier: MIT-0 */
/* C header compile test: pqc_ip.csv -> Markdown -> header. */

#include "c_header_test.h"
#include "reg_access_mock.h"
#include "regs.h"

static void test_hci_reset(void)
{
    uint32_t value;

    printf("INFO: test_hci_reset\n");

    value = PQC_IP_HCI_RESET_RESET_SET(0u, 1u);
    reg_write(PQC_IP_HCI_RESET_ADDR, value);

    value = reg_read(PQC_IP_HCI_RESET_ADDR);
    CHECK(PQC_IP_HCI_RESET_RESET_GET(value) == 1u);
}

static void test_hci_status(void)
{
    uint32_t value;

    printf("INFO: test_hci_status\n");

    reg_write(PQC_IP_HCI_STATUS_ADDR, 0x00000005u);
    value = reg_read(PQC_IP_HCI_STATUS_ADDR);
    CHECK(PQC_IP_HCI_STATUS_ACCEL_STATUS_GET(value) == 5u);
}

static void test_hci_interrupt_status(void)
{
    uint32_t value;

    printf("INFO: test_hci_interrupt_status\n");

    reg_write(PQC_IP_HCI_INTERRUPT_STATUS_ADDR, 0x00000007u);
    value = reg_read(PQC_IP_HCI_INTERRUPT_STATUS_ADDR);
    CHECK(PQC_IP_HCI_INTERRUPT_STATUS_TRANSITION_TO_SUCCESS_GET(value) == 1u);
    CHECK(PQC_IP_HCI_INTERRUPT_STATUS_TRANSITION_TO_ERROR_GET(value) == 1u);
    CHECK(PQC_IP_HCI_INTERRUPT_STATUS_INIT_DONE_GET(value) == 1u);

    value = PQC_IP_HCI_INTERRUPT_STATUS_TRANSITION_TO_SUCCESS_SET(value, 0u);
    value = PQC_IP_HCI_INTERRUPT_STATUS_INIT_DONE_SET(value, 0u);
    reg_write(PQC_IP_HCI_INTERRUPT_STATUS_ADDR, value);

    value = reg_read(PQC_IP_HCI_INTERRUPT_STATUS_ADDR);
    CHECK(PQC_IP_HCI_INTERRUPT_STATUS_TRANSITION_TO_SUCCESS_GET(value) == 0u);
    CHECK(PQC_IP_HCI_INTERRUPT_STATUS_TRANSITION_TO_ERROR_GET(value) == 1u);
    CHECK(PQC_IP_HCI_INTERRUPT_STATUS_INIT_DONE_GET(value) == 0u);
}

static void test_hci_interrupt_control(void)
{
    uint32_t value;

    printf("INFO: test_hci_interrupt_control\n");

    value = PQC_IP_HCI_INTERRUPT_CONTROL_TRANSITION_TO_SUCCESS_IRQ_SET(0u, 1u);
    value = PQC_IP_HCI_INTERRUPT_CONTROL_INIT_DONE_IRQ_SET(value, 1u);
    reg_write(PQC_IP_HCI_INTERRUPT_CONTROL_ADDR, value);

    value = reg_read(PQC_IP_HCI_INTERRUPT_CONTROL_ADDR);
    CHECK(PQC_IP_HCI_INTERRUPT_CONTROL_TRANSITION_TO_SUCCESS_IRQ_GET(value) == 1u);
    CHECK(PQC_IP_HCI_INTERRUPT_CONTROL_INIT_DONE_IRQ_GET(value) == 1u);
}

static void test_hci_accelerator_ip_id(void)
{
    uint32_t value;

    printf("INFO: test_hci_accelerator_ip_id\n");

    reg_write(PQC_IP_HCI_ACCELERATOR_IP_ID_ADDR, 0x00000002u);
    value = reg_read(PQC_IP_HCI_ACCELERATOR_IP_ID_ADDR);
    CHECK(PQC_IP_HCI_ACCELERATOR_IP_ID_HCI_ACCELERATOR_IP_ID_GET(value) == 2u);
}

static void test_hci_param_mem_base_addr(void)
{
    uint32_t value;

    printf("INFO: test_hci_param_mem_base_addr\n");

    value = PQC_IP_HCI_PARAM_MEM_BASE_ADDR_HCI_PARAM_MEM_BASE_ADDR_SET(0u, 0x3fc00u);
    reg_write(PQC_IP_HCI_PARAM_MEM_BASE_ADDR_ADDR, value);

    value = reg_read(PQC_IP_HCI_PARAM_MEM_BASE_ADDR_ADDR);
    CHECK(PQC_IP_HCI_PARAM_MEM_BASE_ADDR_HCI_PARAM_MEM_BASE_ADDR_GET(value) == 0x3fc00u);
}

static void test_hci_param_mem_data(void)
{
    uint32_t value;

    printf("INFO: test_hci_param_mem_data\n");

    value = PQC_IP_HCI_PARAM_MEM_DATA_HCI_PARAM_MEM_DATA_SET(0u, 0xa5a55a5au);
    reg_write(PQC_IP_HCI_PARAM_MEM_DATA_ADDR, value);

    value = reg_read(PQC_IP_HCI_PARAM_MEM_DATA_ADDR);
    CHECK(PQC_IP_HCI_PARAM_MEM_DATA_HCI_PARAM_MEM_DATA_GET(value) == 0xa5a55a5au);
}

int main(void)
{
    double start = c_header_test_monotonic_seconds();

    printf("INFO: pqc-ip C header compile test starting (CSV -> Markdown -> header)\n");

    g_failures = 0;
    reg_store_clear();
    test_hci_reset();
    test_hci_status();
    test_hci_interrupt_status();
    test_hci_interrupt_control();
    test_hci_accelerator_ip_id();
    test_hci_param_mem_base_addr();
    test_hci_param_mem_data();

    return c_header_test_finish("pqc-ip", start);
}
