/* SPDX-License-Identifier: MIT-0 */

#include "reg_access_mock.h"

#include <stddef.h>

#define REG_STORE_CAPACITY 64

struct reg_entry {
    uint32_t addr;
    uint32_t value;
    int used;
};

static struct reg_entry reg_store[REG_STORE_CAPACITY];

void reg_store_clear(void)
{
    size_t i;

    for (i = 0; i < REG_STORE_CAPACITY; i++)
        reg_store[i].used = 0;
}

uint32_t reg_read(uint32_t addr)
{
    size_t i;

    for (i = 0; i < REG_STORE_CAPACITY; i++) {
        if (reg_store[i].used && reg_store[i].addr == addr)
            return reg_store[i].value;
    }
    return 0u;
}

void reg_write(uint32_t addr, uint32_t value)
{
    size_t i;

    for (i = 0; i < REG_STORE_CAPACITY; i++) {
        if (reg_store[i].used && reg_store[i].addr == addr) {
            reg_store[i].value = value;
            return;
        }
    }
    for (i = 0; i < REG_STORE_CAPACITY; i++) {
        if (!reg_store[i].used) {
            reg_store[i].used = 1;
            reg_store[i].addr = addr;
            reg_store[i].value = value;
            return;
        }
    }
}
