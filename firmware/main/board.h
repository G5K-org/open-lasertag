// Pin assignment of the weapon board, see pinbelegung.md and
// kicad/waffe_elektronik (netlist U4).
#pragma once

#include "driver/gpio.h"

#define PIN_TRIGGER     GPIO_NUM_4   // active low, 10k pull-up + 100n
#define PIN_RELOAD      GPIO_NUM_5   // active low, 10k pull-up + 100n
#define PIN_IR_GATE     GPIO_NUM_6   // AO3400 gate, high = IR LED on
#define PIN_BAT_ADC     GPIO_NUM_8   // ADC1_CH7, 100k/100k divider from BAT_P
#define PIN_WS2812      GPIO_NUM_17  // via 74HCT125 to the strip
#define PIN_CHRG_STAT   GPIO_NUM_18  // MCP73831 STAT, 10k pull-up, low = charging
#define PIN_I2S_DOUT    GPIO_NUM_38
#define PIN_I2S_BCLK    GPIO_NUM_39
#define PIN_I2S_LRCLK   GPIO_NUM_40
#define PIN_HIT_VIB     GPIO_NUM_47  // AO3400 gate
#define PIN_RECOIL_VIB  GPIO_NUM_48  // AO3400 gate

// TSOP34838 outputs, idle high, low while a 38 kHz burst is received.
// Index = sensor number - 1.
#define PIN_TSOP1       GPIO_NUM_10  // headband front
#define PIN_TSOP2       GPIO_NUM_11  // headband back
#define PIN_TSOP3       GPIO_NUM_12  // chest
#define PIN_TSOP4       GPIO_NUM_13  // back
#define PIN_TSOP5       GPIO_NUM_14  // shoulders (optional)
#define PIN_TSOP6       GPIO_NUM_21  // weapon front, not wired yet

#define BAT_DIVIDER     2            // BAT_P = 2 * ADC voltage
#define BAT_ADC_UNIT    ADC_UNIT_1
#define BAT_ADC_CHANNEL ADC_CHANNEL_7
