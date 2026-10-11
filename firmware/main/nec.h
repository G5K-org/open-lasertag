// NEC frame coding, shared by IR transmit and receive.
// Address = team, command = player id, both with their inverted byte.
#pragma once

#include <stdbool.h>
#include <stdint.h>

#define NEC_HDR_MARK_US   9000
#define NEC_HDR_SPACE_US  4500
#define NEC_RPT_SPACE_US  2250
#define NEC_BIT_MARK_US   560
#define NEC_ZERO_SPACE_US 560
#define NEC_ONE_SPACE_US  1690

// One received mark (carrier on) followed by its space (carrier off).
// The space of the last pair may be 0 (end of frame).
typedef struct {
    uint16_t mark_us;
    uint16_t space_us;
} nec_pair_t;

typedef enum {
    NEC_INVALID = 0,
    NEC_FRAME,
    NEC_REPEAT,
} nec_result_t;

// Decode one burst. Leading garbage pairs before the header are skipped.
nec_result_t nec_decode(const nec_pair_t *pairs, int n, uint8_t *addr, uint8_t *cmd);

// Fill pairs[34] with header, 32 data bits and the stop mark for addr/cmd.
// The stop mark gets trailing_space_us as its space.
int nec_encode(uint8_t addr, uint8_t cmd, uint16_t trailing_space_us, nec_pair_t pairs[34]);
