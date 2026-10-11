#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

// WLAN (STA, static IP, no power save, own roaming) and UDP to the server.
// Runs on core 0. Falls back to an ESP-NOW gateway when the WLAN is gone.
esp_err_t net_start(void);
bool net_connected(void);

// Reliable: sent twice at once, then repeated until the server acks.
// Buffered while offline.
void net_report_hit(uint8_t shooter_team, uint8_t shooter_player, uint8_t sensor,
                    uint16_t hp_after);
void net_report_death(uint8_t killer_team, uint8_t killer_player);

// Tell the shooter's weapon about the hit (ESP-NOW broadcast, not reliable).
void net_hit_confirm(uint8_t shooter_team, uint8_t shooter_player, bool killed);
