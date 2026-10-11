#pragma once

#include "esp_err.h"

// WS2812 chain: [HP bar][ammo bar][team pixels]. Rendered at 50 Hz on core 1.
esp_err_t leds_start(void);

// 150 ms white flash on hit
void leds_flash_hit(void);
