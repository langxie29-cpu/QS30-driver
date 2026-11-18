/* Support for running the same C assertions in a freestanding RV32 emulator. */
#include <stddef.h>
#include <stdint.h>

extern int main(void);

static void done(uint32_t result)
{
    *(volatile uint32_t *)0x2000fffcu = result;
    for (;;) {}
}

void test_fail(unsigned line)
{
    done(line);
}

void test_entry(void)
{
    done(main()==0 ? 0x600dcafeu : 1u);
}

void *memset(void *dest, int byte, size_t count)
{
    volatile unsigned char *p = dest;
    while (count--) *p++ = (unsigned char)byte;
    return dest;
}

void *memcpy(void *dest, const void *source, size_t count)
{
    unsigned char *out = dest;
    const unsigned char *in = source;
    while (count--) *out++ = *in++;
    return dest;
}
