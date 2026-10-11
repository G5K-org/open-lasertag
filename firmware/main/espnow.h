#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "proto.h"

#define ESPNOW_FRAME_MAX (sizeof(pkt_hdr_t) + PROTO_MAX_PAYLOAD + PROTO_MAC_LEN)

typedef struct {
    uint8_t mac[6];   // sender
    int8_t rssi;
    uint8_t len;
    uint8_t data[ESPNOW_FRAME_MAX];
} espnow_frame_t;

// Call after esp_wifi_start(). Frames use the proto.h format (with HMAC);
// ESP-NOW only carries them.
esp_err_t espnow_init(void);

// Next received frame, false if none arrived within wait.
bool espnow_recv(espnow_frame_t *f, TickType_t wait);

// mac == NULL: broadcast. Unicast peers are added on first use.
void espnow_send(const uint8_t *mac, const uint8_t *data, size_t len);
