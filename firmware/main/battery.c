// Battery voltage (ADC1_CH7 behind a 1:2 divider) and MCP73831 charge status.
#include "battery.h"

#include "board.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_check.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define TAG "battery"
#define SAMPLES 16
#define PERIOD_MS 1000
#define LOW_MV 3450

static adc_oneshot_unit_handle_t s_adc;
static adc_cali_handle_t s_cali;
static volatile uint16_t s_mv;

// 1S LiPo, resting voltage -> charge (approximate)
static const uint16_t CURVE_MV[] = {3300, 3500, 3600, 3700, 3750, 3800, 3850, 3950, 4050, 4200};
static const uint8_t CURVE_PCT[] = {0, 5, 10, 20, 30, 40, 50, 65, 80, 100};

uint16_t battery_mv(void)
{
    return s_mv;
}

uint8_t battery_percent(void)
{
    uint16_t mv = s_mv;
    int n = sizeof(CURVE_MV) / sizeof(CURVE_MV[0]);
    if (mv <= CURVE_MV[0]) {
        return 0;
    }
    for (int i = 1; i < n; i++) {
        if (mv <= CURVE_MV[i]) {
            return CURVE_PCT[i - 1] + (CURVE_PCT[i] - CURVE_PCT[i - 1]) * (mv - CURVE_MV[i - 1]) /
                                          (CURVE_MV[i] - CURVE_MV[i - 1]);
        }
    }
    return 100;
}

bool battery_low(void)
{
    return s_mv > 0 && s_mv < LOW_MV && !battery_charging();
}

bool battery_charging(void)
{
    return gpio_get_level(PIN_CHRG_STAT) == 0;  // STAT low = charging
}

static uint16_t measure(void)
{
    int sum = 0, ok = 0;
    for (int i = 0; i < SAMPLES; i++) {
        int raw, mv;
        if (adc_oneshot_read(s_adc, BAT_ADC_CHANNEL, &raw) != ESP_OK) {
            continue;
        }
        if (s_cali && adc_cali_raw_to_voltage(s_cali, raw, &mv) == ESP_OK) {
            sum += mv;
        } else {
            sum += raw * 3100 / 4095;  // uncalibrated fallback
        }
        ok++;
    }
    return ok ? sum / ok * BAT_DIVIDER : 0;
}

static void battery_task(void *arg)
{
    s_mv = measure();
    while (true) {
        vTaskDelay(pdMS_TO_TICKS(PERIOD_MS));
        uint16_t mv = measure();
        s_mv = (s_mv * 7 + mv) / 8;  // IR pulses and motors cause dips
    }
}

esp_err_t battery_start(void)
{
    gpio_config_t io = {
        .pin_bit_mask = 1ULL << PIN_CHRG_STAT,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
    };
    ESP_RETURN_ON_ERROR(gpio_config(&io), TAG, "gpio");

    adc_oneshot_unit_init_cfg_t unit = {.unit_id = BAT_ADC_UNIT};
    ESP_RETURN_ON_ERROR(adc_oneshot_new_unit(&unit, &s_adc), TAG, "adc unit");
    adc_oneshot_chan_cfg_t ch = {.atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT};
    ESP_RETURN_ON_ERROR(adc_oneshot_config_channel(s_adc, BAT_ADC_CHANNEL, &ch), TAG, "channel");

    adc_cali_curve_fitting_config_t cali = {
        .unit_id = BAT_ADC_UNIT,
        .chan = BAT_ADC_CHANNEL,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    if (adc_cali_create_scheme_curve_fitting(&cali, &s_cali) != ESP_OK) {
        ESP_LOGW(TAG, "no ADC calibration in eFuse, using raw values");
        s_cali = NULL;
    }
    BaseType_t ok = xTaskCreatePinnedToCore(battery_task, "battery", 2560, NULL, 3, NULL, 0);
    return ok == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}
