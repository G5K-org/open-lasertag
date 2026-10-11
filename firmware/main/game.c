// Game logic, runs locally on core 1: HP, ammo, reload, hits, death and
// respawn. Local feedback first, then the network report.
#include "game.h"

#include <string.h>
#include "audio.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "events.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "haptics.h"
#include "input.h"
#include "ir_tx.h"
#include "leds.h"
#include "net.h"
#include "nvs.h"
#include "sdkconfig.h"

#define TAG "game"
#define TICK_MS 10
#define UNLIMITED 0xff
// Frames closer than this come from the same transmission (seen by several TSOPs)
#define SAME_FRAME_US 30000

#if CONFIG_LT_FRIENDLY_FIRE
#define FRIENDLY_FIRE 1
#else
#define FRIENDLY_FIRE 0
#endif
#if CONFIG_LT_STANDALONE
#define STANDALONE true
#else
#define STANDALONE false
#endif

static QueueHandle_t s_q;
static SemaphoreHandle_t s_lock;
static game_state_t s_state;
static game_config_t s_cfg;
static int64_t s_last_shot_us;

// last valid frame, waiting for its confirmation frame
static struct {
    bool valid;
    uint8_t team, player;
    int64_t time_us;
} s_pending_hit;

void game_post(const event_t *ev)
{
    if (s_q && xQueueSend(s_q, ev, 0) != pdTRUE) {
        ESP_LOGW(TAG, "event queue full, event %d dropped", ev->type);
    }
}

void game_snapshot(game_state_t *out)
{
    xSemaphoreTake(s_lock, portMAX_DELAY);
    *out = s_state;
    xSemaphoreGive(s_lock);
}

static void lock(void)
{
    xSemaphoreTake(s_lock, portMAX_DELAY);
}

static void unlock(void)
{
    xSemaphoreGive(s_lock);
}

static void save_identity(uint8_t team, uint8_t player)
{
    nvs_handle_t h;
    if (nvs_open("lasertag", NVS_READWRITE, &h) == ESP_OK) {
        nvs_set_u8(h, "team", team);
        nvs_set_u8(h, "player", player);
        nvs_commit(h);
        nvs_close(h);
    }
}

static void reset_player(int64_t now)
{
    s_state.alive = true;
    s_state.max_hp = s_cfg.max_hp;
    s_state.hp = s_cfg.max_hp;
    s_state.magazine = s_cfg.magazine;
    s_state.ammo = s_cfg.magazine;
    s_state.magazines = s_cfg.magazines ? s_cfg.magazines : UNLIMITED;
    s_state.reloading = false;
    s_state.last_hit_us = now;  // short grace period after (re)spawn
    s_pending_hit.valid = false;
}

static void fire(int64_t now)
{
    if (!s_state.running || !s_state.alive || s_state.reloading) {
        return;
    }
    if (now - s_last_shot_us < CONFIG_LT_FIRE_INTERVAL_MS * 1000LL) {
        return;
    }
    if (s_state.ammo == 0) {
        audio_play(SND_EMPTY);
        return;
    }
    if (ir_tx_shot(s_state.team, s_state.player) != ESP_OK) {
        return;
    }
    s_last_shot_us = now;
    s_state.ammo--;
    s_state.shots++;
    leds_flash_muzzle();
    haptics_play(HAPTIC_RECOIL);
    audio_play(SND_SHOT);
}

static void start_reload(int64_t now)
{
    if (!s_state.running || !s_state.alive || s_state.reloading ||
        s_state.ammo == s_state.magazine || s_state.magazines == 0) {
        return;
    }
    s_state.reloading = true;
    s_state.reload_end_us = now + CONFIG_LT_RELOAD_MS * 1000LL;
    audio_play(SND_RELOAD);
}

static void die(uint8_t team, uint8_t player, int64_t now)
{
    s_state.alive = false;
    s_state.hp = 0;
    s_state.reloading = false;
    s_state.death_us = now;
    haptics_play(HAPTIC_DEATH);
    audio_play(SND_DEATH);
    ESP_LOGI(TAG, "killed by team %u player %u", team, player);
}

static void respawn(int64_t now)
{
    reset_player(now);
    haptics_play(HAPTIC_RESPAWN);
    audio_play(SND_RESPAWN);
    ESP_LOGI(TAG, "respawn");
}

// Hit rules: other team (unless friendly fire), not our own id, n valid
// frames within the window, invulnerable for a while after a hit.
static void ir_frame(const event_t *ev)
{
    uint8_t team = ev->ir.team, player = ev->ir.player;
    int64_t t = ev->time_us;

    if (!s_state.running || !s_state.alive) {
        return;
    }
    if (player == s_state.player) {
        return;
    }
    if (team == s_state.team && !s_cfg.friendly_fire) {
        return;
    }
    if (t - s_state.last_hit_us < CONFIG_LT_INVULN_MS * 1000LL) {
        return;
    }

#if CONFIG_LT_HIT_CONFIRM_FRAMES > 1
    bool same_shooter = s_pending_hit.valid && s_pending_hit.team == team &&
                        s_pending_hit.player == player;
    int64_t dt = t - s_pending_hit.time_us;
    if (same_shooter && dt < SAME_FRAME_US) {
        return;  // same frame on another sensor
    }
    if (!same_shooter || dt > CONFIG_LT_HIT_WINDOW_MS * 1000LL) {
        s_pending_hit.valid = true;
        s_pending_hit.team = team;
        s_pending_hit.player = player;
        s_pending_hit.time_us = t;
        return;
    }
    s_pending_hit.valid = false;
#endif

    s_state.last_hit_us = t;
    s_state.hits_taken++;
    s_state.hp = s_state.hp > s_cfg.damage ? s_state.hp - s_cfg.damage : 0;
    ESP_LOGI(TAG, "hit by team %u player %u on TSOP%u, HP %u", team, player, ev->ir.sensor + 1,
             s_state.hp);

    // local feedback first
    leds_flash_hit();
    if (s_state.hp == 0) {
        die(team, player, t);
    } else {
        haptics_play(HAPTIC_HIT);
        audio_play(SND_HIT);
    }
    net_hit_confirm(team, player, s_state.hp == 0);
    net_report_hit(team, player, ev->ir.sensor, s_state.hp);
    if (s_state.hp == 0) {
        net_report_death(team, player);
    }
}

static void handle(const event_t *ev)
{
    switch (ev->type) {
    case EV_TRIGGER_DOWN:
        fire(ev->time_us);
        break;
    case EV_TRIGGER_UP:
        break;
    case EV_RELOAD_DOWN:
        start_reload(ev->time_us);
        break;
    case EV_IR_FRAME:
        ir_frame(ev);
        break;
    case EV_HIT_CONFIRM:
        // feedback for the shooter: our shot landed
        if (s_state.running) {
            s_state.hits_given++;
            if (ev->confirm.killed) {
                s_state.kills++;
            }
            leds_flash_confirm(ev->confirm.killed);
            audio_play(ev->confirm.killed ? SND_KILL_CONFIRM : SND_HIT_CONFIRM);
            ESP_LOGI(TAG, "%s team %u player %u", ev->confirm.killed ? "killed" : "hit",
                     ev->confirm.victim_team, ev->confirm.victim_player);
        }
        break;
    case EV_NET_START:
        s_cfg = ev->config;
        if (s_cfg.max_hp == 0 || s_cfg.magazine == 0) {
            ESP_LOGW(TAG, "invalid game config ignored");
            break;
        }
        s_state.running = true;
        reset_player(ev->time_us);
        audio_play(SND_START);
        ESP_LOGI(TAG, "game started: HP %u, damage %u, magazine %u", s_cfg.max_hp, s_cfg.damage,
                 s_cfg.magazine);
        break;
    case EV_NET_STOP:
        s_state.running = false;
        s_state.reloading = false;
        ESP_LOGI(TAG, "game stopped");
        break;
    case EV_NET_RESPAWN:
        if (s_state.running && !s_state.alive) {
            respawn(ev->time_us);
        }
        break;
    case EV_NET_IDENTITY:
        if (ev->identity.player == 0 || ev->identity.player == 0xff) {
            break;
        }
        s_state.team = ev->identity.team;
        s_state.player = ev->identity.player;
        save_identity(s_state.team, s_state.player);
        ESP_LOGI(TAG, "identity: team %u player %u", s_state.team, s_state.player);
        break;
    }
}

static void tick(int64_t now)
{
    if (s_state.reloading && now >= s_state.reload_end_us) {
        s_state.reloading = false;
        s_state.ammo = s_state.magazine;
        if (s_state.magazines != UNLIMITED) {
            s_state.magazines--;
        }
    }
    if (s_state.running && !s_state.alive && s_cfg.respawn_s &&
        now - s_state.death_us >= s_cfg.respawn_s * 1000000LL) {
        respawn(now);
    }
#if CONFIG_LT_FULL_AUTO
    if (input_trigger_held()) {
        fire(now);
    }
#endif
}

static void game_task(void *arg)
{
    while (true) {
        event_t ev;
        bool got = xQueueReceive(s_q, &ev, pdMS_TO_TICKS(TICK_MS)) == pdTRUE;
        lock();
        if (got) {
            handle(&ev);
        }
        tick(esp_timer_get_time());
        unlock();
    }
}

esp_err_t game_start(uint8_t team, uint8_t player)
{
    s_lock = xSemaphoreCreateMutex();
    s_q = xQueueCreate(32, sizeof(event_t));
    if (!s_lock || !s_q) {
        return ESP_ERR_NO_MEM;
    }
    s_cfg = (game_config_t){
        .max_hp = CONFIG_LT_MAX_HP,
        .damage = CONFIG_LT_DAMAGE,
        .magazine = CONFIG_LT_MAGAZINE,
        .magazines = CONFIG_LT_MAGAZINES,
        .friendly_fire = FRIENDLY_FIRE,
        .respawn_s = CONFIG_LT_RESPAWN_S,
    };
    s_state.team = team;
    s_state.player = player;
    s_state.running = STANDALONE;
    s_last_shot_us = -CONFIG_LT_FIRE_INTERVAL_MS * 1000LL;
    reset_player(esp_timer_get_time());

    BaseType_t ok = xTaskCreatePinnedToCore(game_task, "game", 4096, NULL, 15, NULL, 1);
    return ok == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}
