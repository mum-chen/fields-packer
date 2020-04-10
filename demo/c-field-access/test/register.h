#ifndef __REGISTER_H__
#define __REGISTER_H__

#define _register_read(name)	__reg_read_##name()
#define _register_write(name, val)	__reg_write_##name(val)

#define REG(name)	R_##name

#define register_fetch(name) ((REG(name))_register_read(name))
#define register_apply(name, reg) do { \
	REG(name) _x; \
	typeof(reg) _y; \
	(void) (&_x == &_y); \
	_register_write(name, reg.val); \
} while(0)

#define register_create(r, v) REG(r) v = register_fetch(r)

#define register_field_fetch(name, field) (register_fetch(name).field)
#define register_field_apply(name, field, value) do { \
	register_create(name, __tmp_reg); \
	__tmp_reg.field = value; \
	register_apply(name, __tmp_reg); \
} while(0)


/*
 * Demo: declare register
 *     REG(name) reg = {
 *         .field1 = val1,
 *         .field2 = val2,
 *     };
 *
 * Demo: fetch and apply
 *     REG(name) reg = register_fetch(name);
 *     register_apply(name, reg);
 *
 * Demo: create register
 *     register_create(name, foo);
 *     register_apply(name, foo);
 *
 * Demo: field access
 *     int fval = register_field_fetch(register_name, field_name);
 *     fval += 2;
 *     register_field_apply(register_name, field_name, fval);
 */

#endif /* __REGISTER_H__ */
