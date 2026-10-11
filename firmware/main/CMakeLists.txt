idf_component_register(
    SRCS main.c game.c ir_tx.c ir_rx.c nec.c input.c haptics.c leds.c audio.c battery.c
         net.c proto.c espnow.c
    INCLUDE_DIRS "."
    REQUIRES esp_driver_rmt esp_driver_gpio esp_driver_ledc esp_driver_i2s esp_adc esp_wifi
             esp_netif esp_event esp_timer esp_app_format nvs_flash mbedtls lwip
)
