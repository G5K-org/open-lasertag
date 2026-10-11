// ESP-NOW transport: weapon <-> weapon (hit confirmation) and weapon <->
// gateway at the server (fallback when WLAN is down). Frames go out on the
// current WLAN channel.
#include "espnow.h"

#include <string.h>
#include "esp_check.h"
#include "esp_log.h"
#include "esp_now.h"
#include "esp_wifi.h"
#include "freertos/queue.h"

#define TAG "espnow"

static const uint8_t BROADCAST[6] = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff};
static QueueHandle_t s_rx_q;

static void on_recv(const esp_now_recv_info_t *info, const uint8_t *data, int len)
{
    if (len <= 0 || len > ESPNOW_FRAME_MAX) {
        return;
    }
    espnow_frame_t f = {.len = len, .rssi = info->rx_ctrl ? info->rx_ctrl->rssi : 0};
    memcpy(f.mac, info->src_addr, 6);
    memcpy(f.data, data, len);
    xQueueSend(s_rx_q, &f, 0);  // WLAN task: never block
}

static esp_err_t ensure_peer(const uint8_t *mac)
{
    if (esp_now_is_peer_exist(mac)) {
        return ESP_OK;
    }
    esp_now_peer_info_t peer = {
        .channel = 0,  // follow the current channel
        .ifidx = WIFI_IF_STA,
        .encrypt = false,
    };
    memcpy(peer.peer_addr, mac, 6);
    return esp_now_add_peer(&peer);
}

esp_err_t espnow_init(void)
{
    s_rx_q = xQueueCreate(16, sizeof(espnow_frame_t));
    ESP_RETURN_ON_FALSE(s_rx_q, ESP_ERR_NO_MEM, TAG, "queue");
    ESP_RETURN_ON_ERROR(esp_now_init(), TAG, "init");
    ESP_RETURN_ON_ERROR(esp_now_register_recv_cb(on_recv), TAG, "recv cb");
    return ensure_peer(BROADCAST);
}

bool espnow_recv(espnow_frame_t *f, TickType_t wait)
{
    return s_rx_q && xQueueReceive(s_rx_q, f, wait) == pdTRUE;
}

void espnow_send(const uint8_t *mac, const uint8_t *data, size_t len)
{
    if (!mac) {
        mac = BROADCAST;
    }
    if (ensure_peer(mac) != ESP_OK) {
        mac = BROADCAST;
    }
    esp_err_t err = esp_now_send(mac, data, len);
    if (err != ESP_OK) {
        ESP_LOGD(TAG, "send failed: %s", esp_err_to_name(err));
    }
}
