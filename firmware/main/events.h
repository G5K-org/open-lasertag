// Events posted to the game task.
#pragma once

#include <stdint.h>

typedef enum {
    EV_TRIGGER_DOWN,
    EV_TRIGGER_UP,
    EV_RELOAD_DOWN,
    EV_IR_FRAME,      // valid NEC frame from a TSOP
    EV_NET_START,     // game start/config from the server
    EV_NET_STOP,
    EV_NET_RESPAWN,
    EV_NET_IDENTITY,  // new team/player id from the server
} event_type_t;

typedef struct {
    uint16_t max_hp;
    uint16_t damage;
    uint8_t magazine;
    uint8_t magazines;
    uint8_t friendly_fire;
    uint8_t respawn_s;
} game_config_t;

typedef struct {
    event_type_t type;
    int64_t time_us;
    union {
        struct {
            uint8_t team;
            uint8_t player;
            uint8_t sensor;  // 0-based TSOP index
        } ir;
        struct {
            uint8_t team;
            uint8_t player;
        } identity;
        game_config_t config;
    };
} event_t;

// Post an event to the game task (safe from any task, not from ISRs).
void game_post(const event_t *ev);
