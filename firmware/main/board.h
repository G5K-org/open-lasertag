// Pin assignment of the weapon board, see pinbelegung.md and
// kicad/waffe_elektronik (netlist U4).
#pragma once

#include "driver/gpio.h"

#define PIN_TRIGGER     GPIO_NUM_4   // active low, 10k pull-up + 100n
#define PIN_RELOAD      GPIO_NUM_5   // active low, 10k pull-up + 100n
#define PIN_IR_GATE     GPIO_NUM_6   // AO3400 gate, high = IR LED on
#define PIN_BAT_ADC     GPIO_NUM_8   // ADC1_CH7, 1M/1M divider straight from the cell (BAT_P)
#define PIN_WS2812      GPIO_NUM_17  // via 74HCT125 to the strip
#define PIN_I2S_DOUT    GPIO_NUM_38
#define PIN_I2S_BCLK    GPIO_NUM_39
#define PIN_I2S_LRCLK   GPIO_NUM_40
#define PIN_VIB         GPIO_NUM_47  // AO3400 gate, one motor for recoil and hit

// Operator panel: OLED on I2C (J4, Qwiic pinout, pull-ups on the display
// module) and rotary encoder with push button (J5, contacts to GND, use the
// internal pull-ups). Not used by the firmware yet.
#define PIN_I2C_SCL     GPIO_NUM_1
#define PIN_I2C_SDA     GPIO_NUM_2
#define PIN_ENC_A       GPIO_NUM_42
#define PIN_ENC_B       GPIO_NUM_41
#define PIN_ENC_SW      GPIO_NUM_21  // also switches the board on (IP5306 KEY through D6)

// IP5306-I2C charger + 5 V boost (U1) on its own I2C bus, 4.7k pull-ups
#define PIN_IP5306_SCL  GPIO_NUM_18
#define PIN_IP5306_SDA  GPIO_NUM_9
#define IP5306_ADDR     0x75

// TSOP34838 outputs, idle high, low while a 38 kHz burst is received.
// Index = sensor number - 1.
#define PIN_TSOP1       GPIO_NUM_10  // headband front
#define PIN_TSOP2       GPIO_NUM_11  // headband back
#define PIN_TSOP3       GPIO_NUM_12  // chest
#define PIN_TSOP4       GPIO_NUM_13  // back
#define PIN_TSOP5       GPIO_NUM_14  // shoulders (optional)
#define PIN_TSOP6       GPIO_NUM_16  // on the weapon itself, connector J6

#define BAT_DIVIDER     2            // BAT_P = 2 * ADC voltage
#define BAT_ADC_UNIT    ADC_UNIT_1
#define BAT_ADC_CHANNEL ADC_CHANNEL_7
