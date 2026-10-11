#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

esp_err_t ir_tx_init(void);

// Send one shot: the NEC frame for (team, player) twice. Non-blocking.
esp_err_t ir_tx_shot(uint8_t team, uint8_t player);

// True if [from_us, to_us] overlaps our own transmission (plus echo guard).
// Reception is ignored during that time.
bool ir_tx_overlaps(int64_t from_us, int64_t to_us);
