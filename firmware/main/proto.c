#include "proto.h"

#include <string.h>
#include "psa/crypto.h"

static psa_key_id_t s_key;

esp_err_t proto_init(const char *key)
{
    if (psa_crypto_init() != PSA_SUCCESS) {
        return ESP_FAIL;
    }
    psa_key_attributes_t attr = PSA_KEY_ATTRIBUTES_INIT;
    psa_set_key_usage_flags(&attr, PSA_KEY_USAGE_SIGN_MESSAGE);
    psa_set_key_algorithm(&attr, PSA_ALG_HMAC(PSA_ALG_SHA_256));
    psa_set_key_type(&attr, PSA_KEY_TYPE_HMAC);
    psa_status_t st = psa_import_key(&attr, (const uint8_t *)key, strlen(key), &s_key);
    psa_reset_key_attributes(&attr);
    return st == PSA_SUCCESS ? ESP_OK : ESP_FAIL;
}

static bool mac(const uint8_t *data, size_t n, uint8_t out[32])
{
    size_t len;
    return psa_mac_compute(s_key, PSA_ALG_HMAC(PSA_ALG_SHA_256), data, n, out, 32, &len) ==
               PSA_SUCCESS &&
           len == 32;
}

size_t proto_build(uint8_t *buf, const pkt_hdr_t *hdr, const void *payload, uint16_t len)
{
    pkt_hdr_t h = *hdr;
    h.magic[0] = PROTO_MAGIC0;
    h.magic[1] = PROTO_MAGIC1;
    h.version = PROTO_VERSION;
    h.len = len;
    memcpy(buf, &h, sizeof(h));
    if (len) {
        memcpy(buf + sizeof(h), payload, len);
    }
    size_t n = sizeof(h) + len;
    uint8_t m[32] = {0};
    mac(buf, n, m);
    memcpy(buf + n, m, PROTO_MAC_LEN);
    return n + PROTO_MAC_LEN;
}

bool proto_verify(const uint8_t *buf, size_t n, const pkt_hdr_t **hdr, const uint8_t **payload)
{
    if (n < sizeof(pkt_hdr_t) + PROTO_MAC_LEN) {
        return false;
    }
    const pkt_hdr_t *h = (const pkt_hdr_t *)buf;
    if (h->magic[0] != PROTO_MAGIC0 || h->magic[1] != PROTO_MAGIC1 ||
        h->version != PROTO_VERSION || h->len > PROTO_MAX_PAYLOAD ||
        n != sizeof(pkt_hdr_t) + h->len + PROTO_MAC_LEN) {
        return false;
    }
    uint8_t m[32];
    if (!mac(buf, n - PROTO_MAC_LEN, m)) {
        return false;
    }
    // constant time compare
    uint8_t diff = 0;
    for (int i = 0; i < PROTO_MAC_LEN; i++) {
        diff |= m[i] ^ buf[n - PROTO_MAC_LEN + i];
    }
    if (diff) {
        return false;
    }
    *hdr = h;
    *payload = buf + sizeof(pkt_hdr_t);
    return true;
}
