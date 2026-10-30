/* SPDX-License-Identifier: MIT-0 */
/* In-memory reg_read/reg_write for c_header_compile end-to-end tests. */

#ifndef REG_ACCESS_MOCK_H
#define REG_ACCESS_MOCK_H

#include <stdint.h>

void reg_store_clear(void);
uint32_t reg_read(uint32_t addr);
void reg_write(uint32_t addr, uint32_t value);

#endif /* REG_ACCESS_MOCK_H */
