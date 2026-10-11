// Network: WLAN station plus one UDP socket to the server.
// One task owns the socket and the resend buffer; other tasks hand in
// reports through a queue.
#include "net.h"

#include <string.h>
#include "battery.h"
#include "esp_app_desc.h"
#include "esp_check.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "events.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "game.h"
#include "lwip/inet.h"
#include "lwip/sockets.h"
#include "proto.h"
#include "sdkconfig.h"

#define TAG "net"
#define PKT_MAX (sizeof(pkt_hdr_t) + PROTO_MAX_PAYLOAD + PROTO_MAC_LEN)
#define PENDING_MAX 32
#define RESEND_US 250000
#define STATUS_US 1000000
#define PING_US 1000000
#define ROAM_SCAN_HOLDOFF_US 10000000
#define ROAM_MIN_GAIN_DB 8
#define BSSID_LOCK_MAX_FAILS 3

typedef struct {
    uint8_t type;
    uint8_t len;
    uint8_t payload[PROTO_MAX_PAYLOAD];
} outmsg_t;

typedef struct {
    bool used;
    uint32_t seq;
    int64_t last_send_us;
    size_t len;
    uint8_t pkt[PKT_MAX];
} pending_t;

static esp_netif_t *s_netif;
static QueueHandle_t s_out_q;
static volatile bool s_connected;
static int s_sock = -1;
static struct sockaddr_in s_server;
static uint32_t s_session;
static uint32_t s_seq;
static pending_t s_pending[PENDING_MAX];
static uint32_t s_server_session;
static uint32_t s_server_seq;
static bool s_server_seen;
static uint16_t s_rtt_ms, s_rtt_max_ms;
static int s_reconnect_fails;
static bool s_bssid_locked;
static volatile bool s_send_hello;

bool net_connected(void)
{
    return s_connected;
}

// ---- WLAN ---------------------------------------------------------------

static void apply_static_ip(void)
{
    if (strlen(CONFIG_LT_STATIC_IP) == 0) {
        return;
    }
    esp_netif_dhcpc_stop(s_netif);
    esp_netif_ip_info_t ip = {0};
    ip.ip.addr = ipaddr_addr(CONFIG_LT_STATIC_IP);
    ip.netmask.addr = ipaddr_addr(CONFIG_LT_STATIC_NETMASK);
    ip.gw.addr = ipaddr_addr(CONFIG_LT_STATIC_GW);
    ESP_ERROR_CHECK(esp_netif_set_ip_info(s_netif, &ip));
}

static void unlock_bssid(void)
{
    wifi_config_t cfg;
    esp_wifi_get_config(WIFI_IF_STA, &cfg);
    cfg.sta.bssid_set = false;
    cfg.sta.channel = 0;
    esp_wifi_set_config(WIFI_IF_STA, &cfg);
    s_bssid_locked = false;
}

static void on_wifi(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        s_connected = false;
        if (s_bssid_locked && ++s_reconnect_fails >= BSSID_LOCK_MAX_FAILS) {
            unlock_bssid();  // roaming target gone, fall back to any AP
        }
        esp_wifi_connect();
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *ev = data;
        ESP_LOGI(TAG, "connected, IP " IPSTR, IP2STR(&ev->ip_info.ip));
        s_reconnect_fails = 0;
        s_connected = true;
        s_send_hello = true;
    }
}

static esp_err_t wifi_init(void)
{
    ESP_RETURN_ON_ERROR(esp_netif_init(), TAG, "netif");
    esp_err_t err = esp_event_loop_create_default();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        return err;
    }
    s_netif = esp_netif_create_default_wifi_sta();
    apply_static_ip();

    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    ESP_RETURN_ON_ERROR(esp_wifi_init(&init), TAG, "wifi init");
    esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, on_wifi, NULL);
    esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, on_wifi, NULL);

    wifi_config_t cfg = {
        .sta = {
            .scan_method = WIFI_ALL_CHANNEL_SCAN,
            .sort_method = WIFI_CONNECT_AP_BY_SIGNAL,
            .threshold.rssi = -90,
        },
    };
    strlcpy((char *)cfg.sta.ssid, CONFIG_LT_WIFI_SSID, sizeof(cfg.sta.ssid));
    strlcpy((char *)cfg.sta.password, CONFIG_LT_WIFI_PASSWORD, sizeof(cfg.sta.password));
    cfg.sta.threshold.authmode =
        strlen(CONFIG_LT_WIFI_PASSWORD) ? WIFI_AUTH_WPA2_PSK : WIFI_AUTH_OPEN;

    ESP_RETURN_ON_ERROR(esp_wifi_set_mode(WIFI_MODE_STA), TAG, "mode");
    ESP_RETURN_ON_ERROR(esp_wifi_set_config(WIFI_IF_STA, &cfg), TAG, "config");
    ESP_RETURN_ON_ERROR(esp_wifi_start(), TAG, "start");
    // latency over battery: no modem sleep
    return esp_wifi_set_ps(WIFI_PS_NONE);
}

// Own roaming: below the threshold, scan for the same SSID and move to a
// clearly stronger AP. No scans while the signal is fine.
static void roam_check(int64_t now)
{
    static int64_t last_scan_us = -ROAM_SCAN_HOLDOFF_US;
    wifi_ap_record_t cur;
    if (!s_connected || esp_wifi_sta_get_ap_info(&cur) != ESP_OK) {
        return;
    }
    if (cur.rssi >= CONFIG_LT_ROAM_RSSI || now - last_scan_us < ROAM_SCAN_HOLDOFF_US) {
        return;
    }
    last_scan_us = now;

    wifi_scan_config_t scan = {
        .ssid = (uint8_t *)CONFIG_LT_WIFI_SSID,
        .scan_type = WIFI_SCAN_TYPE_ACTIVE,
        .scan_time.active = {.min = 20, .max = 40},
    };
    if (esp_wifi_scan_start(&scan, true) != ESP_OK) {
        return;
    }
    uint16_t n = 16;
    wifi_ap_record_t recs[16];
    esp_wifi_scan_get_ap_records(&n, recs);

    const wifi_ap_record_t *best = NULL;
    for (int i = 0; i < n; i++) {
        if (memcmp(recs[i].bssid, cur.bssid, 6) != 0 && (!best || recs[i].rssi > best->rssi)) {
            best = &recs[i];
        }
    }
    if (!best || best->rssi < cur.rssi + ROAM_MIN_GAIN_DB) {
        return;
    }
    ESP_LOGI(TAG, "roaming %d dBm -> " MACSTR " ch %d %d dBm", cur.rssi, MAC2STR(best->bssid),
             best->primary, best->rssi);
    wifi_config_t cfg;
    esp_wifi_get_config(WIFI_IF_STA, &cfg);
    memcpy(cfg.sta.bssid, best->bssid, 6);
    cfg.sta.bssid_set = true;
    cfg.sta.channel = best->primary;
    esp_wifi_set_config(WIFI_IF_STA, &cfg);
    s_bssid_locked = true;
    s_reconnect_fails = 0;
    esp_wifi_disconnect();  // the disconnect handler reconnects to the new AP
}

// ---- UDP ----------------------------------------------------------------

static size_t build(uint8_t *buf, uint8_t type, const void *payload, uint8_t len)
{
    game_state_t g;
    game_snapshot(&g);
    pkt_hdr_t h = {
        .type = type,
        .team = g.team,
        .player = g.player,
        .session = s_session,
        .seq = ++s_seq,
    };
    return proto_build(buf, &h, payload, len);
}

static void send_raw(const uint8_t *buf, size_t len)
{
    if (s_connected) {
        sendto(s_sock, buf, len, 0, (struct sockaddr *)&s_server, sizeof(s_server));
    }
}

static void send_now(uint8_t type, const void *payload, uint8_t len)
{
    uint8_t buf[PKT_MAX];
    send_raw(buf, build(buf, type, payload, len));
}

static void send_reliable(const outmsg_t *m, int64_t now)
{
    pending_t *slot = NULL;
    for (int i = 0; i < PENDING_MAX && !slot; i++) {
        if (!s_pending[i].used) {
            slot = &s_pending[i];
        }
    }
    if (!slot) {  // buffer full: drop the oldest
        slot = &s_pending[0];
        for (int i = 1; i < PENDING_MAX; i++) {
            if (s_pending[i].seq < slot->seq) {
                slot = &s_pending[i];
            }
        }
        ESP_LOGW(TAG, "resend buffer full, dropping seq %lu", (unsigned long)slot->seq);
    }
    slot->used = true;
    slot->len = build(slot->pkt, m->type, m->payload, m->len);
    memcpy(&slot->seq, slot->pkt + offsetof(pkt_hdr_t, seq), sizeof(slot->seq));
    slot->last_send_us = now;
    send_raw(slot->pkt, slot->len);  // two copies right away
    send_raw(slot->pkt, slot->len);
}

static uint32_t pending_count(void)
{
    uint32_t n = 0;
    for (int i = 0; i < PENDING_MAX; i++) {
        n += s_pending[i].used;
    }
    return n;
}

static void resend_pending(int64_t now)
{
    if (!s_connected) {
        return;
    }
    for (int i = 0; i < PENDING_MAX; i++) {
        pending_t *p = &s_pending[i];
        if (p->used && now - p->last_send_us >= RESEND_US) {
            p->last_send_us = now;
            send_raw(p->pkt, p->len);
        }
    }
}

static void send_status(void)
{
    game_state_t g;
    game_snapshot(&g);
    pl_status_t st = {
        .hp = g.hp,
        .ammo = g.ammo,
        .magazines = g.magazines,
        .alive = g.alive,
        .running = g.running,
        .battery_mv = battery_mv(),
        .charging = battery_charging(),
        .rtt_ms = s_rtt_ms,
        .rtt_max_ms = s_rtt_max_ms,
        .shots = g.shots,
        .hits_taken = g.hits_taken,
        .pending = pending_count(),
    };
    wifi_ap_record_t ap;
    if (esp_wifi_sta_get_ap_info(&ap) == ESP_OK) {
        st.rssi = ap.rssi;
        memcpy(st.bssid, ap.bssid, 6);
    }
    s_rtt_max_ms = 0;
    send_now(PKT_STATUS, &st, sizeof(st));
}

static void handle_rx(const uint8_t *buf, size_t n, int64_t now)
{
    const pkt_hdr_t *h;
    const uint8_t *pl;
    if (!proto_verify(buf, n, &h, &pl)) {
        ESP_LOGD(TAG, "dropped invalid packet (%u bytes)", (unsigned)n);
        return;
    }
    game_state_t g;
    game_snapshot(&g);
    if (h->player != PROTO_PLAYER_ALL && h->player != g.player) {
        return;
    }
    // replay protection; a new server session (server restart) resets it
    if (s_server_seen && h->session == s_server_session && h->seq <= s_server_seq) {
        return;
    }
    s_server_seen = true;
    s_server_session = h->session;
    s_server_seq = h->seq;

    event_t ev = {.time_us = now};
    switch (h->type) {
    case PKT_ACK:
        if (h->len == sizeof(pl_ack_t)) {
            const pl_ack_t *a = (const pl_ack_t *)pl;
            for (int i = 0; i < PENDING_MAX; i++) {
                if (s_pending[i].used && a->session == s_session && s_pending[i].seq == a->seq) {
                    s_pending[i].used = false;
                }
            }
        }
        break;
    case PKT_PONG:
        if (h->len == sizeof(pl_ping_t)) {
            pl_ping_t p;
            memcpy(&p, pl, sizeof(p));
            uint32_t rtt = (now - (int64_t)p.t_us) / 1000;
            s_rtt_ms = rtt > 0xffff ? 0xffff : rtt;
            if (s_rtt_ms > s_rtt_max_ms) {
                s_rtt_max_ms = s_rtt_ms;
            }
            ESP_LOGD(TAG, "RTT %u ms", s_rtt_ms);
        }
        break;
    case PKT_GAME_START:
        if (h->len == sizeof(pl_game_start_t)) {
            const pl_game_start_t *c = (const pl_game_start_t *)pl;
            ev.type = EV_NET_START;
            ev.config = (game_config_t){c->max_hp, c->damage, c->magazine, c->magazines,
                                        c->friendly_fire, c->respawn_s};
            game_post(&ev);
        }
        break;
    case PKT_GAME_STOP:
        ev.type = EV_NET_STOP;
        game_post(&ev);
        break;
    case PKT_RESPAWN:
        ev.type = EV_NET_RESPAWN;
        game_post(&ev);
        break;
    case PKT_SET_IDENTITY:
        if (h->len == sizeof(pl_identity_t)) {
            const pl_identity_t *id = (const pl_identity_t *)pl;
            ev.type = EV_NET_IDENTITY;
            ev.identity.team = id->team;
            ev.identity.player = id->player;
            game_post(&ev);
        }
        break;
    default:
        break;
    }
}

static void net_task(void *arg)
{
    int64_t last_status = 0, last_ping = 0, last_roam = 0;
    uint8_t buf[256];
    while (true) {
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(s_sock, &fds);
        struct timeval tv = {.tv_sec = 0, .tv_usec = 20000};
        if (select(s_sock + 1, &fds, NULL, NULL, &tv) > 0) {
            int n = recv(s_sock, buf, sizeof(buf), 0);
            if (n > 0) {
                handle_rx(buf, n, esp_timer_get_time());
            }
        }

        int64_t now = esp_timer_get_time();
        outmsg_t m;
        while (xQueueReceive(s_out_q, &m, 0) == pdTRUE) {
            send_reliable(&m, now);
        }
        if (s_send_hello) {
            s_send_hello = false;
            pl_hello_t hello = {0};
            strlcpy(hello.version, esp_app_get_description()->version, sizeof(hello.version));
            send_now(PKT_HELLO, &hello, sizeof(hello));
        }
        resend_pending(now);
        if (s_connected && now - last_ping >= PING_US) {
            last_ping = now;
            pl_ping_t p = {.t_us = now};
            send_now(PKT_PING, &p, sizeof(p));
        }
        if (s_connected && now - last_status >= STATUS_US) {
            last_status = now;
            send_status();
        }
        if (now - last_roam >= CONFIG_LT_ROAM_CHECK_MS * 1000LL) {
            last_roam = now;
            roam_check(now);
        }
    }
}

static void queue_msg(uint8_t type, const void *payload, uint8_t len)
{
    outmsg_t m = {.type = type, .len = len};
    memcpy(m.payload, payload, len);
    if (s_out_q) {
        xQueueSend(s_out_q, &m, 0);
    }
}

void net_report_hit(uint8_t shooter_team, uint8_t shooter_player, uint8_t sensor,
                    uint16_t hp_after)
{
    pl_hit_t p = {
        .shooter_team = shooter_team,
        .shooter_player = shooter_player,
        .sensor = sensor + 1,
        .hp_after = hp_after,
        .time_ms = esp_timer_get_time() / 1000,
    };
    queue_msg(PKT_HIT, &p, sizeof(p));
}

void net_report_death(uint8_t killer_team, uint8_t killer_player)
{
    pl_death_t p = {
        .killer_team = killer_team,
        .killer_player = killer_player,
        .time_ms = esp_timer_get_time() / 1000,
    };
    queue_msg(PKT_DEATH, &p, sizeof(p));
}

esp_err_t net_start(void)
{
    s_session = esp_random();
    s_out_q = xQueueCreate(16, sizeof(outmsg_t));
    ESP_RETURN_ON_FALSE(s_out_q, ESP_ERR_NO_MEM, TAG, "queue");
    ESP_RETURN_ON_ERROR(proto_init(CONFIG_LT_HMAC_KEY), TAG, "crypto");
    ESP_RETURN_ON_ERROR(wifi_init(), TAG, "wifi");

    s_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    ESP_RETURN_ON_FALSE(s_sock >= 0, ESP_FAIL, TAG, "socket");
    struct sockaddr_in local = {
        .sin_family = AF_INET,
        .sin_port = htons(CONFIG_LT_LOCAL_PORT),
        .sin_addr.s_addr = htonl(INADDR_ANY),
    };
    ESP_RETURN_ON_FALSE(bind(s_sock, (struct sockaddr *)&local, sizeof(local)) == 0, ESP_FAIL,
                        TAG, "bind");
    s_server = (struct sockaddr_in){
        .sin_family = AF_INET,
        .sin_port = htons(CONFIG_LT_SERVER_PORT),
        .sin_addr.s_addr = inet_addr(CONFIG_LT_SERVER_IP),
    };

    BaseType_t ok = xTaskCreatePinnedToCore(net_task, "net", 6144, NULL, 6, NULL, 0);
    return ok == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}
