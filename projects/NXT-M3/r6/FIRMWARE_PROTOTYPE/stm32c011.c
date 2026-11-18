/* Receive-only low-voltage fixture. Applicability: STM32C011F4P6, NXT-M3 R6. */
#include "nxt.h"

#define REG(addr) (*(volatile uint32_t *)(uintptr_t)(addr))
#define GPIOA 0x50000000u
#define GPIOB 0x50000400u
#define GPIOC 0x50000800u
#define RCC 0x40021000u
#define USART1 0x40013800u
#define IWDG 0x40003000u
#define SYSTICK 0xe000e010u
#define NVIC_ISER 0xe000e100u
#define CORE_HZ 12000000u
#define RELOAD (CORE_HZ/1000u - 1u)
#define PIN(n) (1u << (n))
enum { BL = 1, LE = 2, CLK = 3, DATA = 4, LED = 7, RING = 64 };
static volatile uint32_t milliseconds;
static volatile uint8_t head, tail, overflow;
static uint8_t queue[RING];
static struct nxt node;

static void mode(uint32_t gpio, unsigned pin, unsigned setting)
{
    REG(gpio) = (REG(gpio) & ~(3u << (pin*2))) | (setting << (pin*2));
}

static void output(uint32_t gpio, unsigned pin, int high)
{
    REG(gpio+0x18) = high ? PIN(pin) : PIN(pin+16);
}

static void settle(void)
{
    const uint32_t start = REG(SYSTICK+8);
    for (;;) {
        const uint32_t now = REG(SYSTICK+8);
        const uint32_t delta = start >= now ? start-now : start+(RELOAD+1u)-now;
        if (delta >= CORE_HZ/200000u) return;
    }
}

static void display(uint32_t word)
{
    output(GPIOA, BL, 0);
    for (unsigned i = 32; i > 0; --i) {
        output(GPIOA, DATA, (word >> (i-1)) & 1u);
        output(GPIOA, CLK, 1);
        settle();
        output(GPIOA, CLK, 0);
        settle();
    }
    output(GPIOA, LE, 1);
    settle();
    output(GPIOA, LE, 0);
    if (word && !(REG(GPIOC+0x10) & PIN(14))) output(GPIOA, BL, 1);
}

void tick_isr(void)
{
    ++milliseconds;
}

void uart_isr(void)
{
    const uint32_t flags = REG(USART1+0x1c);
    if (flags & 0x0fu) {
        REG(USART1+0x20) = 0x0f;
        overflow = 1;
    }
    if (!(flags & PIN(5))) return;
    const uint8_t byte = (uint8_t)REG(USART1+0x24);
    const uint8_t next = (uint8_t)((head+1u)&(RING-1u));
    if (next == tail) {
        overflow = 1;
        return;
    }
    queue[head] = byte;
    head = next;
}

static void init(void)
{
    REG(RCC) = (REG(RCC) & ~(7u << 11)) | (2u << 11); /* HSI48 / 4 */
    REG(RCC+0x34) |= 7u;
    REG(RCC+0x40) |= PIN(14);
    (void)REG(RCC+0x40);
    mode(GPIOB, 7, 2);
    REG(GPIOB+0x20) &= ~(15u<<28);  /* PB7 USART1_RX AF0 */
    output(GPIOB, 0, 0);
    mode(GPIOB, 0, 1);
    for (unsigned i = BL; i <= DATA; ++i) {
        output(GPIOA, i, 0);
        mode(GPIOA, i, 1);
    }
    output(GPIOA, LED, 1);
    mode(GPIOA, LED, 1);
    mode(GPIOA, 5, 0);
    mode(GPIOA, 6, 0);
    mode(GPIOC, 14, 0);
    mode(GPIOC, 15, 0);
    REG(SYSTICK+4) = RELOAD;
    REG(SYSTICK+8) = 0;
    REG(SYSTICK) = 7;
    REG(USART1+0x0c) = (CORE_HZ+57600u)/115200u;
    REG(USART1) = PIN(0)|PIN(2)|PIN(5);
    REG(NVIC_ISER) = PIN(27);
    REG(IWDG) = 0xcccc; /* Independent watchdog, nominal ~250 ms at 32 kHz LSI. */
    REG(IWDG) = 0x5555;
    REG(IWDG+4) = 3;
    REG(IWDG+8) = 249;
    while (REG(IWDG+0x0c) & 3u) {}
    REG(IWDG) = 0xaaaa;
}

static void run(void)
{
    init();
    const uint8_t address = (uint8_t)(1u+(((REG(GPIOA+0x10)>>5)&3u) ^ 3u));
    nxt_init(&node,address);
    uint32_t last = UINT32_MAX;
    unsigned hardware_fault = 0;
    for (;;) {
        uint32_t now = milliseconds;
        uint32_t status = REG(GPIOC+0x10);
        unsigned is_fault = (status & PIN(14)) || !(status & PIN(15));
        if (is_fault || overflow) {
            output(GPIOA, BL, 0);
            tail = head;
            overflow = 0;
            nxt_fault(&node);
            hardware_fault = 1;
        } else {
            if (hardware_fault) {
                nxt_init(&node,address);
                hardware_fault = 0;
            }
            while (tail != head) {
                uint8_t value = queue[tail];
                tail = (uint8_t)((tail+1u)&(RING-1u));
                nxt_rx(&node,value,now);
            }
        }
        nxt_tick(&node,now);
        uint32_t word = nxt_word(&node);
        if (word != last) {
            display(word);
            last = word;
        }
        unsigned led_off = 0;
        if (node.status == NXT_WAITING) led_off = 1;
        if (node.status == NXT_LINK_LOST || node.status == NXT_MISSING_STAGE)
            led_off = (now & 256u) != 0;
        if (node.status == NXT_FAULT) led_off = (now & 64u) != 0;
        output(GPIOA, LED, led_off);
        REG(IWDG) = 0xaaaa;
    }
}

extern uint32_t __stack, __bss_start, __bss_end;
void reset(void)
{
    for (uint32_t *p=&__bss_start; p < &__bss_end; ++p) *p=0;
    run();
}

static void idle(void)
{
    for (;;) {}
}

__attribute__((section(".vectors"),used))
const uintptr_t vectors[48] = {
    [0] = (uintptr_t)&__stack, [1] = (uintptr_t)reset, [2] = (uintptr_t)idle,
    [3] = (uintptr_t)idle, [15] = (uintptr_t)tick_isr, [43] = (uintptr_t)uart_isr,
};

/* Clang may lower zero initialization of the protocol state to this EABI routine. */
void __aeabi_memclr(void *dest, size_t count)
{
    volatile uint8_t *bytes = dest;
    while (count--) *bytes++ = 0;
}

void __aeabi_memclr4(void *dest, size_t count)
{
    __aeabi_memclr(dest,count);
}
