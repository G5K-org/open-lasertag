// Recoil and hit vibration motors on LEDC PWM, patterns stepped by esp_timer.
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
    ledc_channel_t channel;
    esp_timer_handle_t timer;
    const step_t *steps;
    int count;
    int pos;
} motor_t;

static const step_t RECOIL[] = {{100, 60}};
static const step_t HIT[] = {{100, 250}};
static const step_t DEATH[] = {{100, 400}, {0, 150}, {100, 400}, {0, 150}, {100, 900}};
static const step_t RESPAWN[] = {{80, 80}, {0, 80}, {80, 80}};

static motor_t s_recoil = {.channel = LEDC_CHANNEL_0};
static motor_t s_hit = {.channel = LEDC_CHANNEL_1};

static void set_duty(motor_t *m, uint8_t percent)
{
    ledc_set_duty(LEDC_LOW_SPEED_MODE, m->channel, DUTY_MAX * percent / 100);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, m->channel);
}

static void step(void *arg)
{
    motor_t *m = arg;
    if (m->pos >= m->count) {
        set_duty(m, 0);
        return;
    }
    const step_t *s = &m->steps[m->pos++];
    set_duty(m, s->duty_percent);
    esp_timer_start_once(m->timer, s->ms * 1000);
}

static void start(motor_t *m, const step_t *steps, int count)
{
    esp_timer_stop(m->timer);
    m->steps = steps;
    m->count = count;
    m->pos = 0;
    step(m);
}

void haptics_play(haptic_pattern_t pattern)
{
#define START(m, p) start(m, p, sizeof(p) / sizeof(p[0]))
    switch (pattern) {
    case HAPTIC_RECOIL: START(&s_recoil, RECOIL); break;
    case HAPTIC_HIT: START(&s_hit, HIT); break;
    case HAPTIC_DEATH: START(&s_hit, DEATH); break;
    case HAPTIC_RESPAWN: START(&s_hit, RESPAWN); break;
    }
#undef START
}

static esp_err_t motor_init(motor_t *m, gpio_num_t pin, const char *name)
{
    ledc_channel_config_t ch = {
        .gpio_num = pin,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = m->channel,
        .timer_sel = LEDC_TIMER_0,
        .duty = 0,
    };
    ESP_RETURN_ON_ERROR(ledc_channel_config(&ch), TAG, "channel");
    esp_timer_create_args_t args = {.callback = step, .arg = m, .name = name};
    return esp_timer_create(&args, &m->timer);
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
    ESP_RETURN_ON_ERROR(motor_init(&s_recoil, PIN_RECOIL_VIB, "recoil"), TAG, "recoil");
    return motor_init(&s_hit, PIN_HIT_VIB, "hit");
}
