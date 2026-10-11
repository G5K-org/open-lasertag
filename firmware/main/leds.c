// WS2812 display through the led_strip component (RMT backend).
#include "leds.h"

#include <math.h>
#include "battery.h"
#include "board.h"
#include "esp_check.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "game.h"
#include "led_strip.h"
#include "net.h"
#include "sdkconfig.h"

#define TAG "leds"
#define N_HP CONFIG_LT_LEDS_HP
#define N_AMMO CONFIG_LT_LEDS_AMMO
#define N_TEAM CONFIG_LT_LEDS_TEAM
#define N_TOTAL (N_HP + N_AMMO + N_TEAM)
#define FRAME_MS 20
#define FLASH_US 150000

typedef struct {
    uint8_t r, g, b;
} rgb_t;

static const rgb_t TEAM_COLORS[8] = {
    {255, 0, 0}, {0, 0, 255}, {0, 255, 0}, {255, 200, 0},
    {255, 0, 255}, {0, 255, 255}, {255, 255, 255}, {255, 80, 0},
};

static led_strip_handle_t s_strip;
static volatile int64_t s_flash_until;

void leds_flash_hit(void)
{
    s_flash_until = esp_timer_get_time() + FLASH_US;
}

static void put(int idx, rgb_t c, float scale)
{
    float k = scale * CONFIG_LT_LED_BRIGHTNESS / 255.0f;
    led_strip_set_pixel(s_strip, idx, c.r * k, c.g * k, c.b * k);
}

// green -> yellow -> red over the HP fraction
static rgb_t hp_color(float frac)
{
    if (frac > 0.5f) {
        return (rgb_t){(uint8_t)(255 * (1 - frac) * 2), 255, 0};
    }
    return (rgb_t){255, (uint8_t)(255 * frac * 2), 0};
}

static void render(const game_state_t *g, int64_t now)
{
    float t = now / 1e6f;
    bool blink = ((now / 250000) & 1) != 0;

    if (now < s_flash_until) {
        for (int i = 0; i < N_TOTAL; i++) {
            put(i, (rgb_t){255, 255, 255}, 1);
        }
        return;
    }

    // HP bar: 1 LED = 1/N_HP of max HP
    float frac = g->max_hp ? (float)g->hp / g->max_hp : 0;
    int lit = (int)ceilf(frac * N_HP);
    for (int i = 0; i < N_HP; i++) {
        if (!g->alive) {
            float pulse = 0.5f + 0.5f * sinf(t * 2 * (float)M_PI);  // red pulse while dead
            put(i, (rgb_t){255, 0, 0}, pulse);
        } else if (!g->running) {
            put(i, (rgb_t){0, 0, 0}, 0);
        } else if (i < lit && !(frac < 0.2f && blink)) {
            put(i, hp_color(frac), 1);
        } else {
            put(i, (rgb_t){0, 0, 0}, 0);
        }
    }

    // ammo bar, sweeping while reloading
    for (int i = 0; i < N_AMMO; i++) {
        int idx = N_HP + i;
        if (g->reloading) {
            int pos = (now / 60000) % N_AMMO;
            put(idx, (rgb_t){0, 120, 255}, i == pos ? 1 : 0);
        } else {
            int shown = g->magazine ? (g->ammo * N_AMMO + g->magazine - 1) / g->magazine : 0;
            bool empty_blink = g->ammo == 0 && blink;
            put(idx, (rgb_t){255, 140, 0}, i < shown || (empty_blink && i == 0) ? 1 : 0);
        }
    }

    // team pixels; status overlays: charging, offline, low battery
    rgb_t team = TEAM_COLORS[g->team & 7];
    for (int i = 0; i < N_TEAM; i++) {
        int idx = N_HP + N_AMMO + i;
        if (battery_charging()) {
            put(idx, (rgb_t){0, 255, 0}, 0.3f + 0.3f * sinf(t * 3));
        } else if (battery_low() && blink) {
            put(idx, (rgb_t){255, 0, 0}, 1);
        } else if (i == N_TEAM - 1 && !net_connected() && blink) {
            put(idx, (rgb_t){0, 0, 0}, 0);
        } else {
            put(idx, team, 1);
        }
    }
}

static void leds_task(void *arg)
{
    TickType_t last = xTaskGetTickCount();
    game_state_t g;
    while (true) {
        game_snapshot(&g);
        render(&g, esp_timer_get_time());
        led_strip_refresh(s_strip);
        vTaskDelayUntil(&last, pdMS_TO_TICKS(FRAME_MS));
    }
}

esp_err_t leds_start(void)
{
    led_strip_config_t cfg = {
        .strip_gpio_num = PIN_WS2812,
        .max_leds = N_TOTAL,
        .led_model = LED_MODEL_WS2812,
        .color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB,
    };
    led_strip_rmt_config_t rmt = {
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = 10 * 1000 * 1000,
        .mem_block_symbols = 48,
    };
    ESP_RETURN_ON_ERROR(led_strip_new_rmt_device(&cfg, &rmt, &s_strip), TAG, "strip");
    led_strip_clear(s_strip);
    BaseType_t ok = xTaskCreatePinnedToCore(leds_task, "leds", 3072, NULL, 5, NULL, 1);
    return ok == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}
