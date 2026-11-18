#include "nxt.h"

static void digits_copy(uint8_t dst[3], const uint8_t src[3])
{
    for (unsigned i = 0; i < 3; ++i) dst[i] = src[i];
}

static void blank(struct nxt *node, enum nxt_status status)
{
    const uint8_t off[3] = {NXT_BLANK, NXT_BLANK, NXT_BLANK};
    digits_copy(node->digits, off);
    node->status = (uint8_t)status;
}

uint16_t nxt_crc(const uint8_t *data, size_t len)
{
    uint16_t crc = 0xffff;
    for (size_t i = 0; i < len; ++i) {
        crc ^= (uint16_t)((uint16_t)data[i] << 8);
        for (unsigned bit = 0; bit < 8; ++bit) {
            uint32_t shift = (uint32_t)crc << 1;
            crc = (uint16_t)((crc & 0x8000) ? shift ^ 0x1021u : shift);
        }
    }
    return crc;
}

int nxt_init(struct nxt *node, uint8_t address)
{
    *node = (struct nxt){0};
    if (address < 1 || address > 3) {
        blank(node, NXT_FAULT);
        return 0;
    }
    node->address = address;
    blank(node, NXT_WAITING);
    return 1;
}

int nxt_local(struct nxt *node, const char *digits)
{
    uint8_t values[3][3];
    if (node->status == NXT_FAULT || !nxt_format(digits, 1, values)) return 0;
    digits_copy(node->digits, values[0]);
    node->status = NXT_LOCAL;
    node->staged = 0;
    return 1;
}

void nxt_fault(struct nxt *node)
{
    node->staged = 0;
    blank(node, NXT_FAULT);
}

static int newer(uint16_t next, uint16_t prev)
{
    uint16_t delta = (uint16_t)(next - prev);
    return delta && delta < 0x8000;
}

void nxt_tick(struct nxt *node, uint32_t now)
{
    if (node->staged && now-node->staged_ms >= NXT_STAGE_MS) node->staged = 0;
    if (node->seen && now-node->applied_ms >= NXT_LEASE_MS) {
        node->seen = 0;
        node->staged = 0;
        if (node->status == NXT_REMOTE || node->status == NXT_MISSING_STAGE)
            blank(node, NXT_LINK_LOST);
    }
}

static void accept(struct nxt *node, const uint8_t *f, uint32_t now)
{
    nxt_tick(node, now);
    if (node->status == NXT_FAULT || f[1] != 1) return;
    const uint16_t seq = (uint16_t)((uint16_t)f[4] | (uint16_t)((uint16_t)f[5] << 8));
    const uint8_t mask = f[6];
    if (mask > 7 || !(mask & (1u << (node->address-1)))) return;
    if (node->seen && !newer(seq, node->sequence)) return;
    if (f[2] == NXT_PREPARE && f[3] == node->address) {
        for (unsigned i = 7; i < 10; ++i)
            if (f[i] > 9 && f[i] != NXT_BLANK) return;
        if (node->staged && !newer(seq, node->stage_sequence)) return;
        digits_copy(node->stage, f+7);
        node->stage_sequence = seq;
        node->stage_mask = mask;
        node->staged_ms = now;
        node->staged = 1;
        return;
    }
    if (f[2] != NXT_COMMIT || f[3] != 0 || f[7] || f[8] || f[9]) return;
    if (node->staged && node->stage_sequence == seq && node->stage_mask == mask) {
        digits_copy(node->digits, node->stage);
        node->status = NXT_REMOTE;
    } else {
        blank(node, NXT_MISSING_STAGE);
    }
    node->staged = 0;
    node->seen = 1;
    node->sequence = seq;
    node->applied_ms = now;
}

void nxt_rx(struct nxt *node, uint8_t byte, uint32_t now)
{
    if (node->count == 0 && byte != NXT_SOF) return;
    node->buf[node->count++] = byte;
    if (node->count < NXT_FRAME) return;
    const uint16_t crc = (uint16_t)((uint16_t)node->buf[10] | (uint16_t)((uint16_t)node->buf[11] << 8));
    if (crc == nxt_crc(node->buf, 10)) {
        accept(node, node->buf, now);
        node->count = 0;
        return;
    }
    unsigned start = 1;
    while (start < NXT_FRAME && node->buf[start] != NXT_SOF) ++start;
    node->count = (uint8_t)(NXT_FRAME-start);
    for (unsigned i = 0; i < node->count; ++i) node->buf[i] = node->buf[i+start];
}

uint32_t nxt_word(const struct nxt *node)
{
    uint32_t word = 0;
    for (unsigned i = 0; i < 3; ++i) {
        if (node->digits[i] <= 9)
            word |= UINT32_C(1) << (i*10 + node->digits[i]);
    }
    return word;
}

int nxt_format(const char *number, uint8_t mask, uint8_t slices[3][3])
{
    unsigned capacity = 0, length = 0;
    if (!mask || mask > 7 || !number || !*number) return 0;
    for (unsigned i = 0; i < 3; ++i)
        if (mask & (1u << i)) capacity += 3;
    while (number[length]) {
        if (length == capacity || number[length] < '0' || number[length] > '9') return 0;
        ++length;
    }
    for (unsigned i = 0; i < 3; ++i)
        for (unsigned j = 0; j < 3; ++j) slices[i][j] = NXT_BLANK;
    unsigned slot = 0;
    for (unsigned i = 0; i < 3; ++i) {
        if (!(mask & (1u << i))) continue;
        for (unsigned j = 0; j < 3; ++j, ++slot) {
            if (slot >= capacity-length)
                slices[i][j] = (uint8_t)(number[slot-(capacity-length)]-'0');
        }
    }
    return 1;
}

void nxt_frame(uint8_t frame[NXT_FRAME], uint8_t op, uint8_t address,
               uint16_t seq, uint8_t mask, const uint8_t digits[3])
{
    frame[0] = NXT_SOF;
    frame[1] = 1;
    frame[2] = op;
    frame[3] = address;
    frame[4] = (uint8_t)seq;
    frame[5] = (uint8_t)(seq >> 8);
    frame[6] = mask;
    for (unsigned i = 0; i < 3; ++i) frame[7+i] = digits ? digits[i] : 0;
    uint16_t crc = nxt_crc(frame, 10);
    frame[10] = (uint8_t)crc;
    frame[11] = (uint8_t)(crc >> 8);
}
