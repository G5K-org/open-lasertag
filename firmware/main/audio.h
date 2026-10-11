#pragma once

#include "esp_err.h"

typedef enum {
    SND_SHOT,
    SND_EMPTY,
    SND_RELOAD,
    SND_HIT,
    SND_DEATH,
    SND_RESPAWN,
    SND_START,
    SND_HIT_CONFIRM,   // our shot landed
    SND_KILL_CONFIRM,  // our shot killed
} sound_t;

// MAX98357A over I2S, sounds are synthesised (no sample files).
esp_err_t audio_start(void);
void audio_play(sound_t s);
