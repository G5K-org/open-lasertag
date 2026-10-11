#pragma once

#include <stdbool.h>
#include "esp_err.h"

// WS2812 chain: [HP bar][ammo bar][team pixels][muzzle ring]. Rendered at
// 50 Hz on core 1.
esp_err_t leds_start(void);

// 150 ms white flash on hit (not on the muzzle ring)
void leds_flash_hit(void);

// Muzzle flash on the ring at the front, ~120 ms
void leds_flash_muzzle(void);

// Shooter feedback: ammo bar flashes green (hit) or longer (kill)
void leds_flash_confirm(bool kill);
