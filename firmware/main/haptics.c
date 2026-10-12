// One vibration motor for recoil and hit feedback, LEDC PWM, patterns stepped
// by esp_timer. A pattern only replaces a running one of equal or lower
// priority, so a shot's short kick never cuts off hit or death feedback.
#include "haptics.h"

#include "board.h"
#include "driver/ledc.h"
#include "esp_check.h"
#include "esp_timer.h"

#define TAG "haptics"
#define PWM_HZ 20000
#define PWM_RES LEDC_TIMER_10_BIT
#define DUTY_MAX ((1 << 10) - 1)

typedef struct {
    uint8_t duty_percent;
    uint16_t ms;
} step_t;

typedef struct {
    const step_t *steps;
    int count;
    int prio;
} pattern_t;

static const step_t RECOIL[] = {{100, 60}};
static const step_t HIT[] = {{100, 250}};
static const step_t DEATH[] = {{100, 400}, {0, 150}, {100, 400}, {0, 150}, {100, 900}};
static const step_t RESPAWN[] = {{80, 80}, {0, 80}, {80, 80}};

#define PAT(p, prio) {p, sizeof(p) / sizeof(p[0]), prio}
static const pattern_t PATTERNS[] = {
    [HAPTIC_RECOIL] = PAT(RECOIL, 0),
    [HAPTIC_HIT] = PAT(HIT, 1),
    [HAPTIC_RESPAWN] = PAT(RESPAWN, 1),
    [HAPTIC_DEATH] = PAT(DEATH, 2),
};

static esp_timer_handle_t s_timer;
static const pattern_t *s_pat;  // running pattern, NULL when idle
static int s_pos;

static void set_duty(uint8_t percent)
{
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, DUTY_MAX * percent / 100);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
}

static void step(void *arg)
{
    if (!s_pat || s_pos >= s_pat->count) {
        set_duty(0);
        s_pat = NULL;
        return;
    }
    const step_t *st = &s_pat->steps[s_pos++];
    set_duty(st->duty_percent);
    esp_timer_start_once(s_timer, st->ms * 1000);
}

void haptics_play(haptic_pattern_t pattern)
{
    const pattern_t *p = &PATTERNS[pattern];
    if (s_pat && s_pat->prio > p->prio) {
        return;
    }
    esp_timer_stop(s_timer);
    s_pat = p;
    s_pos = 0;
    step(NULL);
}

esp_err_t haptics_init(void)
{
    ledc_timer_config_t t = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = PWM_RES,
        .timer_num = LEDC_TIMER_0,
        .freq_hz = PWM_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ESP_RETURN_ON_ERROR(ledc_timer_config(&t), TAG, "timer");
    ledc_channel_config_t ch = {
        .gpio_num = PIN_VIB,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = LEDC_CHANNEL_0,
        .timer_sel = LEDC_TIMER_0,
        .duty = 0,
    };
    ESP_RETURN_ON_ERROR(ledc_channel_config(&ch), TAG, "channel");
    esp_timer_create_args_t args = {.callback = step, .name = "vib"};
    return esp_timer_create(&args, &s_timer);
}
