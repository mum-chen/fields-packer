#include <stdint.h>

#include "reg_accessor.h"

void reg_write(uint16_t addr, uint32_t val)
{
	*((volatile uint32_t *)addr) = val;
}

uint32_t reg_read(uint16_t addr)
{
	return *((volatile uint32_t *)addr);
}

int main(void)
{
	int val = get_dev0_get();
	set_dev1_stop(1);
	set_dev1_set(val);
	set_dev1_stop(0);
}
