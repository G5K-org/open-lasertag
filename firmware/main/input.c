// Trigger and reload buttons. Both have an RC filter on the board; a 2 ms
// poll with a short counter removes the remaining bounce.
#include "input.h"

#include "board.h"
#include "esp_check.h"
#include "esp_timer.h"
#include "events.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define TAG "input"
#define POLL_MS 2
#define STABLE_POLLS 4

typedef struct {
    gpio_num_t pin;
    event_type_t ev_down;
    event_type_t ev_up;  // EV_RELOAD_DOWN for "none"
    bool pressed;
    uint8_t count;
} button_t;

static button_t s_buttons[] = {
    {.pin = PIN_TRIGGER, .ev_down = EV_TRIGGER_DOWN, .ev_up = EV_TRIGGER_UP},
    {.pin = PIN_RELOAD, .ev_down = EV_RELOAD_DOWN, .ev_up = EV_RELOAD_DOWN},
};

static void input_task(void *arg)
{
    TickType_t last = xTaskGetTickCount();
    while (true) {
        for (int i = 0; i < sizeof(s_buttons) / sizeof(s_buttons[0]); i++) {
            button_t *b = &s_buttons[i];
            bool level_pressed = gpio_get_level(b->pin) == 0;
            if (level_pressed == b->pressed) {
                b->count = 0;
                continue;
            }
            if (++b->count < STABLE_POLLS) {
                continue;
            }
            b->count = 0;
            b->pressed = level_pressed;
            if (b->pressed || b->ev_up != b->ev_down) {
                event_t ev = {
                    .type = b->pressed ? b->ev_down : b->ev_up,
                    .time_us = esp_timer_get_time(),
                };
                game_post(&ev);
            }
        }
        vTaskDelayUntil(&last, pdMS_TO_TICKS(POLL_MS));
    }
}

bool input_trigger_held(void)
{
    return s_buttons[0].pressed;
}

esp_err_t input_start(void)
{
    gpio_config_t io = {
        .pin_bit_mask = 1ULL << PIN_TRIGGER | 1ULL << PIN_RELOAD,
        .mode = GPIO_MODE_INPUT,
    };
    ESP_RETURN_ON_ERROR(gpio_config(&io), TAG, "gpio");
    BaseType_t ok = xTaskCreatePinnedToCore(input_task, "input", 2560, NULL, 12, NULL, 1);
    return ok == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}
