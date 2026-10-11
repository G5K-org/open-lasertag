#include "nec.h"

static bool near(uint32_t value, uint32_t target, uint32_t tol_percent)
{
    uint32_t tol = target * tol_percent / 100;
    return value + tol >= target && value <= target + tol;
}

nec_result_t nec_decode(const nec_pair_t *pairs, int n, uint8_t *addr, uint8_t *cmd)
{
    int i = 0;
    // TSOP AGC may produce a short glitch before the header
    while (i < n && !near(pairs[i].mark_us, NEC_HDR_MARK_US, 25)) {
        i++;
    }
    if (i >= n) {
        return NEC_INVALID;
    }
    uint16_t hdr_space = pairs[i].space_us;
    if (near(hdr_space, NEC_RPT_SPACE_US, 25)) {
        return NEC_REPEAT;
    }
    if (!near(hdr_space, NEC_HDR_SPACE_US, 25)) {
        return NEC_INVALID;
    }
    i++;
    if (n - i < 33) {
        return NEC_INVALID;
    }

    uint32_t data = 0;
    for (int bit = 0; bit < 32; bit++, i++) {
        const nec_pair_t *p = &pairs[i];
        if (!near(p->mark_us, NEC_BIT_MARK_US, 50)) {
            return NEC_INVALID;
        }
        if (near(p->space_us, NEC_ONE_SPACE_US, 35)) {
            data |= 1u << bit;  // LSB first
        } else if (!near(p->space_us, NEC_ZERO_SPACE_US, 60)) {
            return NEC_INVALID;
        }
    }
    if (!near(pairs[i].mark_us, NEC_BIT_MARK_US, 50)) {
        return NEC_INVALID;
    }

    uint8_t a = data & 0xff, a_inv = (data >> 8) & 0xff;
    uint8_t c = (data >> 16) & 0xff, c_inv = (data >> 24) & 0xff;
    if ((uint8_t)~a != a_inv || (uint8_t)~c != c_inv) {
        return NEC_INVALID;
    }
    *addr = a;
    *cmd = c;
    return NEC_FRAME;
}

int nec_encode(uint8_t addr, uint8_t cmd, uint16_t trailing_space_us, nec_pair_t pairs[34])
{
    uint32_t data = addr | (uint32_t)(uint8_t)~addr << 8 | (uint32_t)cmd << 16 |
                    (uint32_t)(uint8_t)~cmd << 24;
    pairs[0] = (nec_pair_t){NEC_HDR_MARK_US, NEC_HDR_SPACE_US};
    for (int bit = 0; bit < 32; bit++) {
        pairs[1 + bit] = (nec_pair_t){
            NEC_BIT_MARK_US, (data >> bit) & 1 ? NEC_ONE_SPACE_US : NEC_ZERO_SPACE_US};
    }
    pairs[33] = (nec_pair_t){NEC_BIT_MARK_US, trailing_space_us};
    return 34;
}
