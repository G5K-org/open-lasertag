// IR transmitter: RMT TX with 38 kHz carrier on the IR MOSFET gate.
#include "ir_tx.h"

#include "board.h"
#include "driver/rmt_tx.h"
#include "esp_check.h"
#include "esp_timer.h"
#include "nec.h"
#include "sdkconfig.h"

#define TAG "ir_tx"
#define FRAME_PAIRS 34
#define SHOT_PAIRS (2 * FRAME_PAIRS)
// Receivers may still finish decoding a reflection of our own shot
#define ECHO_GUARD_US 20000

static rmt_channel_handle_t s_chan;
static rmt_encoder_handle_t s_copy;
static rmt_symbol_word_t s_symbols[SHOT_PAIRS];
static volatile int64_t s_tx_start_us = -1;
static volatile int64_t s_tx_end_us = -1;

static bool IRAM_ATTR on_tx_done(rmt_channel_handle_t chan, const rmt_tx_done_event_data_t *ev,
                                 void *ctx)
{
    s_tx_end_us = esp_timer_get_time();
    return false;
}

esp_err_t ir_tx_init(void)
{
    rmt_tx_channel_config_t cfg = {
        .gpio_num = PIN_IR_GATE,
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = 1000000,
        .mem_block_symbols = 48,
        .trans_queue_depth = 2,
    };
    ESP_RETURN_ON_ERROR(rmt_new_tx_channel(&cfg, &s_chan), TAG, "tx channel");

    rmt_carrier_config_t carrier = {
        .frequency_hz = 38000,
        .duty_cycle = CONFIG_LT_IR_DUTY_PERCENT / 100.0f,
    };
    ESP_RETURN_ON_ERROR(rmt_apply_carrier(s_chan, &carrier), TAG, "carrier");

    rmt_tx_event_callbacks_t cbs = {.on_trans_done = on_tx_done};
    ESP_RETURN_ON_ERROR(rmt_tx_register_event_callbacks(s_chan, &cbs, NULL), TAG, "cb");

    rmt_copy_encoder_config_t enc_cfg = {};
    ESP_RETURN_ON_ERROR(rmt_new_copy_encoder(&enc_cfg, &s_copy), TAG, "encoder");
    return rmt_enable(s_chan);
}

esp_err_t ir_tx_shot(uint8_t team, uint8_t player)
{
    if (s_tx_start_us > s_tx_end_us) {
        return ESP_ERR_INVALID_STATE;  // previous shot still on air
    }
    nec_pair_t pairs[FRAME_PAIRS];
    for (int f = 0; f < 2; f++) {
        uint16_t gap = f == 0 ? CONFIG_LT_IR_FRAME_GAP_MS * 1000 : 1000;
        nec_encode(team, player, gap, pairs);
        for (int i = 0; i < FRAME_PAIRS; i++) {
            s_symbols[f * FRAME_PAIRS + i] = (rmt_symbol_word_t){
                .level0 = 1, .duration0 = pairs[i].mark_us,
                .level1 = 0, .duration1 = pairs[i].space_us,
            };
        }
    }
    rmt_transmit_config_t tx = {.loop_count = 0};
    s_tx_start_us = esp_timer_get_time();
    esp_err_t err = rmt_transmit(s_chan, s_copy, s_symbols, sizeof(s_symbols), &tx);
    if (err != ESP_OK) {
        s_tx_end_us = s_tx_start_us;
    }
    return err;
}

bool ir_tx_overlaps(int64_t from_us, int64_t to_us)
{
    int64_t start = s_tx_start_us, end = s_tx_end_us;
    if (start < 0) {
        return false;
    }
    if (start > end) {
        return to_us >= start;  // still sending
    }
    return to_us >= start && from_us <= end + ECHO_GUARD_US;
}
