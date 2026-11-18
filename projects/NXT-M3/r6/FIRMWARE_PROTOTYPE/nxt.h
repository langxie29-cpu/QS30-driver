#ifndef NXT_H
#define NXT_H

#include <stddef.h>
#include <stdint.h>

enum { NXT_FRAME = 12, NXT_BLANK = 15, NXT_PREPARE = 1, NXT_COMMIT = 2,
       NXT_LEASE_MS = 1000, NXT_STAGE_MS = 150, NXT_SOF = 0xa5 };
enum nxt_status { NXT_WAITING, NXT_LOCAL, NXT_REMOTE, NXT_LINK_LOST, NXT_MISSING_STAGE, NXT_FAULT };

struct nxt {
    uint8_t address, digits[3], stage[3], stage_mask, status;
    uint8_t buf[NXT_FRAME], count, staged, seen;
    uint16_t sequence, stage_sequence;
    uint32_t applied_ms, staged_ms;
};

uint16_t nxt_crc(const uint8_t *data, size_t len);
int nxt_init(struct nxt *node, uint8_t address);
int nxt_local(struct nxt *node, const char *digits);
void nxt_fault(struct nxt *node);
void nxt_rx(struct nxt *node, uint8_t byte, uint32_t now);
void nxt_tick(struct nxt *node, uint32_t now);
uint32_t nxt_word(const struct nxt *node);
int nxt_format(const char *number, uint8_t mask, uint8_t slices[3][3]);
void nxt_frame(uint8_t frame[NXT_FRAME], uint8_t op, uint8_t address,
               uint16_t seq, uint8_t mask, const uint8_t digits[3]);

#endif
