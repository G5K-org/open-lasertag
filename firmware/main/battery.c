// Battery voltage (ADC1_CH7 behind a 1:2 divider) and the IP5306 charger / 5 V boost (U1, I2C):
// configures it at every start and reads the charge state.
#include "battery.h"

#include "board.h"
#include "driver/i2c_master.h"
#include "driver/usb_serial_jtag.h"
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
static volatile bool s_charging;
static bool s_host;
static i2c_master_dev_handle_t s_ip;

// IP5306 registers (read -> change the bit -> write back, other bits keep their value)
#define REG_SYS_CTL0 0x00     // bit 1 boost stays on at light load, bit 0 key may switch off
#define REG_SYS_CTL1 0x01     // bit 7 off = long press (not double click), bit 2 5 V on after USB is unplugged
#define REG_SYS_CTL2 0x02     // bit 3:2 light load off time, 00 = 8 s
#define REG_CHG_DIG  0x24     // bit 4:0 charge current on the USB side: 0.05 A + n * 0.1 A
#define REG_READ0    0x70     // bit 3 charging
#define CHG_CURRENT  0x10     // 1.65 A from USB, about 2 A into the cell (USB charger)
#define CHG_HOST     0x04     // 0.45 A: data connection to a computer, its port only guarantees 0.5 A

static esp_err_t ip_read(uint8_t reg, uint8_t *val)
{
    return i2c_master_transmit_receive(s_ip, &reg, 1, val, 1, 50);
}

static esp_err_t ip_update(uint8_t reg, uint8_t mask, uint8_t bits)
{
    uint8_t v;
    ESP_RETURN_ON_ERROR(ip_read(reg, &v), TAG, "read 0x%02x", reg);
    uint8_t buf[2] = {reg, (uint8_t)((v & ~mask) | (bits & mask))};
    return i2c_master_transmit(s_ip, buf, 2, 50);
}

static esp_err_t ip5306_setup(void)
{
    i2c_master_bus_config_t bus = {
        .i2c_port = I2C_NUM_1,  // port 0 stays free for the OLED
        .sda_io_num = PIN_IP5306_SDA,
        .scl_io_num = PIN_IP5306_SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    i2c_master_bus_handle_t h;
    ESP_RETURN_ON_ERROR(i2c_new_master_bus(&bus, &h), TAG, "i2c bus");
    i2c_device_config_t dev = {.dev_addr_length = I2C_ADDR_BIT_LEN_7, .device_address = IP5306_ADDR,
                               .scl_speed_hz = 100000};
    ESP_RETURN_ON_ERROR(i2c_master_bus_add_device(h, &dev, &s_ip), TAG, "i2c dev");
    ESP_RETURN_ON_ERROR(ip_update(REG_SYS_CTL0, 0x03, 0x03), TAG, "ctl0");
    ESP_RETURN_ON_ERROR(ip_update(REG_SYS_CTL1, 0x84, 0x84), TAG, "ctl1");
    ESP_RETURN_ON_ERROR(ip_update(REG_SYS_CTL2, 0x0c, 0x00), TAG, "ctl2");
    s_host = usb_serial_jtag_is_connected();
    return ip_update(REG_CHG_DIG, 0x1f, s_host ? CHG_HOST : CHG_CURRENT);
}

void battery_power_off(void)
{
    if (s_ip) {
        ip_update(REG_SYS_CTL0, 0x02, 0x00);  // allow the light load shutdown
    }
}

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
    return s_charging;
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
        uint8_t r;
        s_charging = s_ip && ip_read(REG_READ0, &r) == ESP_OK && (r & 0x08);
        // charge current: full only on a charger; a computer port (USB data, SOF seen) may cut off above 0.5 A
        bool host = usb_serial_jtag_is_connected();
        if (s_ip && host != s_host) {
            if (ip_update(REG_CHG_DIG, 0x1f, host ? CHG_HOST : CHG_CURRENT) == ESP_OK) {
                s_host = host;
            }
        }
    }
}

esp_err_t battery_start(void)
{
    if (ip5306_setup() != ESP_OK) {
        ESP_LOGW(TAG, "IP5306 not answering, no charge state");  // e.g. USB only, no cell
        s_ip = NULL;
    }

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
