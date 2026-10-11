#pragma once

#include "esp_err.h"

typedef enum {
    HAPTIC_RECOIL,   // short kick per shot
    HAPTIC_HIT,      // 250 ms buzz
    HAPTIC_DEATH,    // long pattern
    HAPTIC_RESPAWN,  // two short pulses
} haptic_pattern_t;

esp_err_t haptics_init(void);
void haptics_play(haptic_pattern_t pattern);
