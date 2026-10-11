#pragma once

#include <stdbool.h>
#include "esp_err.h"

// Poll trigger and reload, post EV_TRIGGER_* / EV_RELOAD_DOWN.
esp_err_t input_start(void);
bool input_trigger_held(void);
