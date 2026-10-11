#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

esp_err_t battery_start(void);
uint16_t battery_mv(void);
uint8_t battery_percent(void);
bool battery_low(void);
bool battery_charging(void);
