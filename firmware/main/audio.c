// Sound effects on the MAX98357A. Mono 16 bit; the amp plays the left slot
// (SD tied to 5V_PERIPH), mono mode puts the same sample in both slots.
#include "audio.h"

#include <math.h>
#include <stdlib.h>
#include "board.h"
#include "driver/i2s_std.h"
#include "esp_check.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "sdkconfig.h"

#define TAG "audio"
#define RATE 22050
#define CHUNK 256

typedef enum { WAVE_SQUARE, WAVE_NOISE, WAVE_SINE } wave_t;

// One segment: frequency sweep f0 -> f1 over ms, amplitude a0 -> a1 (0..1)
typedef struct {
    wave_t wave;
    uint16_t f0, f1;
    uint16_t ms;
    float a0, a1;
} seg_t;

typedef struct {
    const seg_t *segs;
    int count;
} sfx_t;

#define SFX(arr) {arr, sizeof(arr) / sizeof(arr[0])}

static const seg_t SHOT[] = {
    {WAVE_SQUARE, 1800, 300, 110, 1.0f, 0.1f},
    {WAVE_NOISE, 0, 0, 40, 0.3f, 0.0f},
};
static const seg_t EMPTY[] = {{WAVE_NOISE, 0, 0, 15, 0.6f, 0.0f}};
static const seg_t RELOAD[] = {
    {WAVE_NOISE, 0, 0, 25, 0.7f, 0.0f},
    {WAVE_SINE, 0, 0, 180, 0, 0},
    {WAVE_NOISE, 0, 0, 25, 0.8f, 0.0f},
    {WAVE_SQUARE, 900, 1200, 60, 0.4f, 0.2f},
};
static const seg_t HIT[] = {
    {WAVE_SQUARE, 220, 110, 250, 1.0f, 0.2f},
};
static const seg_t DEATH[] = {
    {WAVE_SQUARE, 440, 330, 300, 0.9f, 0.7f},
    {WAVE_SQUARE, 330, 220, 300, 0.8f, 0.6f},
    {WAVE_SQUARE, 220, 80, 700, 0.7f, 0.0f},
};
static const seg_t RESPAWN[] = {
    {WAVE_SQUARE, 523, 523, 90, 0.6f, 0.6f},
    {WAVE_SQUARE, 659, 659, 90, 0.6f, 0.6f},
    {WAVE_SQUARE, 784, 784, 90, 0.6f, 0.6f},
    {WAVE_SQUARE, 1047, 1047, 180, 0.6f, 0.0f},
};
static const seg_t START[] = {
    {WAVE_SINE, 880, 880, 150, 0.8f, 0.8f},
    {WAVE_SINE, 0, 0, 80, 0, 0},
    {WAVE_SINE, 1760, 1760, 300, 0.8f, 0.0f},
};

static const seg_t HIT_CONFIRM[] = {{WAVE_SINE, 2400, 2400, 45, 0.7f, 0.0f}};
static const seg_t KILL_CONFIRM[] = {
    {WAVE_SINE, 1800, 1800, 70, 0.7f, 0.5f},
    {WAVE_SINE, 0, 0, 30, 0, 0},
    {WAVE_SINE, 2700, 2700, 150, 0.8f, 0.0f},
};

static const sfx_t SOUNDS[] = {
    [SND_SHOT] = SFX(SHOT),       [SND_EMPTY] = SFX(EMPTY),
    [SND_RELOAD] = SFX(RELOAD),   [SND_HIT] = SFX(HIT),
    [SND_DEATH] = SFX(DEATH),     [SND_RESPAWN] = SFX(RESPAWN),
    [SND_START] = SFX(START),
    [SND_HIT_CONFIRM] = SFX(HIT_CONFIRM), [SND_KILL_CONFIRM] = SFX(KILL_CONFIRM),
};

static i2s_chan_handle_t s_tx;
static QueueHandle_t s_q;

void audio_play(sound_t s)
{
    if (s_q) {
        xQueueOverwrite(s_q, &s);  // a new sound replaces a queued one
    }
}

// Render one segment; returns false if a new sound interrupted it.
static bool play_seg(const seg_t *seg, int16_t *buf)
{
    const float vol = CONFIG_LT_AUDIO_VOLUME / 100.0f * 32000;
    int total = RATE * seg->ms / 1000;
    float phase = 0;
    uint32_t lfsr = 0xace1u;
    int16_t noise = 0;

    for (int pos = 0; pos < total;) {
        int n = total - pos < CHUNK ? total - pos : CHUNK;
        for (int i = 0; i < n; i++, pos++) {
            float x = (float)pos / total;
            float f = seg->f0 + (seg->f1 - seg->f0) * x;
            float a = (seg->a0 + (seg->a1 - seg->a0) * x) * vol;
            float v;
            switch (seg->wave) {
            case WAVE_SQUARE: v = phase < 0.5f ? 1 : -1; break;
            case WAVE_SINE: v = sinf(phase * 2 * (float)M_PI); break;
            default:
                if ((pos & 3) == 0) {  // ~5.5 kHz noise
                    lfsr = (lfsr >> 1) ^ (-(lfsr & 1u) & 0xb400u);
                    noise = (int16_t)lfsr;
                }
                v = noise / 32768.0f;
            }
            phase += f / RATE;
            if (phase >= 1) {
                phase -= 1;
            }
            buf[i] = (int16_t)(v * a);
        }
        size_t written;
        i2s_channel_write(s_tx, buf, n * sizeof(int16_t), &written, portMAX_DELAY);
        if (uxQueueMessagesWaiting(s_q)) {
            return false;
        }
    }
    return true;
}

static void audio_task(void *arg)
{
    static int16_t buf[CHUNK];
    sound_t s;
    while (true) {
        xQueueReceive(s_q, &s, portMAX_DELAY);
        const sfx_t *fx = &SOUNDS[s];
        for (int i = 0; i < fx->count; i++) {
            if (!play_seg(&fx->segs[i], buf)) {
                break;
            }
        }
    }
}

esp_err_t audio_start(void)
{
    i2s_chan_config_t chan = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    chan.auto_clear_after_cb = true;  // output silence when no sound is queued
    ESP_RETURN_ON_ERROR(i2s_new_channel(&chan, &s_tx, NULL), TAG, "channel");

    i2s_std_config_t std = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT,
                                                        I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = PIN_I2S_BCLK,
            .ws = PIN_I2S_LRCLK,
            .dout = PIN_I2S_DOUT,
            .din = I2S_GPIO_UNUSED,
        },
    };
    ESP_RETURN_ON_ERROR(i2s_channel_init_std_mode(s_tx, &std), TAG, "std mode");
    ESP_RETURN_ON_ERROR(i2s_channel_enable(s_tx), TAG, "enable");

    s_q = xQueueCreate(1, sizeof(sound_t));
    BaseType_t ok = xTaskCreatePinnedToCore(audio_task, "audio", 3072, NULL, 8, NULL, 0);
    return ok == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}
