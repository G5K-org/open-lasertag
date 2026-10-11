// Host test for the NEC codec: gcc -I../main test_nec.c ../main/nec.c && ./a.out
#include <stdio.h>
#include <stdlib.h>
#include "nec.h"

static int failures;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); failures++; } } while (0)

int main(void)
{
    nec_pair_t p[40];
    uint8_t a, c;

    // round trip for all team/player combinations
    for (int team = 0; team < 8; team++) {
        for (int player = 1; player < 255; player++) {
            int n = nec_encode(team, player, 0, p);
            CHECK(nec_decode(p, n, &a, &c) == NEC_FRAME && a == team && c == player);
        }
    }

    // TSOP distortion: marks ~150 us longer, spaces shorter, plus jitter
    srand(1);
    for (int k = 0; k < 1000; k++) {
        int n = nec_encode(3, 42, 0, p);
        for (int i = 0; i < n; i++) {
            int j = rand() % 81 - 40;
            p[i].mark_us += 150 + j;
            if (p[i].space_us) p[i].space_us -= 150 + j;
        }
        CHECK(nec_decode(p, n, &a, &c) == NEC_FRAME && a == 3 && c == 42);
    }

    // leading glitch before the header
    nec_pair_t g[40] = {{120, 300}};
    nec_encode(1, 7, 0, g + 1);
    CHECK(nec_decode(g, 35, &a, &c) == NEC_FRAME && a == 1 && c == 7);

    // bit error breaks the inverse check
    nec_encode(2, 9, 0, p);
    p[20].space_us = p[20].space_us == NEC_ONE_SPACE_US ? NEC_ZERO_SPACE_US : NEC_ONE_SPACE_US;
    CHECK(nec_decode(p, 34, &a, &c) == NEC_INVALID);

    // repeat code
    nec_pair_t r[2] = {{9000, 2250}, {560, 0}};
    CHECK(nec_decode(r, 2, &a, &c) == NEC_REPEAT);

    // truncated frame
    nec_encode(2, 9, 0, p);
    CHECK(nec_decode(p, 20, &a, &c) == NEC_INVALID);

    // noise
    for (int i = 0; i < 40; i++) p[i] = (nec_pair_t){rand() % 3000, rand() % 3000};
    CHECK(nec_decode(p, 40, &a, &c) == NEC_INVALID);

    printf(failures ? "%d failures\n" : "all NEC tests passed\n", failures);
    return failures != 0;
}
