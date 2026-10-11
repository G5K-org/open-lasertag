#pragma once

#include "esp_err.h"

// Start the IR receive task (core 1). Valid NEC frames are posted to the
// game task as EV_IR_FRAME.
esp_err_t ir_rx_start(void);
