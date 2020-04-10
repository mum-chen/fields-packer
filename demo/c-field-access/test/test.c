#include <stdint.h>

#include "reg_all.h"
#include "register.h"

static inline uint32_t paddr(uint16_t dev, uint16_t addr)
{
	return (dev << 16) | addr;
}

void pwrite(uint16_t dev, uint16_t addr, uint32_t val)
{
	*((volatile uint32_t *)paddr(dev, addr)) = val;
}

uint32_t pread(uint16_t dev, uint16_t addr)
{
	return *((volatile uint32_t *)paddr(dev, addr));
}

#define BUS_MAP_START 0x0000

int main(void)
{
	int val;
	/* demo for busmap */
	struct bus_map *bus_map = (struct bus_map *)(BUS_MAP_START);
	val = bus_map->r_config0.cfg0;
	bus_map->r_config1.cfg1 = val;

	/* demo for bus */
	val = register_field_fetch(DEVICE0_GET, dev0_get);
	register_field_apply(DEVICE0_SET, dev0_set, val);

	/* demo for peripheral */
	val = register_field_fetch(B_CFG2, bcfg2);
	register_field_apply(B_CFG0, bcfg0, val);

	return 0;
}
