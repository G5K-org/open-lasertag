// UDP packet format weapon <-> server. Little endian, packed.
//
//   header (16 bytes) | payload (len bytes) | HMAC-SHA256 truncated to 16 bytes
//
// The MAC covers header and payload. The receiver drops packets whose
// (session, seq) is not newer than the last accepted one from that sender.
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"

#define PROTO_MAGIC0 'L'
#define PROTO_MAGIC1 'T'
#define PROTO_VERSION 1
#define PROTO_MAC_LEN 16
#define PROTO_MAX_PAYLOAD 64
#define PROTO_PLAYER_ALL 0xff

typedef enum {
    // weapon -> server
    PKT_HELLO = 0x01,   // after (re)connect: firmware version
    PKT_STATUS = 0x02,  // every second
    PKT_HIT = 0x03,     // reliable, until ACK
    PKT_DEATH = 0x04,   // reliable, until ACK
    PKT_PING = 0x05,    // RTT measurement
    // weapon -> weapon (ESP-NOW broadcast)
    PKT_HIT_CONFIRM = 0x10,  // victim tells the shooter about the hit
    // server -> weapon
    PKT_ACK = 0x81,
    PKT_PONG = 0x82,
    PKT_GAME_START = 0x83,
    PKT_GAME_STOP = 0x84,
    PKT_RESPAWN = 0x85,
    PKT_SET_IDENTITY = 0x86,
} pkt_type_t;

typedef struct __attribute__((packed)) {
    uint8_t magic[2];
    uint8_t version;
    uint8_t type;
    uint8_t team;
    uint8_t player;    // sender id, or target id for server packets (0xff = all)
    uint16_t len;      // payload length
    uint32_t session;  // random per boot of the sender
    uint32_t seq;      // increments with every packet of the sender
} pkt_hdr_t;

typedef struct __attribute__((packed)) {
    char version[16];
} pl_hello_t;

typedef struct __attribute__((packed)) {
    uint16_t hp;
    uint8_t ammo;
    uint8_t magazines;
    uint8_t alive;
    uint8_t running;
    uint16_t battery_mv;
    uint8_t charging;
    int8_t rssi;
    uint8_t bssid[6];   // current AP, for RTT per hall zone
    uint16_t rtt_ms;    // last RTT
    uint16_t rtt_max_ms;
    uint32_t shots;
    uint32_t hits_taken;
    uint32_t pending;   // reliable packets not yet acked
} pl_status_t;

typedef struct __attribute__((packed)) {
    uint8_t shooter_team;
    uint8_t shooter_player;
    uint8_t sensor;     // 1 = headband front ... 6 = weapon front
    uint8_t reserved;
    uint16_t hp_after;
    uint32_t time_ms;   // weapon uptime at the hit
} pl_hit_t;

typedef struct __attribute__((packed)) {
    uint8_t killer_team;
    uint8_t killer_player;
    uint32_t time_ms;
} pl_death_t;

typedef struct __attribute__((packed)) {
    uint8_t shooter_team;
    uint8_t shooter_player;
    uint8_t killed;
    uint8_t reserved;
} pl_hit_confirm_t;

typedef struct __attribute__((packed)) {
    uint64_t t_us;      // echoed back by the server in PKT_PONG
} pl_ping_t;

typedef struct __attribute__((packed)) {
    uint32_t session;   // weapon session and seq being acknowledged
    uint32_t seq;
} pl_ack_t;

typedef struct __attribute__((packed)) {
    uint16_t max_hp;
    uint16_t damage;
    uint8_t magazine;
    uint8_t magazines;
    uint8_t friendly_fire;
    uint8_t respawn_s;
} pl_game_start_t;

typedef struct __attribute__((packed)) {
    uint8_t team;
    uint8_t player;
} pl_identity_t;

// Sizes are part of the wire format (tools/udp_test_server.py)
_Static_assert(sizeof(pkt_hdr_t) == 16, "header");
_Static_assert(sizeof(pl_hello_t) == 16, "hello");
_Static_assert(sizeof(pl_status_t) == 32, "status");
_Static_assert(sizeof(pl_hit_t) == 10, "hit");
_Static_assert(sizeof(pl_death_t) == 6, "death");
_Static_assert(sizeof(pl_hit_confirm_t) == 4, "hit confirm");
_Static_assert(sizeof(pl_ping_t) == 8, "ping");
_Static_assert(sizeof(pl_ack_t) == 8, "ack");
_Static_assert(sizeof(pl_game_start_t) == 8, "game start");
_Static_assert(sizeof(pl_identity_t) == 2, "identity");

esp_err_t proto_init(const char *key);

// Build a packet into buf (size >= sizeof(pkt_hdr_t) + len + PROTO_MAC_LEN).
// Returns the total length.
size_t proto_build(uint8_t *buf, const pkt_hdr_t *hdr, const void *payload, uint16_t len);

// Check magic, version, length and MAC. On success *hdr/*payload point into buf.
bool proto_verify(const uint8_t *buf, size_t n, const pkt_hdr_t **hdr, const uint8_t **payload);
