// IR receiver for up to 6 TSOP34838.
// The S3 has only 4 RMT RX channels: TSOP 1-4 use RMT, TSOP 5/6 are timed
// with GPIO edge interrupts. Both paths deliver mark/space pairs to the same
// NEC decoder.
#include "ir_rx.h"

#include <string.h>
#include "board.h"
#include "driver/gpio.h"
#include "driver/rmt_rx.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "events.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "ir_tx.h"
#include "nec.h"
#include "sdkconfig.h"

#define TAG "ir_rx"
#define RMT_SENSORS 4
#define MAX_PAIRS 64
#define FRAME_IDLE_US 6000  // longest gap inside a frame is the 4.5 ms header space
#define FRAME_LEN_US 68000  // approx. NEC frame duration, for TX overlap checks

typedef struct {
    uint8_t sensor;
    uint16_t count;
    int64_t end_us;
} rx_done_t;

static const gpio_num_t s_rmt_pins[RMT_SENSORS] = {PIN_TSOP1, PIN_TSOP2, PIN_TSOP3, PIN_TSOP4};
static rmt_channel_handle_t s_rmt[RMT_SENSORS];
// callback context must live in internal RAM (RMT_ISR_IRAM_SAFE)
static uint8_t s_rmt_sensor[RMT_SENSORS] = {0, 1, 2, 3};
static rmt_symbol_word_t s_rmt_buf[RMT_SENSORS][MAX_PAIRS];
static QueueHandle_t s_done_q;
static TaskHandle_t s_starter;
static const rmt_receive_config_t s_rx_cfg = {
    .signal_range_min_ns = 1250,                   // glitch filter
    .signal_range_max_ns = FRAME_IDLE_US * 1000,   // idle -> frame done
};

// ---- software receivers (GPIO interrupt) --------------------------------

typedef struct {
    gpio_num_t pin;
    uint8_t sensor;
    nec_pair_t pairs[MAX_PAIRS];
    volatile uint16_t count;
    volatile int64_t mark_start_us;  // falling edge time
    volatile int64_t last_edge_us;
    volatile bool in_mark;
    volatile bool active;
} soft_rx_t;

static soft_rx_t s_soft[2];
static int s_soft_count;
static portMUX_TYPE s_soft_lock = portMUX_INITIALIZER_UNLOCKED;

static void IRAM_ATTR soft_isr(void *arg)
{
    soft_rx_t *rx = arg;
    int64_t now = esp_timer_get_time();
    bool low = gpio_get_level(rx->pin) == 0;  // TSOP low = carrier present

    portENTER_CRITICAL_ISR(&s_soft_lock);
    if (low && !rx->in_mark) {
        if (rx->active && rx->count > 0 && rx->count <= MAX_PAIRS) {
            uint32_t space = now - rx->last_edge_us;
            rx->pairs[rx->count - 1].space_us = space > 0xffff ? 0xffff : space;
        }
        rx->mark_start_us = now;
        rx->in_mark = true;
        rx->active = true;
    } else if (!low && rx->in_mark) {
        uint32_t mark = now - rx->mark_start_us;
        rx->in_mark = false;
        if (mark >= 2 && rx->count < MAX_PAIRS) {
            rx->pairs[rx->count++] = (nec_pair_t){mark > 0xffff ? 0xffff : mark, 0};
        }
    }
    rx->last_edge_us = now;
    portEXIT_CRITICAL_ISR(&s_soft_lock);
}

static esp_err_t soft_rx_add(gpio_num_t pin, uint8_t sensor)
{
    soft_rx_t *rx = &s_soft[s_soft_count++];
    *rx = (soft_rx_t){.pin = pin, .sensor = sensor};
    gpio_config_t io = {
        .pin_bit_mask = 1ULL << pin,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .intr_type = GPIO_INTR_ANYEDGE,
    };
    ESP_RETURN_ON_ERROR(gpio_config(&io), TAG, "gpio");
    return gpio_isr_handler_add(pin, soft_isr, rx);
}

// ---- RMT receivers ------------------------------------------------------

static bool IRAM_ATTR on_rmt_recv(rmt_channel_handle_t chan, const rmt_rx_done_event_data_t *ev,
                                  void *ctx)
{
    BaseType_t woken = pdFALSE;
    rx_done_t done = {
        .sensor = *(const uint8_t *)ctx,
        .count = ev->num_symbols,
        .end_us = esp_timer_get_time(),
    };
    xQueueSendFromISR(s_done_q, &done, &woken);
    return woken == pdTRUE;
}

static esp_err_t rmt_rx_add(int idx)
{
    rmt_rx_channel_config_t cfg = {
        .gpio_num = s_rmt_pins[idx],
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = 1000000,  // 1 tick = 1 us
        .mem_block_symbols = 48,
        .flags.invert_in = true,   // carrier present -> level 1
    };
    ESP_RETURN_ON_ERROR(rmt_new_rx_channel(&cfg, &s_rmt[idx]), TAG, "rx channel %d", idx);
    rmt_rx_event_callbacks_t cbs = {.on_recv_done = on_rmt_recv};
    ESP_RETURN_ON_ERROR(rmt_rx_register_event_callbacks(s_rmt[idx], &cbs, &s_rmt_sensor[idx]),
                        TAG, "cb");
    ESP_RETURN_ON_ERROR(rmt_enable(s_rmt[idx]), TAG, "enable");
    // TSOP open collector output: the vest has pull-ups, the internal one
    // keeps an unplugged sensor line quiet
    gpio_pullup_en(s_rmt_pins[idx]);
    return rmt_receive(s_rmt[idx], s_rmt_buf[idx], sizeof(s_rmt_buf[idx]), &s_rx_cfg);
}

// ---- decoding -----------------------------------------------------------

static void handle_pairs(uint8_t sensor, const nec_pair_t *pairs, int n, int64_t end_us)
{
    uint8_t addr, cmd;
    nec_result_t r = nec_decode(pairs, n, &addr, &cmd);
    if (r != NEC_FRAME) {
        return;  // repeat codes and noise are ignored
    }
    if (ir_tx_overlaps(end_us - FRAME_LEN_US, end_us)) {
        ESP_LOGD(TAG, "TSOP%d: frame during own shot ignored", sensor + 1);
        return;
    }
    ESP_LOGD(TAG, "TSOP%d: team %u player %u", sensor + 1, addr, cmd);
    event_t ev = {
        .type = EV_IR_FRAME,
        .time_us = end_us,
        .ir = {.team = addr, .player = cmd, .sensor = sensor},
    };
    game_post(&ev);
}

static void poll_soft(int64_t now)
{
    for (int i = 0; i < s_soft_count; i++) {
        soft_rx_t *rx = &s_soft[i];
        nec_pair_t pairs[MAX_PAIRS];
        int n = 0;
        int64_t end = 0;

        portENTER_CRITICAL(&s_soft_lock);
        if (rx->active && !rx->in_mark && now - rx->last_edge_us > FRAME_IDLE_US) {
            n = rx->count;
            end = rx->last_edge_us;
            memcpy(pairs, rx->pairs, n * sizeof(nec_pair_t));
            rx->count = 0;
            rx->active = false;
        }
        portEXIT_CRITICAL(&s_soft_lock);

        if (n > 0) {
            handle_pairs(rx->sensor, pairs, n, end);
        }
    }
}

static esp_err_t ir_rx_init(void)
{
    for (int i = 0; i < RMT_SENSORS; i++) {
        ESP_RETURN_ON_ERROR(rmt_rx_add(i), TAG, "TSOP%d", i + 1);
    }
    esp_err_t err = gpio_install_isr_service(0);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        return err;
    }
#if CONFIG_LT_TSOP5_ENABLE
    ESP_RETURN_ON_ERROR(soft_rx_add(PIN_TSOP5, 4), TAG, "TSOP5");
#endif
#if CONFIG_LT_TSOP6_ENABLE
    ESP_RETURN_ON_ERROR(soft_rx_add(PIN_TSOP6, 5), TAG, "TSOP6");
#endif
    return ESP_OK;
}

static void ir_rx_task(void *arg)
{
    // Channels and interrupts are created here so that their ISRs are
    // allocated on core 1, away from WLAN on core 0.
    esp_err_t *result = arg;
    *result = ir_rx_init();
    xTaskNotifyGive(s_starter);
    if (*result != ESP_OK) {
        vTaskDelete(NULL);
    }

    nec_pair_t pairs[MAX_PAIRS];
    while (true) {
        rx_done_t done;
        // short timeout so the software receivers are finalised in time
        if (xQueueReceive(s_done_q, &done, pdMS_TO_TICKS(2)) == pdTRUE) {
            int n = done.count > MAX_PAIRS ? MAX_PAIRS : done.count;
            for (int i = 0; i < n; i++) {
                rmt_symbol_word_t s = s_rmt_buf[done.sensor][i];
                pairs[i] = (nec_pair_t){s.level0 ? s.duration0 : 0, s.level0 ? s.duration1 : 0};
            }
            rmt_receive(s_rmt[done.sensor], s_rmt_buf[done.sensor], sizeof(s_rmt_buf[0]),
                        &s_rx_cfg);
            handle_pairs(done.sensor, pairs, n, done.end_us);
        }
        poll_soft(esp_timer_get_time());
    }
}

esp_err_t ir_rx_start(void)
{
    s_done_q = xQueueCreate(16, sizeof(rx_done_t));
    if (!s_done_q) {
        return ESP_ERR_NO_MEM;
    }
    static esp_err_t result;
    s_starter = xTaskGetCurrentTaskHandle();
    if (xTaskCreatePinnedToCore(ir_rx_task, "ir_rx", 4096, &result, 20, NULL, 1) != pdPASS) {
        return ESP_ERR_NO_MEM;
    }
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    return result;
}
