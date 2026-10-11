// ESP-NOW <-> USB serial gateway for the lasertag server.
//
// Weapons that lost the WLAN send their packets (proto.h format, HMAC
// protected) by ESP-NOW on a fixed channel. The gateway does not check
// them, it only relays:
//
//   weapon -> server:  "LT:<sender mac, 12 hex>:<packet hex>\n" on stdout
//   server -> weapon:  "LT:<target mac or ffffffffffff>:<packet hex>\n" on stdin
//
// Everything else on the serial line is log output and ignored by the server.
#include <ctype.h>
#include <stdio.h>
#include <string.h>
#include "driver/usb_serial_jtag.h"
#include "driver/usb_serial_jtag_vfs.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_now.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "nvs_flash.h"
#include "sdkconfig.h"

#define TAG "gateway"
#define FRAME_MAX 250
#define TYPE_OFFSET 3        // pkt_hdr_t.type
#define WEAPON_TYPE_MAX 0x0f // only weapon -> server packets are relayed

typedef struct {
    uint8_t mac[6];
    uint8_t len;
    uint8_t data[FRAME_MAX];
} frame_t;

static const uint8_t BROADCAST[6] = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff};
static QueueHandle_t s_rx_q;

static void on_recv(const esp_now_recv_info_t *info, const uint8_t *data, int len)
{
    if (len <= TYPE_OFFSET || len > FRAME_MAX || data[TYPE_OFFSET] > WEAPON_TYPE_MAX ||
        data[TYPE_OFFSET] == 0) {
        return;  // not for the server (e.g. weapon -> weapon hit confirmation)
    }
    frame_t f = {.len = len};
    memcpy(f.mac, info->src_addr, 6);
    memcpy(f.data, data, len);
    xQueueSend(s_rx_q, &f, 0);
}

// ESP-NOW -> serial
static void uplink_task(void *arg)
{
    static char line[8 + 12 + 1 + 2 * FRAME_MAX + 2];
    frame_t f;
    while (true) {
        xQueueReceive(s_rx_q, &f, portMAX_DELAY);
        char *p = line + sprintf(line, "LT:%02x%02x%02x%02x%02x%02x:", MAC2STR(f.mac));
        for (int i = 0; i < f.len; i++) {
            p += sprintf(p, "%02x", f.data[i]);
        }
        *p++ = '\n';
        *p = 0;
        fputs(line, stdout);
        fflush(stdout);
    }
}

static int hexval(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    c = tolower((unsigned char)c);
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}

static int unhex(const char *s, uint8_t *out, int max)
{
    int n = 0;
    while (s[0] && s[1] && hexval(s[0]) >= 0 && hexval(s[1]) >= 0) {
        if (n == max) {
            return -1;
        }
        out[n++] = hexval(s[0]) << 4 | hexval(s[1]);
        s += 2;
    }
    return n;
}

static void send_to(const uint8_t *mac, const uint8_t *data, int len)
{
    if (memcmp(mac, BROADCAST, 6) != 0 && !esp_now_is_peer_exist(mac)) {
        esp_now_peer_info_t peer = {.channel = 0, .ifidx = WIFI_IF_STA};
        memcpy(peer.peer_addr, mac, 6);
        if (esp_now_add_peer(&peer) == ESP_ERR_ESPNOW_FULL) {
            mac = BROADCAST;  // more weapons than peer slots
        }
    }
    esp_err_t err = esp_now_send(mac, data, len);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "send: %s", esp_err_to_name(err));
    }
}

// serial -> ESP-NOW
static void downlink_task(void *arg)
{
    static char line[8 + 12 + 1 + 2 * FRAME_MAX + 8];
    uint8_t mac[6], data[FRAME_MAX];
    while (fgets(line, sizeof(line), stdin)) {
        if (strncmp(line, "LT:", 3) != 0 || strlen(line) < 3 + 12 + 1 || line[15] != ':') {
            continue;
        }
        line[15] = 0;
        int len = unhex(line + 16, data, sizeof(data));
        if (unhex(line + 3, mac, 6) != 6 || len <= 0) {
            continue;
        }
        send_to(mac, data, len);
    }
    ESP_LOGE(TAG, "stdin closed");
    vTaskDelete(NULL);
}

void app_main(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    // blocking, interrupt driven stdin/stdout on the USB-Serial-JTAG port
    usb_serial_jtag_driver_config_t usb = {.rx_buffer_size = 2048, .tx_buffer_size = 4096};
    ESP_ERROR_CHECK(usb_serial_jtag_driver_install(&usb));
    usb_serial_jtag_vfs_use_driver();
    setvbuf(stdin, NULL, _IONBF, 0);

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));
    ESP_ERROR_CHECK(esp_wifi_set_channel(CONFIG_GW_CHANNEL, WIFI_SECOND_CHAN_NONE));

    s_rx_q = xQueueCreate(32, sizeof(frame_t));
    ESP_ERROR_CHECK(esp_now_init());
    ESP_ERROR_CHECK(esp_now_register_recv_cb(on_recv));
    esp_now_peer_info_t bc = {.channel = 0, .ifidx = WIFI_IF_STA};
    memcpy(bc.peer_addr, BROADCAST, 6);
    ESP_ERROR_CHECK(esp_now_add_peer(&bc));

    uint8_t mac[6];
    esp_wifi_get_mac(WIFI_IF_STA, mac);
    printf("LT-GW: ready, channel %d, mac %02x%02x%02x%02x%02x%02x\n", CONFIG_GW_CHANNEL,
           MAC2STR(mac));
    fflush(stdout);

    xTaskCreate(uplink_task, "uplink", 4096, NULL, 10, NULL);
    xTaskCreate(downlink_task, "downlink", 4096, NULL, 9, NULL);
}
