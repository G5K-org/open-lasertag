idf_component_register(
    SRCS gateway.c
    REQUIRES esp_wifi esp_netif esp_event nvs_flash esp_driver_usb_serial_jtag esp_timer
)
