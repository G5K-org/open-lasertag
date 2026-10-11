// Lasertag weapon firmware, ESP32-S3.
// Core 0: WLAN, UDP, sound, battery. Core 1: IR receive, game logic,
// buttons, LEDs.
#include "audio.h"
#include "battery.h"
#include "esp_log.h"
#include "game.h"
#include "haptics.h"
#include "input.h"
#include "ir_rx.h"
#include "ir_tx.h"
#include "leds.h"
#include "net.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "sdkconfig.h"

#define TAG "main"

static void load_identity(uint8_t *team, uint8_t *player)
{
    *team = CONFIG_LT_TEAM;
    *player = CONFIG_LT_PLAYER_ID;
    nvs_handle_t h;
    if (nvs_open("lasertag", NVS_READONLY, &h) == ESP_OK) {
        nvs_get_u8(h, "team", team);
        nvs_get_u8(h, "player", player);
        nvs_close(h);
    }
}

static void check(esp_err_t err, const char *what)
{
    if (err != ESP_OK) {
        // keep running without the failed part, e.g. no WLAN in the field
        ESP_LOGE(TAG, "%s failed: %s", what, esp_err_to_name(err));
    }
}

void app_main(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    uint8_t team, player;
    load_identity(&team, &player);
    ESP_LOGI(TAG, "team %u, player %u", team, player);

    ESP_ERROR_CHECK(game_start(team, player));
    check(ir_tx_init(), "IR TX");
    check(ir_rx_start(), "IR RX");
    check(input_start(), "buttons");
    check(haptics_init(), "vibration");
    check(battery_start(), "battery");
    check(leds_start(), "WS2812");
    check(audio_start(), "audio");
    check(net_start(), "network");
}
