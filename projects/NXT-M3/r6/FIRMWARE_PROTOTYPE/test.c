#include "nxt.h"
#ifdef NXT_EMULATED
extern void test_fail(unsigned line);
#define assert(condition) do { if (!(condition)) test_fail(__LINE__); } while (0)
#else
#include <assert.h>
#include <stdio.h>
#endif

static int compare3(const uint8_t a[3], const uint8_t b[3])
{
    for (unsigned i = 0; i < 3; ++i)
        if (a[i] != b[i]) return 0;
    return 1;
}

static void send(struct nxt *node, const uint8_t frame[NXT_FRAME], uint32_t now)
{
    for (unsigned i = 0; i < NXT_FRAME; ++i) nxt_rx(node, frame[i], now);
}

static void show(struct nxt nodes[3], const char *number, uint8_t mask, uint16_t seq, uint32_t now)
{
    uint8_t slices[3][3], frame[NXT_FRAME];
    assert(nxt_format(number, mask, slices));
    for (uint8_t i = 0; i < 3; ++i) {
        if (!(mask & (1u << i))) continue;
        nxt_frame(frame, NXT_PREPARE, (uint8_t)(i+1), seq, mask, slices[i]);
        for (uint8_t j = 0; j < 3; ++j) send(&nodes[j], frame, now);
    }
    nxt_frame(frame, NXT_COMMIT, 0, seq, mask, NULL);
    for (uint8_t j = 0; j < 3; ++j) send(&nodes[j], frame, now);
}

int main(void)
{
    struct nxt nodes[3], invalid;
    uint8_t slices[3][3], frame[NXT_FRAME];
    assert(!nxt_init(&invalid, 0));
    assert(!nxt_local(&invalid, "0"));
    for (uint8_t i = 0; i < 3; ++i) assert(nxt_init(&nodes[i], (uint8_t)(i+1)));
    assert(nxt_crc((const uint8_t *)"123456789", 9) == 0x29b1);
    assert(nxt_local(&nodes[0], "09"));
    assert(nxt_word(&nodes[0]) == ((UINT32_C(1)<<10)|(UINT32_C(1)<<29)));
    show(nodes, "123456789", 7, 65535, 1);
    assert(compare3(nodes[0].digits, (uint8_t[]){1,2,3}));
    assert(compare3(nodes[1].digits, (uint8_t[]){4,5,6}));
    assert(compare3(nodes[2].digits, (uint8_t[]){7,8,9}));
    show(nodes, "12345", 5, 0, 2);
    assert(compare3(nodes[0].digits, (uint8_t[]){15,1,2}));
    assert(compare3(nodes[2].digits, (uint8_t[]){3,4,5}));
    show(nodes, "007", 2, 1, 3);
    assert(compare3(nodes[1].digits, (uint8_t[]){0,0,7}));
    show(nodes, "234", 1, 1, 3);
    show(nodes, "567", 4, 1, 3);
    assert(compare3(nodes[0].digits, (uint8_t[]){2,3,4}));
    assert(compare3(nodes[1].digits, (uint8_t[]){0,0,7}));
    assert(compare3(nodes[2].digits, (uint8_t[]){5,6,7}));
    assert(!nxt_format("-1", 7, slices));
    assert(!nxt_format("1.2", 7, slices));
    assert(!nxt_format("1234", 1, slices));
    nxt_frame(frame, NXT_PREPARE, 1, 2, 1, (uint8_t[]){0,0,8});
    frame[10] ^= 1;
    send(&nodes[0], frame, 4);
    nxt_frame(frame, NXT_COMMIT, 0, 2, 1, NULL);
    send(&nodes[0], frame, 5);
    assert(nodes[0].status == NXT_MISSING_STAGE && nxt_word(&nodes[0]) == 0);
    show(nodes, "999", 1, 2, 6);
    assert(nodes[0].status == NXT_MISSING_STAGE);
    show(nodes, "123", 1, 3, 7);
    assert(nodes[0].status == NXT_REMOTE);
    nxt_tick(&nodes[0], 1007);
    assert(nodes[0].status == NXT_LINK_LOST && nxt_word(&nodes[0]) == 0);
    show(nodes, "456", 1, 1, 1008);
    assert(nodes[0].status == NXT_REMOTE);
    nxt_fault(&nodes[0]);
    show(nodes, "999", 1, 2, 1010);
    assert(nodes[0].status == NXT_FAULT && nxt_word(&nodes[0]) == 0);
    nxt_frame(frame,NXT_PREPARE,2,3,2,(uint8_t[]){1,2,3});
    const uint8_t noise[] = {NXT_SOF,1,1,1};
    for (unsigned i=0; i<sizeof(noise); ++i) nxt_rx(&nodes[1],noise[i],1100);
    send(&nodes[1],frame,1100);
    nxt_frame(frame,NXT_COMMIT,0,3,2,NULL);
    send(&nodes[1],frame,1101);
    assert(nodes[1].status == NXT_REMOTE && nodes[1].digits[2] == 3);
    nxt_frame(frame,NXT_PREPARE,2,4,2,(uint8_t[]){8,8,8});
    send(&nodes[1],frame,1200);
    nxt_frame(frame,NXT_COMMIT,0,4,2,NULL);
    send(&nodes[1],frame,1350);
    assert(nodes[1].status == NXT_MISSING_STAGE);
#ifndef NXT_EMULATED
    puts("PASS: standalone, 3/6/9 slices, mask routing, CRC, rejection, wrap, timeout, recovery, fault, stream resync");
#endif
    return 0;
}
