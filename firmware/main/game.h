#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

typedef struct {
    uint8_t team;
    uint8_t player;
    bool running;      // game active (standalone or started by the server)
    bool alive;
    uint16_t hp;
    uint16_t max_hp;
    uint8_t ammo;
    uint8_t magazine;  // shots per magazine
    uint8_t magazines; // remaining spare magazines, 0xff = unlimited
    bool reloading;
    int64_t reload_end_us;
    int64_t last_hit_us;
    int64_t death_us;
    uint32_t shots;
    uint32_t hits_taken;
    uint32_t hits_given;  // confirmed by the victims over ESP-NOW
    uint32_t kills;
} game_state_t;

esp_err_t game_start(uint8_t team, uint8_t player);

// Consistent copy of the current state for display and network.
void game_snapshot(game_state_t *out);
