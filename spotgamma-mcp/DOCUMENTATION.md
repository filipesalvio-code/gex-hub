# spotgamma-mcp — Tool Documentation

MCP server for the **SpotGamma Dashboard API** (`https://api.spotgamma.com`), generated from
`spotgamma-api-endpoints.md`. **45 tools** across 8 groups.

Every example below was executed live against the production API on **2026-07-25**
with SPX-oriented arguments (Alpha subscriber token). Outputs are trimmed for
readability; full byte counts are noted.

## Calling a tool

MCP tools are invoked by name with a JSON arguments object:

```json
{ "name": "spotgamma_key_levels", "arguments": { "include_gamma_curve": true } }
```

## Authentication

| Layer | Value |
|---|---|
| Static app token | Sent automatically on every request (hardcoded in the SpotGamma web bundle) |
| User token | `SPOTGAMMA_SG_TOKEN` env var — value of `localStorage["sgToken"]` after login; **automatically attached to every request when set** (mirrors the web app) |
| Free tier | Tools with `use_free` call the unpaid `free_` variant — no token needed |
| Expiry | sgToken JWT lasts ~3 days; re-copy from the browser when gated tools start 403-ing |

**Auth matrix (verified 2026-07-25):**

- **Public, no token needed:** key_levels, home_all_data, combo_levels, tilt, risk_reversal, prices, quote, series, futures, most_recent_market_open, treasury_rates, dividends, zero_dte, equity_put_call_ratio, trending, economic_calendar, compass, content_for_category, synth_oi_last_update, synth_oi_eh_symbols, concentration — plus every `use_free` variant.
- **Gated (403 without token):** equities_gex, equities_by_syms, historical_gex, latest_greeks, daily_greeks, skew, rr, iv_stats, oi, oi_syms, synth_oi_equities, synth_oi_chart_data, synth_oi_historical, synth_oi_equity_scanners, running_hiro, hiro_history, latest_hiro, earnings, equity_scanners, compass_hist, founders_notes, `/v1/me/*` via raw_get.
- **Stale (404 even with token):** oi_intraday (all kinds), correlation_regime.

**Conventions:** dates are `YYYY-MM-DD`; responses are JSON truncated at ~200 KB with a notice;
`params` arguments pass straight through to the query string.

---
## Contents

1. [GEX / Gamma (core)](#1-gex-gamma-core)
2. [Greeks / Skew / IV](#2-greeks-skew-iv)
3. [Open Interest (incl. synthetic OI)](#3-open-interest-incl-synthetic-oi)
4. [HIRO (order flow)](#4-hiro-order-flow)
5. [Market data](#5-market-data)
6. [Calendars](#6-calendars)
7. [Scanners / Compass](#7-scanners-compass)
8. [Content / misc + escape hatch](#8-content-misc-escape-hatch)

---

## 1. GEX / Gamma (core)

Gamma-exposure data: SPX key levels, the full equity GEX table, per-symbol profiles, and historical series.

### `spotgamma_key_levels`

**Endpoint:** `GET /home/keyLevels`

The dashboard's headline SPX gamma map. Returns the call wall, put wall, zero-gamma strike (`zero_g_strike`), max-gamma strike, gamma notional, UPX, `levels_with_pct` (strike + strength score), the strike list, greeks (theta/vega/delta), and — when `include_gamma_curve` is set — the full per-strike gamma curve (`current_list`). This is the tool to reach for first when asked “where are the SPX gamma levels?”.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `include_gamma_curve` | boolean | no | Include the full gamma curve (`current_list`). Default false. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_key_levels",
  "arguments": {
    "include_gamma_curve": true
  }
}
```


**Example output (live, 2026-07-25)**

```json
{
  "data": [
    {
      "sym": "SPX",
      "trade_date": "2026-07-23T00:00:00.000Z",
… [truncated — full response 17,204 chars]
```


> **Note:** Public endpoint — works without a token. SPX-only by design.

### `spotgamma_equities_gex`

**Endpoint:** `GET /v4/equities (free: /v1/free_equities)`

Full equity GEX table — one row per symbol with `upx` (expected move / “UPX”), `callsum`, `putsum`, `minfs`, earnings timestamp, next-expiry gamma split (`next_exp_call_gamma` / `next_exp_put_gamma`), ATM gamma/delta per side (`atmgc/atmgp/atmdc/atmdp`), put/call volume (`pv/cv`) and more. Large payload (~115 KB even filtered); use `syms_filter` to keep only the rows you need.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `use_free` | boolean | no | Use the unpaid-tier `/v1/free_equities` (works without a token, fewer fields). |
| `syms_filter` | string[] | no | Client-side row filter, e.g. `["SPX"]`. Case-insensitive. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_equities_gex",
  "arguments": {
    "syms_filter": [
      "SPX"
    ]
  }
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "trade_date": "2026-07-24T00:00:00.000Z",
    "quote_date": "2026-07-24T00:00:00.000Z",
    "sym": "SPX",
    "name": "S&P 500",
    "upx": 7411.98,
    "callsum": 9342009,
    "putsum": 12532786,
    "minfs": 400,
    "earnings_utc": null,
    "keyd": 6000,
    "largeCoi": 7000,
    "largePoi": 7000,
    "next_exp_call_gamma": 121416636,
    "next_exp_put_gamma": 179153473,
    "next_exp_g": 0.0533,
    "next_exp_d": 0.0154,
    "max_exp_g_date": "2026-09-18T20:00:00.000Z",
    "max_exp_d_date": "2026-12-18T21:00:00.000Z",
    "atmgc": -2625433287,
    "atmgp": -3008901780,
    "atmdc": -2831933695267,
    "atmdp": 1838714392139,
    "pv": 917040,
    "cv": 644612,
    "d95ne": 0.1434,
    "d25ne": 0.0922,
    "d95": 0.2767,
    "d25": 0.1225,
    "putctrl": 20000,
    "activity_factor": 99.99,
    "position_factor": 76.02,
    "date": null,
    "total_volume": null,
… [truncated — full response 115,364 chars]
```


> **Note:** Gated (403 without token). Free variant verified working without a token.

### `spotgamma_equities_by_syms`

**Endpoint:** `GET /v3/equitiesBySyms`

Per-symbol GEX profile for a specific trade date — same field family as the equities table but date-addressed. The app requests the previous trading day.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `syms` | string | yes | Symbol, e.g. `SPX`. |
| `date` | YYYY-MM-DD | no | Profile date; API default when omitted. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_equities_by_syms",
  "arguments": {
    "syms": "SPX",
    "date": "2026-07-24"
  }
}
```


**Example output (live, 2026-07-25)**

```json
{
  "SPX": {
    "trade_date": "2026-07-24T00:00:00.000Z",
    "quote_date": "2026-07-24T00:00:00.000Z",
    "sym": "SPX",
    "name": "S&P 500",
    "upx": 7411.98,
    "callsum": 9342009,
    "putsum": 12532786,
    "minfs": 400,
    "earnings_utc": null,
    "keyd": 6000,
    "largeCoi": 7000,
    "largePoi": 7000,
    "next_exp_call_gamma": 121416636,
    "next_exp_put_gamma": 179153473,
    "next_exp_g": 0.0533,
    "next_exp_d": 0.0154,
    "max_exp_g_date": "2026-09-18T20:00:00.000Z",
    "max_exp_d_date": "2026-12-18T21:00:00.000Z",
    "atmgc": -2625433287,
    "atmgp": -3008901780,
    "atmdc": -2831933695267,
    "atmdp": 1838714392139,
    "pv": 917040,
    "cv": 644612,
    "d95ne": 0.1434,
    "d25ne": 0.0922,
    "d95": 0.2767,
    "d25": 0.1225,
    "putctrl": 20000,
    "activity_factor": 99.99,
    "position_factor": 76.02,
    "date": null,
    "total_volume": null,
… [truncated — full response 115,214 chars]
```


> **Note:** Gated (403 without token; no free variant).

### `spotgamma_historical_gex`

**Endpoint:** `GET /v4/historical (free: /v1/free_historical)`

Historical GEX time series. Very large payload (hits the ~200 KB server cap) — pass narrowing params via `params` (e.g. symbol/date filters as accepted by the API).

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `use_free` | boolean | no | Use `/v1/free_historical`. |
| `params` | object | no | Extra query params passed through as-is. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_historical_gex",
  "arguments": {
    "params": {
      "sym": "SPX"
    }
  }
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "trade_date": "2026-07-24T00:00:00.000Z",
    "quote_date": "2026-07-24T00:00:00.000Z",
    "sym": "SPX",
    "upx": 7411.98,
    "putsum": 12532786,
    "callsum": 9342009,
    "cws": 7600,
    "pws": 7300,
    "keyg": 7000,
    "maxfs": 7465,
    "put_call_ratio": 1.3416,
    "minfs": 400,
    "keyd": 6000,
    "largeCoi": 7000,
    "largePoi": 7000,
    "next_exp_g": 0.0533,
    "next_exp_d": 0.0154,
    "max_exp_g_date": "2026-09-18T20:00:00.000Z",
    "max_exp_d_date": "2026-12-18T21:00:00.000Z",
    "cv": 644612,
    "pv": 917040,
    "volume_ratio": 0.7029,
    "atmgc": -2625433287,
    "atmgp": -3008901780,
    "gamma_ratio": 0.8726,
    "atmdc": -2831933695267,
    "atmdp": 1838714392139,
    "delta_ratio": -1.5402,
    "d95ne": 0.1434,
    "d25ne": 0.0922,
    "d95": 0.2767,
    "d25": 0.1225,
    "ne_skew": -0.23323615,
    "skew": -0.42760027,
… [truncated — full response 200,095 chars]
```


> **Note:** Gated. The example call passed `{"sym":"SPX"}` and still returned a multi-symbol payload — server-side filtering is limited; expect to post-filter.

### `spotgamma_combo_levels`

**Endpoint:** `GET /v2/comboLevels`

Combined gamma levels per symbol — a compact level set (call/put walls, zero-gamma, nearby strikes) used by the app's per-symbol views.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sym` | string | yes | Symbol, e.g. `SPX`. |
| `next_exp` | string\|number\|boolean | no | `nextExp` flag/value. |
| `params` | object | no | Extra query params. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_combo_levels",
  "arguments": {
    "sym": "SPX"
  }
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "trade_date": "2026-07-23T00:00:00.000Z",
    "model": "combo_profile",
    "sym": "SPX",
… [truncated — full response 3,732 chars]
```


> **Note:** Verified public (returned data with no token attached).

### `spotgamma_home_all_data`

**Endpoint:** `GET /home/allData`

Aggregate home payload the dashboard loads for its main view — a bundle of the day's key datasets in one response.

**Parameters**

_No parameters._


**Example call (SPX)**

```json
{
  "name": "spotgamma_home_all_data",
  "arguments": {}
}
```


**Example output (live, 2026-07-25)**

```json
{
  "keyLevels": [
    {
      "sym": "SPX",
      "trade_date": "2026-07-23T00:00:00.000Z",
… [truncated — full response 22,048 chars]
```


> **Note:** Verified public.

## 2. Greeks / Skew / IV

Option greeks snapshots and history, skew, tilt, risk reversal, and IV statistics.

### `spotgamma_latest_greeks`

**Endpoint:** `GET /v2/latest_greeks (free: /v2/free_latest_greeks)`

Latest greeks snapshot for a symbol — the full option-chain greeks grid (per strike/expiry). Very large for SPX (hits the ~200 KB cap); post-filter by strike/expiry client-side.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sym` | string | yes | Symbol. |
| `use_free` | boolean | no | Use the free variant. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_latest_greeks",
  "arguments": {
    "sym": "SPX"
  }
}
```


**Example output (live, 2026-07-25)**

```json
�=����>���@�p���@�'��B�J�@�'��B�J�?�����˿oس*�	��?�܅r������]��?oس*��K�?oس*��K��˿oس*��K��?��e�_������]�@����@�`�j���@�`�j���?�����˿q��O����?�܅r������]��?q��#B�?q��#B��˿q��#B��?��e�_������]�@�����@�2�҇��@�2�҇��?�����˿rKڧ�����?�܅r������]��?rKڧ���?rKڧ����˿rKڧ����?��e�_������]�@� ���@��#y���@��#y���?�����˿s��U���?�܅r������]��?s��Tbe��?s��Tbe���˿s��Tbe���?��e�_������]�@�����@��!��@��!��?�����˿tֱ������?�܅r������]��?tֱ�O~��?tֱ�O~���˿tֱ�O~���?��e�_������]�@�@���@��˞�w�@��˞�w�?�����˿v+Û7����?�܅r������]��?v+Ør�?v+Ør��˿v+Ør��?��e�_������]�@�h���@���v�I+�@���v�I+�?�����˿w��������?�܅r������]��?w���i1�?w���i1��˿w���i1��?��e�_������]�@�0���@�i�"����@�i�"����?�����˿x��������?�܅r������]��?x���N�+�?x���N�+��˿x���N�+��?��e�_������]�@�����@��j�Up�@��j�Up�?�����˿zf�*H��?�܅r������]��?zf�%6̃�?zf�%6̃��˿zf�%6̃��?��e�_������]�@�����@�L�~�]��@�L�~�]��?�����˿{��?����?�܅r������]��?{���<e�?{���<e��˿{���<e��?��
```


> **Note:** Gated; free variant available.

### `spotgamma_daily_greeks`

**Endpoint:** `GET /v2/daily_greeks (free: /v2/free_daily_greeks)`

Daily greeks history for a symbol on a given date — the per-strike greeks series the app charts.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sym` | string | yes | Symbol. |
| `date` | YYYY-MM-DD | yes | Trade date. |
| `mkt_close` | string\|number\|boolean | no | `mkt_close` flag/value. |
| `use_free` | boolean | no | Use the free variant. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_daily_greeks",
  "arguments": {
    "sym": "SPX",
    "date": "2026-07-24"
  }
}
```


**Example output (live, 2026-07-25)**

```json
�=����>���@�p���@�'��B�J�@�'��B�J�?�����˿oس*�	��?�܅r������]��?oس*��K�?oس*��K��˿oس*��K��?��e�_������]�?��CБg�@����@�`�j���@�`�j���?�����˿q��O����?�܅r������]��?q��#B�?q��#B��˿q��#B��?��e�_������]�?�o��N�@�����@�2�҇��@�2�҇��?�����˿rKڧ�����?�܅r������]��?rKڧ���?rKڧ����˿rKڧ����?��e�_������]�?�Q���3�@� ���@��#y���@��#y���?�����˿s��U���?�܅r������]��?s��Tbe��?s��Tbe���˿s��Tbe���?��e�_������]�?��JȵG�@�����@��!��@��!��?�����˿tֱ������?�܅r������]��?tֱ�O~��?tֱ�O~���˿tֱ�O~���?��e�_������]�?𢎉����@�@���@��˞�w�@��˞�w�?�����˿v+Û7����?�܅r������]��?v+Ør�?v+Ør��˿v+Ør��?��e�_������]�?�O��ۨb�@�h���@���v�I+�@���v�I+�?�����˿w��������?�܅r������]��?w���i1�?w���i1��˿w���i1��?��e�_������]�?��?���@�0���@�i�"����@�i�"����?�����˿x��������?�܅r������]��?x���N�+�?x���N�+��˿x���N�+��?��e�_������]�?�a�
… [truncated — full response 200,095 chars]
```


> **Note:** Gated; free variant available.

### `spotgamma_skew`

**Endpoint:** `GET /v2/skew (free: /v2/free_skew)`

Skew dataset powering the app's skew chart. Large payload.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `use_free` | boolean | no | Use the free variant. |
| `params` | object | no | Extra query params. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_skew",
  "arguments": {}
}
```


**Example output (live, 2026-07-25)**

```json
{
  "today": {
    "next": {
      "day": 1784922270058,
      "dte": 3.0107632175925927,
      "exp": 1785182400000,
      "greeks": {
        "3000": [
          [
            4395.5,
            4414.7,
            0.999856271403353,
            1.271355006326439e-61,
            -0.05655439341995,
            3.51335148189883e-58,
            0.609212560333302,
            1784922268000
          ],
          [
            0,
            0.05,
            -2.191915363385297e-59,
            8.62838773842346e-61,
            -2.43594592861396e-56,
            2.40187203211983e-57,
            0.613669160837261,
            1784922245000
          ],
          0.8181042530942146
        ],
        "3200": [
          [
            4195.6,
            4214.3,
            0.999856271403353,
            1.163365968153883e-53,
            -0.0837810635148296,
… [truncated — full response 200,095 chars]
```


> **Note:** Gated; free variant available.

### `spotgamma_tilt`

**Endpoint:** `GET /v1/tilt`

Tilt metric for a symbol — SpotGamma's call/put skew tilt reading. Large per-strike payload for SPX.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sym` | string | yes | Symbol. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_tilt",
  "arguments": {
    "sym": "SPX"
  }
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "trade_date": "2018-01-02T00:00:00.000Z",
    "upx": 2694,
    "delta_tilt": 2.6471,
    "gamma_tilt": 1.4268
  },
  {
    "trade_date": "2018-01-03T00:00:00.000Z",
    "upx": 2713,
    "delta_tilt": 3.3606,
    "gamma_tilt": 1.6662
  },
  {
    "trade_date": "2018-01-04T00:00:00.000Z",
    "upx": 2725,
    "delta_tilt": 3.6616,
    "gamma_tilt": 1.7241
  },
  {
    "trade_date": "2018-01-05T00:00:00.000Z",
    "upx": 2739,
    "delta_tilt": 3.9294,
    "gamma_tilt": 1.7224
  },
  {
    "trade_date": "2018-01-08T00:00:00.000Z",
    "upx": 2748,
    "delta_tilt": 4.254,
    "gamma_tilt": 1.7385
  },
  {
    "trade_date": "2018-01-09T00:00:00.000Z",
    "upx": 2755,
    "delta_tilt": 4.2365,
    "gamma_tilt": 1.6604
  },
  {
    "trade_date": "2018-01-10T00:00:00.000Z",
    "upx": 2747,
    "delta_tilt": 3.6133,
    "gamma_tilt": 1.4732
  },
  {
… [truncated — full response 200,095 chars]
```


> **Note:** Verified public (worked with no token attached).

### `spotgamma_risk_reversal`

**Endpoint:** `GET /v1/optionsRiskReversal`

Options risk-reversal data for a symbol (25-delta style call/put IV spread series).

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sym` | string | yes | Symbol. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_risk_reversal",
  "arguments": {
    "sym": "SPX"
  }
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "trade_date": "2020-04-09T00:00:00.000Z",
    "rr": 0
  },
  {
    "trade_date": "2020-04-13T00:00:00.000Z",
    "rr": -0.15
  },
  {
    "trade_date": "2020-04-14T00:00:00.000Z",
    "rr": -0.13
  },
  {
    "trade_date": "2020-04-15T00:00:00.000Z",
    "rr": -0.14
  },
  {
    "trade_date": "2020-04-16T00:00:00.000Z",
    "rr": -0.15
  },
  {
    "trade_date": "2020-04-17T00:00:00.000Z",
    "rr": -0.14
  },
  {
    "trade_date": "2020-04-20T00:00:00.000Z",
    "rr": -0.16
  },
  {
    "trade_date": "2020-04-21T00:00:00.000Z",
    "rr": -0.16
  },
  {
    "trade_date": "2020-04-22T00:00:00.000Z",
    "rr": -0.16
  },
  {
    "trade_date": "2020-04-23T00:00:00.000Z",
    "rr": -0.15
  },
  {
    "trade_date": "2020-04-24T00:00:00.000Z",
    "rr": -0.12
  },
  {
    "trade_date": "2020-04-27T00:00:00.000Z",
    "rr": -0.12
  },
  {
    "trade_date": "2020-04-28T00:00:00.000Z",
… [truncated — full response 115,794 chars]
```


> **Note:** Verified public.

### `spotgamma_rr`

**Endpoint:** `GET /v1/rr (free: /v1/free_rr)`

Risk-reversal chart series (the RR chart in the dashboard).

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sym` | string | yes | Symbol. |
| `use_free` | boolean | no | Use the free variant. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_rr",
  "arguments": {
    "sym": "SPX"
  }
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "trade_date": "2021-04-01T00:00:00.000Z",
    "rr": null,
    "upx": 4019.87
  },
  {
    "trade_date": "2021-04-05T00:00:00.000Z",
    "rr": null,
    "upx": 4077.91
  },
  {
    "trade_date": "2021-04-06T00:00:00.000Z",
    "rr": null,
    "upx": 4073.94
  },
  {
    "trade_date": "2021-04-07T00:00:00.000Z",
    "rr": null,
    "upx": 4079.95
  },
  {
    "trade_date": "2021-04-08T00:00:00.000Z",
    "rr": null,
    "upx": 4097.17
  },
  {
    "trade_date": "2021-04-09T00:00:00.000Z",
    "rr": null,
    "upx": 4128.8
  },
  {
    "trade_date": "2021-04-12T00:00:00.000Z",
    "rr": null,
    "upx": 4127.99
  },
  {
    "trade_date": "2021-04-13T00:00:00.000Z",
    "rr": null,
    "upx": 4141.59
  },
  {
    "trade_date": "2021-04-14T00:00:00.000Z",
    "rr": null,
    "upx": 4124.66
  },
  {
    "trade_date": "2021-04-15T00:00:00.000Z",
    "rr": null,
    "upx": 4124.66
… [truncated — full response 126,450 chars]
```


> **Note:** Gated; free variant available.

### `spotgamma_iv_stats`

**Endpoint:** `GET /v1/iv_stats (free: /v1/free_iv_stats)`

IV statistics for a symbol — IV percentile/rank style aggregates plus term structure stats. Large payload.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sym` | string | yes | Symbol. |
| `date` | YYYY-MM-DD | no | Optional date. |
| `use_free` | boolean | no | Use the free variant. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_iv_stats",
  "arguments": {
    "sym": "SPX"
  }
}
```


**Example output (live, 2026-07-25)**

```json
��#�W���˿ٙ�������?ôe�0�?�\�<��?�Y��ڻ�?�0V
��?�!���<�?�4�� ���?�3�(k���?��"�F��?��c7��˿�333333��?ē����?����L�?Ɗd(ܗN�?�7�5TiL�?�5�mۤ�?ҳy� r�?�Q��S�?��	�/j�?�����˿���?�*���"�?�c�ئ�~�?�>\p>Y�?��.�ݺX�?���;A`�?�(�/��?�ۄ7�s�?˖Du�u�?��mZS4˿ə�������?��+�PH��?��ةqO��?���(�?���x���?�Q��N��?�^}�dw�?�֔h
w7�?�5��#�`�?����[9�˿���������?�YB�n�?������?���zh��?̜�n����?ѭ�! ���?ԀlV����?�?��`<;�?�b/����?��r�J/r˿���������?ː��!��?�
��ꌕ�?�i�����?�H.��"��?�͇KL�?Ձb�a=�?��dљ0��?є1���?��4�%˿�z�G�{��?̙��>G0�?�aQz��?�0'saN�?�
… [truncated — full response 200,095 chars]
```


> **Note:** Gated; free variant available.

## 3. Open Interest (incl. synthetic OI)

Classical open interest, OI concentration, and SpotGamma's synthetic-OI (Equity Hub) datasets.

### `spotgamma_oi_intraday`

**Endpoint:** `GET /v2/open_interest/intraday_{kind}`

Intraday OI endpoints from the app bundle: `gamma`, `delta`, `stats`, `strike_bars`, `timestamps`. The exact query schema (from the bundle): gamma/delta → `symbol,date,ts,mkt_actor`; stats → `sym,date`; strike_bars → `symbol,bar_type,date`; timestamps → `symbol,greek,date,mkt_actor`.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `kind` | enum | yes | `gamma` \| `delta` \| `stats` \| `strike_bars` \| `timestamps`. |
| `symbol` | string | yes | Underlying, e.g. `SPX`. |
| `date` | YYYY-MM-DD | no | Trade date. |
| `ts` | string | no | Timestamp (gamma/delta). |
| `mkt_actor` | string | no | Market-actor filter. |
| `greek` | string | no | Greek name (timestamps). |
| `bar_type` | string | no | Bar type (strike_bars). |


**Example call (SPX)**

```json
{
  "name": "spotgamma_oi_intraday",
  "arguments": {
    "kind": "gamma",
    "symbol": "SPX",
    "date": "2026-07-24"
  }
}
```


**Example output (live, 2026-07-25)**

```
Error: SpotGamma API 404 Not Found: <!DOCTYPE html>
```


> **Note:** ⚠ STALE: all five routes return **404 even with a valid token** (verified 2026-07-25). Kept for completeness.

### `spotgamma_oi`

**Endpoint:** `GET /v1/oi · GET /v1/oi/{exp}`

Open interest for a symbol — full chain OI by strike/expiry (very large for SPX). Pass `expiration` to use the per-expiry variant.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sym` | string | yes | Symbol. |
| `expiration` | string | no | Expiration for `/v1/oi/{exp}`. |
| `params` | object | no | Extra query params. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_oi",
  "arguments": {
    "sym": "SPX"
  }
}
```


**Example output (live, 2026-07-25)**

```json
��1784923200000�<�2600����bd_buy_oi�bd_sell_oi�mm_buy_oi�mm_sell_oi�cust_lt_100_buy_oi�cust_lt_100_sell_oi�cust_100_199_buy_oi�cust_100_199_sell_oi�cust_gt_199_buy_oi�cust_gt_199_sell_oi�procust_lt_100_buy_oi�procust_lt_100_sell_oi�procust_100_199_buy_oi�procust_100_199_sell_oi�procust_gt_199_buy_oi�procust_gt_199_sell_oi�firm_buy_oi�firm_sell_oi�cust_buy_oi�cust_sell_oi�procust_buy_oi�procust_sell_oi�2800����bd_buy_oi�bd_sell_oi�mm_buy_oi�mm_sell_oi�cust_lt_100_buy_oi�cust_lt_100_sell_oi�cust_100_199_buy_oi�cust_100_199_sell_oi�cust_gt_199_buy_oi�cust_gt_199_sell_oi�procust_lt_100_buy_oi�procust_lt_100_sell_oi�procust_100_199_buy_oi�procust_100_199_sell_oi�procust_gt_199_buy_oi�procust_gt_199_sell_oi�firm_buy_oi�firm_sell_oi�cust_buy_oi�cust_sell_oi�procust_buy_oi�procust_sell_oi�3000���bd_buy_oi�bd_sell_oi�mm_buy_oi�mm_sell_oi�cust_lt_100_buy_oi�cust_lt_100_sell_oi�cust_100_199_buy_oi�
… [truncated — full response 200,095 chars]
```


> **Note:** Gated (403 without token).

### `spotgamma_oi_syms`

**Endpoint:** `GET /v1/oi_syms`

List of symbols that have OI data available.

**Parameters**

_No parameters._


**Example call (SPX)**

```json
{
  "name": "spotgamma_oi_syms",
  "arguments": {}
}
```


**Example output (live, 2026-07-25)**

```json
[
  "A",
  "AA",
  "AAAU",
  "AADX",
  "AAL",
  "AAMI",
  "AAOG",
  "AAOI",
  "AAON",
  "AAOX",
  "AAOZ",
  "AAP",
  "AAPB",
  "AAPD",
  "AAPL",
  "AAPU",
  "AAPW",
  "AAPX",
  "AAPY",
  "AARD",
  "AAT",
  "AAXJ",
  "AB",
  "ABAT",
  "ABBV",
  "ABCB",
  "ABCL",
  "ABEO",
  "ABEV",
  "ABG",
  "ABL",
  "ABM",
  "ABNB",
  "ABNG",
  "ABNY",
  "ABOS",
  "ABR",
  "ABSI",
  "ABT",
  "ABTC",
  "ABTC1",
  "ABUS",
  "ABVC",
  "ABVE",
  "ABVEF",
  "ABVX",
  "ABX",
  "ACA",
  "ACAD",
  "ACB",
  "ACCO",
  "ACDC",
  "ACEL",
  "ACES",
  "ACET",
  "ACGL",
  "ACH",
  "ACHC",
  "ACHR",
  "ACHV",
  "ACI",
  "ACIC",
  "ACIO",
  "ACIU",
  "ACIW",
  "ACLS",
  "ACLX",
  "ACM",
  "ACMR",
  "ACN",
  "ACNB",
  "ACNT",
  "ACOG",
  "ACR",
  "ACRE",
  "ACRS",
  "ACT",
  "ACTG",
  "ACVA",
  "ACWI",
  "ACWV",
  "ACWX",
  "AD",
  "ADAM",
  "ADBE",
  "ADBG",
  "ADC",
  "ADCT",
  "ADEA",
  "ADI",
  "ADM",
  "ADMA",
… [truncated — full response 60,105 chars]
```


> **Note:** Gated (403 without token).

### `spotgamma_concentration`

**Endpoint:** `GET /v1/concentration`

OI concentration — where open interest clusters, grouped by `strike` or `expiration`. Large payload for SPX.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `syms` | string | yes | Comma-separated symbols. |
| `group_by` | enum | yes | `strike` \| `expiration`. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_concentration",
  "arguments": {
    "syms": "SPX",
    "group_by": "strike"
  }
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "underlying": "SPX",
    "type": "put",
    "strike": 200,
    "oi": "45641",
    "volume": "2",
    "delta": -8548.742518103489,
    "gamma": 6.814460872275434
  },
  {
    "underlying": "SPX",
    "type": "call",
    "strike": 200,
    "oi": "11014",
    "volume": "19",
    "delta": 8140015571.355159,
    "gamma": 3.5883195476587932
  },
  {
    "underlying": "SPX",
    "type": "call",
    "strike": 201,
    "oi": "16895",
    "volume": "0",
    "delta": null,
    "gamma": null
  },
  {
    "underlying": "SPX",
    "type": "put",
    "strike": 201,
    "oi": "16895",
    "volume": "0",
    "delta": null,
    "gamma": null
  },
  {
    "underlying": "SPX",
    "type": "put",
    "strike": 400,
    "oi": "43458",
    "volume": "10",
    "delta": -1598731.791828649,
    "gamma": 878.1808726838727
  },
  {
    "underlying": "SPX",
    "type": "call",
    "strike": 400,
… [truncated — full response 199,485 chars]
```


> **Note:** Verified public (worked with no token attached).

### `spotgamma_synth_oi_equities`

**Endpoint:** `GET /synth_oi/v1/equities (free: …/free_equities)`

Synthetic-OI equity table for a date — the Equity Hub dataset fired on home load. Very large payload.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date` | YYYY-MM-DD | yes | Data date. |
| `use_free` | boolean | no | Use the free variant. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_synth_oi_equities",
  "arguments": {
    "date": "2026-07-24"
  }
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "quote_date": "2026-07-23T00:00:00.000Z",
    "sym": "LUNG",
    "name": "Pulmonx Corp",
    "upx": 1.22,
    "callsum": 513,
    "putsum": 7842,
    "cv": 0,
    "pv": 0,
    "stock_volume": 98596,
    "stock_volume_30d_avg": 344245.4347826087,
    "earnings_utc": "2026-07-29T20:05:00.000Z",
    "large_call_oi": 1,
    "large_put_oi": 1,
    "put_call_ratio": 15.286549707602338,
    "gamma_ratio": "NaN",
    "delta_ratio": "NaN",
    "ne_call_volume": null,
    "ne_put_volume": null,
    "dpi_high52w": 3.88,
    "dpi_low52w": 1.13,
    "d95ne": null,
    "d25ne": null,
    "d95": null,
    "d25": null,
    "ne_skew": null,
    "skew": null,
    "atm_iv30": null,
    "rv30": 0.8926743215605233,
    "options_implied_move": null,
    "iv_slope_ne_45": null,
    "fwd_garch": 0.6972105710642068,
    "iv_pct": null,
    "iv_rank": null,
    "skew_rank": null,
    "cskew_pct": null,
… [truncated — full response 200,095 chars]
```


> **Note:** Gated; free variant available.

### `spotgamma_synth_oi_chart_data`

**Endpoint:** `GET /synth_oi/v1/chart_data`

Synthetic-OI chart series. Query schema is not fully documented — pass params through (`sym` accepted). Large payload.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `params` | object | no | Query params passed through as-is. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_synth_oi_chart_data",
  "arguments": {
    "params": {
      "sym": "SPX"
    }
  }
}
```


**Example output (live, 2026-07-25)**

```json
{
  "sym": "SPX",
  "curves": {
    "cust": {
      "delta": {
        "all": [
          107127431461.7271,
          106852247299.55037,
          106147089961.95865,
          106003173389.78842,
          105712518010.40648,
          105418151596.64198,
          104818531174.73674,
          104666401638.13579,
          104359524406.09753,
          103892768683.58673,
          103735493405.98048,
          103098114627.18176,
          102283214381.60826,
          101448743531.93814,
          100595276024.21848,
          99723293555.12769,
          98833207701.84016,
          98653051384.07045,
          98472188926.96082,
          98290623333.44829,
          97925395030.5499,
          97000244484.0487,
          96625428705.18156,
          96247945389.03964,
          96058215328.02472,
          95867833277.189,
          95485136019.80916,
… [truncated — full response 200,095 chars]
```


> **Note:** Gated (403 without token).

### `spotgamma_synth_oi_historical`

**Endpoint:** `GET /synth_oi/v1/historical (free: …/free_historical)`

Historical synthetic-OI series.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `use_free` | boolean | no | Use the free variant. |
| `params` | object | no | Extra query params. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_synth_oi_historical",
  "arguments": {
    "params": {
      "sym": "SPX"
    }
  }
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "quote_date": "2026-07-24T00:00:00.000Z",
    "sym": "SPX",
    "name": "S&P 500",
    "upx": 7411.98,
    "callsum": 11130539,
    "putsum": 14125086,
    "cv": 644612,
    "pv": 917040,
    "stock_volume": 3022307840,
    "stock_volume_30d_avg": 3089843021.6363635,
    "large_call_oi": 7000,
    "large_put_oi": 7000,
    "put_call_ratio": 1.2690388129451773,
    "gamma_ratio": "1.2579434977454706",
    "delta_ratio": "0.49442398474917076172",
    "ne_call_volume": 0.3330313428853326,
    "ne_put_volume": 0.2654333507807729,
    "dpi_high52w": 7620.89990234375,
    "dpi_low52w": 0,
    "d95ne": 0.14347333495161205,
    "d25ne": 0.09196771112037769,
    "d95": 0.2778951545273692,
    "d25": 0.12185567270829152,
    "ne_skew": -0.2330335532902471,
    "skew": -0.43353239975622804,
    "atm_iv30": 0.14722176378661855,
    "rv30": 0.10388090965084305,
… [truncated — full response 58,936 chars]
```


> **Note:** Gated; free variant available.

### `spotgamma_synth_oi_last_update`

**Endpoint:** `GET /synth_oi/v1/last_update`

Synthetic-OI last-update timestamp (US/Eastern).

**Parameters**

_No parameters._


**Example call (SPX)**

```json
{
  "name": "spotgamma_synth_oi_last_update",
  "arguments": {}
}
```


**Example output (live, 2026-07-25)**

```json
2026-07-25T08:54:55-04:00
```


> **Note:** Verified public.

### `spotgamma_synth_oi_eh_symbols`

**Endpoint:** `GET /synth_oi/v1/eh_symbols`

Equity Hub symbol universe — all symbols covered by synthetic OI, with metadata. Large payload.

**Parameters**

_No parameters._


**Example call (SPX)**

```json
{
  "name": "spotgamma_synth_oi_eh_symbols",
  "arguments": {}
}
```


**Example output (live, 2026-07-25)**

```json
{
  "A": "Agilent Technologies, Inc.",
  "AA": "Alcoa Corp",
  "AAAU": null,
  "AADX": null,
  "AAL": "American Airlines Group Inc",
  "AAMI": null,
  "AAOG": null,
  "AAOI": "Applied Optoelectronics Inc",
  "AAON": "AAON Inc",
  "AAOX": null,
  "AAP": "Advance Auto Parts Inc",
  "AAPB": null,
  "AAPD": null,
  "AAPL": "Apple Inc",
  "AAPU": null,
  "AAPX": "ETF Opportunities Trust T-Rex 2X Long Apple Daily Target ETF",
  "AARD": null,
  "AAT": "American Assets Trust Inc",
  "AAXJ": "iShares MSCI All Country Asia ex Japan ETF",
  "AB": "AllianceBernstein Holding LP",
  "ABAT": "American Battery Technology Co.",
  "ABBV": "AbbVie Inc",
  "ABCL": "AbCellera Biologics Inc",
  "ABEO": "Abeona Therapeutics Inc",
  "ABEV": "Ambev SA",
  "ABG": "Asbury Automotive Group Inc",
  "ABM": "ABM Industries Inc",
  "ABNB": "Airbnb, Inc.",
  "ABOS": "Acumen Pharmaceuticals, Inc.",
… [truncated — full response 153,521 chars]
```


> **Note:** Verified public.

### `spotgamma_synth_oi_equity_scanners`

**Endpoint:** `GET /synth_oi/v1/equityScanners`

Synthetic-OI scanner definitions/results (Equity Hub scans).

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `params` | object | no | Extra query params. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_synth_oi_equity_scanners",
  "arguments": {}
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "quote_date": "2026-07-23T04:00:00.000Z",
    "sym": "BNO",
    "name": "United States Brent Oil Fund, LP",
    "upx": 53.46,
    "callsum": 304474,
    "putsum": 25983,
    "cv": 34508,
    "pv": 2837,
    "stock_volume": 809912,
    "earnings_utc": null,
    "large_call_oi": 60,
    "large_put_oi": 48,
    "delta_ratio": "215.7519064632157621",
    "ne_call_volume": 0.07491016575866466,
    "ne_put_volume": 0.0690870637997885,
    "dpi_high52w": 60.79,
    "dpi_low52w": 27.14,
    "d95ne": 0.871316327033478,
    "d25ne": 0.860768428028873,
    "d95": 0.7212482454614647,
    "d25": 0.8399907261330726,
    "ne_skew": 0.08029873677233802,
    "skew": 0.21856772961060605,
    "atm_iv30": 0.74362846067057,
    "rv30": 0.48380754753147426,
    "options_implied_move": 2.5092708140786892,
    "iv_slope_ne_45": 0.23655942049084142,
    "fwd_garch": 0.4796705023873135,
… [truncated — full response 46,755 chars]
```


> **Note:** Gated (403 without token).

## 4. HIRO (order flow)

SpotGamma's HIRO order-flow signals: live running list, per-symbol history, and latest ticks.

### `spotgamma_running_hiro`

**Endpoint:** `GET /v6/running_hiro (free: /v1/free_running_hiro)`

Live running HIRO list — every covered symbol with the current day signal, price, and 1/5/20-day signal ranges (`low1/high1/low5/high5/low20/high20`). The paid tier includes the numeric signals; the free variant returns symbol metadata only.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `use_free` | boolean | no | Use the free variant (no token needed, fewer fields). |


**Example call (SPX)**

```json
{
  "name": "spotgamma_running_hiro",
  "arguments": {}
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "symbol": "AA",
    "day": "2026-07-24",
    "lastClose": 44.3,
    "companyName": "Alcoa Corporation",
    "sector": "Basic Materials",
    "industry": "Aluminum",
    "low1": -827848.4905893711,
    "high1": 281388.7578888623,
    "low5": -5554570.637910205,
    "high5": 1244159.646734199,
    "low20": -9591872.860736074,
    "high20": 3812282.3393777837,
    "currentDaySignal": "-824646.9116883766",
    "currentDayPrice": "44.32"
  },
  {
    "symbol": "AAL",
    "day": "2026-07-24",
    "lastClose": 14.42,
    "companyName": "American Airlines Group Inc.",
    "sector": "Industrials",
    "industry": "Airlines",
    "low1": -108027.30510386763,
    "high1": 6178518.723371716,
    "low5": -21833521.38434365,
    "high5": 7086417.110927708,
    "low20": -21833521.38434365,
    "high20": 9971629.351939628,
    "currentDaySignal": "5623525.05778965",
… [truncated — full response 185,679 chars]
```


> **Note:** Gated; free variant verified without token.

### `spotgamma_hiro_history`

**Endpoint:** `GET /v11/hiro`

HIRO history per symbol with flags for all expiries / next expiry / retail flow.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `syms` | string | yes | Symbol(s). |
| `start` | string | no | Start (API format). |
| `all` | boolean | no | `all=1` flag. |
| `next_exp` | boolean | no | `nextExp=1` flag. |
| `retail` | boolean | no | `retail=1` flag. |
| `params` | object | no | Extra query params. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_hiro_history",
  "arguments": {
    "syms": "SPX",
    "all": true,
    "next_exp": true,
    "retail": true
  }
}
```


**Example output (live, 2026-07-25)**

```json
{
  "SPX": {
    "all": [],
    "nextExp": [],
    "retail": []
  }
}
```


> **Note:** Gated (403 without token). The SPX example returned a small/empty payload — history depth may require a `start` value.

### `spotgamma_latest_hiro`

**Endpoint:** `GET /v4/latestHiro (free: /v1/free_latest_hiro)`

Latest HIRO ticks — the most recent order-flow prints. App uses `limit=720`.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `syms` | string | no | Comma-separated symbols. |
| `all` | boolean | no | `all=1` flag. |
| `limit` | integer | no | Row limit. |
| `use_free` | boolean | no | Use the free variant. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_latest_hiro",
  "arguments": {
    "syms": "SPX",
    "all": true,
    "limit": 10
  }
}
```


**Example output (live, 2026-07-25)**

```json
{
  "SPX": {
    "all": [
      {
        "instrument": "SPX",
        "mid_signal": 694633,
        "gamma_signal": 18169,
        "vega_signal": 7199996,
        "option_type": "C",
        "stock_price": 7409.9,
        "utc_time": 1784924080000
      },
      {
        "instrument": "SPX",
        "mid_signal": 289465,
        "gamma_signal": -5114,
        "vega_signal": -2739522,
        "option_type": "P",
        "stock_price": 7409.700000000001,
        "utc_time": 1784924080000
      },
      {
        "instrument": "SPX",
        "mid_signal": 2959858,
        "gamma_signal": 21717,
        "vega_signal": 56059743,
        "option_type": "C",
        "stock_price": 7409.4,
        "utc_time": 1784924085000
      },
      {
        "instrument": "SPX",
        "mid_signal": -5013208,
        "gamma_signal": 54784,
        "vega_signal": 33902009,
        "option_type": "P",
… [truncated — full response 2,355 chars]
```


> **Note:** Gated; free variant available.

## 5. Market data

Quotes, bars, futures, rates, and breadth/positioning datasets.

### `spotgamma_prices`

**Endpoint:** `GET /v1/prices`

Batch last-price quotes for a watchlist (symbols joined with `-` on the wire).

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `syms` | string[] | yes | Symbols, e.g. `["SPX","SPY"]`. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_prices",
  "arguments": {
    "syms": [
      "SPX",
      "SPY"
    ]
  }
}
```


**Example output (live, 2026-07-25)**

```json
{
  "SPX": "7409.4",
  "SPY": "738.37"
}
```


> **Note:** Verified public.

### `spotgamma_quote`

**Endpoint:** `GET /v1/twelve_quote`

Single full quote (Twelve Data proxied): open/high/low/close, change, volume, 52-week range.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `symbol` | string | yes | Symbol. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_quote",
  "arguments": {
    "symbol": "SPX"
  }
}
```


**Example output (live, 2026-07-25)**

```json
{
  "SPX": {
    "symbol": "SPX",
    "name": "Amundi Core S&P 500 Swap UCITS ETF Acc",
    "exchange": "MTA",
    "mic_code": "XMIL",
    "currency": "EUR",
    "datetime": "2026-07-24",
    "timestamp": 1784876400,
    "last_quote_at": 1784906700,
    "open": "67.080002",
    "high": "67.43000",
    "low": "67.070000",
    "close": "67.39000",
    "volume": "3982",
    "previous_close": "66.99000",
    "change": "0.40000153",
    "percent_change": "0.59710634",
    "average_volume": "72270",
    "is_market_open": false,
    "fifty_two_week": {
      "low": "55.31000",
      "high": "68.33000",
      "low_change": "12.079998",
      "high_change": "-0.94000244",
      "low_change_percent": "21.84053",
      "high_change_percent": "-1.37568",
      "range": "55.310001 - 68.330002"
    }
  }
}
```


> **Note:** Verified public.

### `spotgamma_series`

**Endpoint:** `GET /v1/twelve_series`

Time-series bars (Twelve Data proxied). Intraday: `interval=1min&outputsize=390&order=asc(&date=…)`. Daily: `interval=1day&start_date=…(&end_date=…)&order=asc`.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `symbol` | string | yes | Symbol. |
| `interval` | string | yes | e.g. `1min`, `5min`, `1day`. |
| `outputsize` | integer | no | Max bars. |
| `order` | enum | no | `asc` \| `desc`. |
| `date` | YYYY-MM-DD | no | Single day (intraday). |
| `start_date` | YYYY-MM-DD | no | Range start (daily). |
| `end_date` | YYYY-MM-DD | no | Range end (daily). |


**Example call (SPX)**

```json
{
  "name": "spotgamma_series",
  "arguments": {
    "symbol": "SPX",
    "interval": "1day",
    "start_date": "2026-07-01",
    "end_date": "2026-07-24",
    "order": "asc"
  }
}
```


**Example output (live, 2026-07-25)**

```json
{
  "SPX": {
    "meta": {
      "symbol": "SPX",
      "interval": "1day",
      "exchange_timezone": "America/New_York"
    },
    "values": [
      {
        "datetime": "2026-06-30",
        "open": 7441.27001953125,
        "high": 7508.2900390625,
        "low": 7438.0400390625,
        "close": 7499.35986328125,
        "volume": "3800695028"
      },
      {
        "datetime": "2026-07-01",
        "open": 7478.83984375,
        "high": 7521.81005859375,
        "low": 7449.6298828125,
        "close": 7483.22998046875,
        "volume": "3631311555"
      },
      {
        "datetime": "2026-07-02",
        "open": 0,
        "high": 0,
        "low": 0,
        "close": 7483.240234375,
        "volume": "3523124154"
      },
      {
        "datetime": "2026-07-06",
        "open": 7506.9599609375,
        "high": 7551.31005859375,
        "low": 7500.97021484375,
… [truncated — full response 3,550 chars]
```


> **Note:** Verified public.

### `spotgamma_futures`

**Endpoint:** `GET /v1/futures · GET /v1/futures/realtime`

Futures snapshot — e.g. `S&P ES=F` for ES (S&P 500 e-mini). Returns the full contract table (large payload). `realtime` switches to the realtime variant.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sym` | string | yes | Futures symbol, e.g. `S&P ES=F`. |
| `realtime` | boolean | no | Use `/v1/futures/realtime`. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_futures",
  "arguments": {
    "sym": "S&P ES=F"
  }
}
```


**Example output (live, 2026-07-25)**

```json
{
  "S&P ES=F": {
    "all": [
      {
        "stock_price": 7437.5,
        "utc_time": 1784865600000
      },
      {
        "stock_price": 7437,
        "utc_time": 1784865610000
      },
      {
        "stock_price": 7437,
        "utc_time": 1784865615000
      },
      {
        "stock_price": 7437,
        "utc_time": 1784865625000
      },
      {
        "stock_price": 7436.5,
        "utc_time": 1784865635000
      },
      {
        "stock_price": 7436.75,
        "utc_time": 1784865650000
      },
      {
        "stock_price": 7436.5,
        "utc_time": 1784865670000
      },
      {
        "stock_price": 7436.5,
        "utc_time": 1784865680000
      },
      {
        "stock_price": 7436.25,
        "utc_time": 1784865685000
      },
      {
        "stock_price": 7436,
        "utc_time": 1784865690000
      },
      {
        "stock_price": 7435.75,
… [truncated — full response 200,095 chars]
```


> **Note:** Verified public.

### `spotgamma_most_recent_market_open`

**Endpoint:** `GET /v1/futures/mostRecentMarketOpen`

SPX/SPY prices at the most recent market open. Tiny, fast, public — good connectivity check.

**Parameters**

_No parameters._


**Example call (SPX)**

```json
{
  "name": "spotgamma_most_recent_market_open",
  "arguments": {}
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "sym": "SPX",
    "price": 7407.75,
    "date": "2026-07-24"
  },
  {
    "sym": "SPY",
    "price": 738.59,
    "date": "2026-07-24"
  }
]
```


> **Note:** Verified public (catalog-confirmed).

### `spotgamma_treasury_rates`

**Endpoint:** `GET /v1/treasury_rates`

US Treasury yield curve for a date (1M–30Y).

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date` | YYYY-MM-DD | yes | Rates date. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_treasury_rates",
  "arguments": {
    "date": "2026-07-24"
  }
}
```


**Example output (live, 2026-07-25)**

```json
{
  "date": "2026-07-23",
  "days": [
    30,
    45,
    60,
    91,
    121,
    182,
    365,
    730,
    1095,
    1825,
    2555,
    3650,
    7300,
    10950
  ],
  "be_yields": [
    0.0382,
    0.039,
    0.0395,
    0.0395,
    0.0404,
    0.0409,
    0.0415,
    0.0437,
    0.044000000000000004,
    0.0446,
    0.0458,
    0.0471,
    0.052000000000000005,
    0.051699999999999996
  ]
}
```


> **Note:** Verified public.

### `spotgamma_dividends`

**Endpoint:** `GET /v1/dividends`

Dividend data. Note: SPX is an index — the example returned an empty array; use paying symbols (e.g. `SPY`) for dividend rows.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `params` | object | no | Query params passed through. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_dividends",
  "arguments": {
    "params": {
      "sym": "SPX"
    }
  }
}
```


**Example output (live, 2026-07-25)**

```json
[]
```


> **Note:** Verified public.

### `spotgamma_zero_dte`

**Endpoint:** `GET /v1/zeroDTE`

0DTE data for a symbol — same-day expiry positioning/greeks. Very large payload for SPX.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sym` | string | yes | Symbol. |
| `params` | object | no | Extra query params. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_zero_dte",
  "arguments": {
    "sym": "SPX"
  }
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "trade_date": "2018-01-03T00:00:00.000Z",
    "zero_dte_volume": 101175,
    "all_volume": 1422583,
    "zero_dte_oi": 160606,
    "all_oi": 12814282,
    "percent_total": 0.0711,
    "sym": "SPX"
  },
  {
    "trade_date": "2018-01-05T00:00:00.000Z",
    "zero_dte_volume": 139975,
    "all_volume": 1601808,
    "zero_dte_oi": 736905,
    "all_oi": 13713258,
    "percent_total": 0.0874,
    "sym": "SPX"
  },
  {
    "trade_date": "2018-01-10T00:00:00.000Z",
    "zero_dte_volume": 120763,
    "all_volume": 1147885,
    "zero_dte_oi": 169393,
    "all_oi": 14382321,
    "percent_total": 0.1052,
    "sym": "SPX"
  },
  {
    "trade_date": "2018-01-12T00:00:00.000Z",
    "zero_dte_volume": 203211,
    "all_volume": 1903130,
    "zero_dte_oi": 818311,
    "all_oi": 15239603,
    "percent_total": 0.1068,
    "sym": "SPX"
  },
  {
    "trade_date": "2018-01-17T00:00:00.000Z",
… [truncated — full response 200,095 chars]
```


> **Note:** Verified public.

### `spotgamma_equity_put_call_ratio`

**Endpoint:** `GET /v1/equityPutCallRatio`

Equity put/call ratio chart series (market-wide).

**Parameters**

_No parameters._


**Example call (SPX)**

```json
{
  "name": "spotgamma_equity_put_call_ratio",
  "arguments": {}
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "trade_date": "2020-01-02T05:00:00.000Z",
    "vol_ratio": 0.5111882119140359,
    "oi_ratio": 0.9094139057238133
  },
  {
    "trade_date": "2020-01-03T05:00:00.000Z",
    "vol_ratio": 0.5832193774396873,
    "oi_ratio": 0.9084244418525825
  },
  {
    "trade_date": "2020-01-06T05:00:00.000Z",
    "vol_ratio": 0.6105803448382879,
    "oi_ratio": 0.9120946593267596
  },
  {
    "trade_date": "2020-01-07T05:00:00.000Z",
    "vol_ratio": 0.6238902031437328,
    "oi_ratio": 0.9069881003263468
  },
  {
    "trade_date": "2020-01-08T05:00:00.000Z",
    "vol_ratio": 0.5049041111324907,
    "oi_ratio": 0.9022693881659597
  },
  {
    "trade_date": "2020-01-09T05:00:00.000Z",
    "vol_ratio": 0.5721215574548908,
    "oi_ratio": 0.9011720834052606
  },
  {
    "trade_date": "2020-01-10T05:00:00.000Z",
    "vol_ratio": 0.6109378554437146,
    "oi_ratio": 0.8980764137789284
  },
  {
… [truncated — full response 200,095 chars]
```


> **Note:** Verified public.

### `spotgamma_correlation_regime`

**Endpoint:** `GET /v1/correlation_regime`

Correlation regime for a symbol.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sym` | string | yes | Symbol. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_correlation_regime",
  "arguments": {
    "sym": "SPX"
  }
}
```


**Example output (live, 2026-07-25)**

```
Error: SpotGamma API 404 Not Found: <!DOCTYPE html>
```


> **Note:** ⚠ STALE: returns **404** (verified 2026-07-25). Per the app bundle, `correlation_regime` now arrives as a field inside other payloads.

### `spotgamma_trending`

**Endpoint:** `GET /v3/trending`

Trending symbols ranked by trend score (absolute move vs. expectation).

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `interval` | integer | no | Interval in minutes (app uses 30). |


**Example call (SPX)**

```json
{
  "name": "spotgamma_trending",
  "arguments": {
    "interval": 30
  }
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "symbol": "UBER",
    "trend": -3.271118485104816,
    "trend_abs": 3.271118485104816,
    "instrument": "UBER"
  },
  {
    "symbol": "GNRC",
    "trend": -3.1964294277937677,
    "trend_abs": 3.1964294277937677,
    "instrument": "GNRC"
  },
  {
    "symbol": "RUT",
    "trend": -2.7147550135285954,
    "trend_abs": 2.7147550135285954,
    "instrument": "RUT"
  },
  {
    "symbol": "XLK",
    "trend": -2.64225623814185,
    "trend_abs": 2.64225623814185,
    "instrument": "XLK"
  },
  {
    "symbol": "TEM",
    "trend": -2.6366646069260646,
    "trend_abs": 2.6366646069260646,
    "instrument": "TEM"
  },
  {
    "symbol": "RKT",
    "trend": -2.611051250490235,
    "trend_abs": 2.611051250490235,
    "instrument": "RKT"
  },
  {
    "symbol": "MRNA",
    "trend": -2.4908404326025506,
    "trend_abs": 2.4908404326025506,
    "instrument": "MRNA"
  },
  {
… [truncated — full response 1,498 chars]
```


> **Note:** Verified public.

## 6. Calendars

Earnings and macro-economic calendars.

### `spotgamma_earnings`

**Endpoint:** `GET /v1/earnings (free: /v1/free_earnings)`

Earnings calendar by date range or symbol list. Rows include `sym`, `day`, `utc`, `period` (BMO/AMC), `confirmed`, `implied_move`, call/put volume, `activity_factor`, `inHiro`. Large payload for wide ranges.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `start` | YYYY-MM-DD | no | Range start. |
| `end` | YYYY-MM-DD | no | Range end. |
| `syms` | string | no | Comma-separated symbols. |
| `use_free` | boolean | no | Use the free variant (verified without token). |


**Example call (SPX)**

```json
{
  "name": "spotgamma_earnings",
  "arguments": {
    "start": "2026-07-24",
    "end": "2026-07-31"
  }
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "sym": "VZ",
    "day": "2026-07-24T00:00:00.000Z",
    "utc": "2026-07-24T11:00:00.000Z",
    "company_name": "Verizon Communications",
    "period": "BMO",
    "confirmed": 1,
    "implied_move": 0.030620250467278985,
    "cv": 78706,
    "pv": 32200,
    "activity_factor": 0.06,
    "inHiro": true
  },
  {
    "sym": "SLB",
    "day": "2026-07-24T00:00:00.000Z",
    "utc": "2026-07-24T10:50:00.000Z",
    "company_name": "SLB ",
    "period": "BMO",
    "confirmed": 1,
    "implied_move": 0.024564206809052094,
    "cv": 32523,
    "pv": 35083,
    "activity_factor": 0.05,
    "inHiro": true
  },
  {
    "sym": "AXP",
    "day": "2026-07-24T00:00:00.000Z",
    "utc": "2026-07-24T11:00:00.000Z",
    "company_name": "American Express Co.",
    "period": "BMO",
    "confirmed": 1,
    "implied_move": 0.0389595143941473,
    "cv": 15809,
    "pv": 20022,
… [truncated — full response 200,095 chars]
```


> **Note:** Gated; free variant verified without token.

### `spotgamma_economic_calendar`

**Endpoint:** `GET /v1/fmp/api/v3/economic_calendar`

Macro-economic calendar (FMP proxied): releases with estimate/actual, country, impact.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `from` | YYYY-MM-DD | yes | Range start. |
| `to` | YYYY-MM-DD | yes | Range end. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_economic_calendar",
  "arguments": {
    "from": "2026-07-20",
    "to": "2026-07-26"
  }
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "date": "2026-07-27 04:00:00",
    "country": "KG",
    "event": "Interest Rate Decision",
    "currency": "KGS",
    "previous": 12,
    "estimate": 12,
    "actual": null,
    "change": null,
    "impact": "Low",
    "changePercentage": 0,
    "unit": "%"
  },
  {
    "date": "2026-07-27 01:30:00",
    "country": "CN",
    "event": "Industrial Profits YoY (Jun)",
    "currency": "CNY",
    "previous": 18.8,
    "estimate": 19.2,
    "actual": null,
    "change": null,
    "impact": "Low",
    "changePercentage": 0,
    "unit": "%"
  },
  {
    "date": "2026-07-27 00:00:00",
    "country": "SG",
    "event": "Monetary Policy Statement",
    "currency": "SGD",
    "previous": null,
    "estimate": null,
    "actual": null,
    "change": null,
    "impact": "Medium",
    "changePercentage": 0,
    "unit": null
  },
  {
    "date": "2026-07-26 10:00:00",
    "country": "IL",
… [truncated — full response 121,355 chars]
```


> **Note:** Verified public.

## 7. Scanners / Compass

Equity scanners and SpotGamma Compass indicators.

### `spotgamma_equity_scanners`

**Endpoint:** `GET /v1/equityScanners (free: /v1/free_equityScanners)`

Equity scanner definitions and results (gamma/OI-driven scans).

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `use_free` | boolean | no | Use the free variant. |
| `params` | object | no | Extra query params. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_equity_scanners",
  "arguments": {}
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "quote_date": "2026-07-24T00:00:00.000Z",
    "sym": "SLS",
    "name": "SELLAS Life Sciences Group Inc",
    "upx": 11.32,
    "callsum": 624265,
    "putsum": 259022,
    "earnings_utc": null,
    "largeCoi": 5,
    "largePoi": 6,
    "max_exp_g_date": "2027-01-15T21:00:00.000Z",
    "atmgc": -13871498,
    "atmgp": -5502771,
    "pv": 7192,
    "cv": 25626,
    "d95ne": 1.9113,
    "d25ne": 1.6907,
    "d95": 2.8368,
    "d25": 0,
    "stock_volume": 3319199,
    "dpi_high52w": 15.88,
    "dpi_low52w": 1.39,
    "delta_ratio": -12.2453,
    "ne_skew": 0.03767739,
    "skew": -0.99460149,
    "options_implied_move": 1.6808874582,
    "atm_iv30": 2.3525,
    "rv30": 1.4717,
    "fwd_garch": 1.169,
    "iv_pct": 0.9959,
    "iv_rank": 0.9703,
    "skew_rank": 0.0735,
    "cskew_pct": 0.004081632653061225,
    "pskew_pct": 0.37551020408163266,
    "garch_rank": 0.3147,
… [truncated — full response 29,044 chars]
```


> **Note:** Gated; free variant available.

### `spotgamma_compass`

**Endpoint:** `GET /v1/compass`

Compass snapshot per symbol — currently returns `rsi` and `bollingerBand` readings.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `syms` | string | yes | Comma-separated symbols. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_compass",
  "arguments": {
    "syms": "SPX"
  }
}
```


**Example output (live, 2026-07-25)**

```json
[
  {
    "bollingerBand": "0.20408802",
    "sym": "SPX",
    "rsi": "45.22759"
  }
]
```


> **Note:** Verified public.

### `spotgamma_compass_hist`

**Endpoint:** `GET /v1/compass_hist`

Compass history per symbol — the Compass time series.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `syms` | string | yes | Comma-separated symbols. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_compass_hist",
  "arguments": {
    "syms": "SPX"
  }
}
```


**Example output (live, 2026-07-25)**

```json
{
  "SPX": [
    {
      "close": 7411.97998046875,
      "trade_date": "2026-07-24T00:00:00.000Z",
      "iv_rank": 0.2797,
      "skew_rank": 0.196,
      "cws": 7600,
      "pws": 7300,
      "atm_iv30": 0.1471,
      "rv30": 0.1013
    },
    {
      "close": 7408.2998046875,
      "trade_date": "2026-07-23T00:00:00.000Z",
      "iv_rank": 0.3282,
      "skew_rank": 0.2,
      "cws": 7600,
      "pws": 7300,
      "atm_iv30": 0.1546,
      "rv30": 0.1014
    },
    {
      "close": 7498.9599609375,
      "trade_date": "2026-07-22T00:00:00.000Z",
      "iv_rank": 0.1867,
      "skew_rank": 0.26,
      "cws": 7600,
      "pws": 7300,
      "atm_iv30": 0.1327,
      "rv30": 0.1052
    },
    {
      "close": 7509.2001953125,
      "trade_date": "2026-07-21T00:00:00.000Z",
      "iv_rank": 0.1912,
      "skew_rank": 0.312,
      "cws": 7600,
      "pws": 7300,
      "atm_iv30": 0.1334,
… [truncated — full response 2,305 chars]
```


> **Note:** Gated (403 without token).

## 8. Content / misc + escape hatch

Dashboard content endpoints and the generic passthrough for anything not wrapped.

### `spotgamma_content_for_category`

**Endpoint:** `GET /home/contentForCategory`

CMS content for a dashboard category (e.g. `tooltips` — the UI's explanatory copy).

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `category` | string | yes | Category key, e.g. `tooltips`. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_content_for_category",
  "arguments": {
    "category": "tooltips"
  }
}
```


**Example output (live, 2026-07-25)**

```json
{
  "content": [
    {
… [truncated — full response 43,558 chars]
```


> **Note:** Verified public.

### `spotgamma_founders_notes`

**Endpoint:** `GET /foundersNotes · /foundersNotes/id · /foundersNotes/preview`

Founders Notes blog: paged listing (`page/perPage/month/year`), single note (`id`), or preview (`preview_key`). Listing is a large payload.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `page` | integer | no | Page number. |
| `per_page` | integer | no | Items per page. |
| `month` | integer | no | Filter month (1–12). |
| `year` | integer | no | Filter year. |
| `id` | integer | no | Fetch one note by id. |
| `preview_key` | string | no | Preview key. |


**Example call (SPX)**

```json
{
  "name": "spotgamma_founders_notes",
  "arguments": {
    "page": 1,
    "per_page": 2
  }
}
```


**Example output (live, 2026-07-25)**

```json
{
  "status": "success",
  "page": 1,
  "hasNextPage": true,
  "perPage": 2,
  "data": [
    {
      "title": "PM Note: Fri, July 24, 2026 at 5:18 PM ET",
      "category": "founders-notes",
      "pdfUrl": null,
… [truncated — full response 200,095 chars]
```


> **Note:** Gated (403 without token).

### `spotgamma_raw_get`

**Endpoint:** `GET {any path}`

Escape hatch: GET any catalog path with arbitrary query params — including the account endpoints (`/v1/me/user`, `/v1/me/watchlists`, `/v1/me/alerts`, …) and misc routes (`/v2/occ`, `/v1/allReviews`, `/v1/zendesk_article`, …). Set `auth: true` for gated paths.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `path` | string | yes | API path starting with `/`. |
| `params` | object | no | Query params passed through. |
| `auth` | boolean | no | Require/attach Bearer token (default: attach when configured). |


**Example call (SPX)**

```json
{
  "name": "spotgamma_raw_get",
  "arguments": {
    "path": "/v1/me/user",
    "auth": true
  }
}
```


**Example output (live, 2026-07-25)**

```json
{
  "firstName": "Filipe",
  "lastName": "Salvio",
  "email": "<email>",
  "username": "<email>",
  "id": 30787,
  "sgId": "0542f012-96a3-45d4-8af2-9fb17b554433",
  "isInstitutional": false,
  "settings": {
    "oi": {
      "zoom": 0.01,
      "hiroSyms": {
        "SPX": "S&P 500"
      },
      "hideLevels": false,
      "scaleRange": "auto",
      "strikeZoom": 0.35,
      "useWhiteMode": false,
      "selectedLense": 1,
      "strikeBarType": "gamma",
      "candleDuration": 300,
      "hideColorScale": false,
      "showGexZeroDte": true,
      "hideContourLines": false,
      "statsLookbackDays": 90,
      "strikeBarsTrackerDisabled": false
    },
    "hiro": {
      "tabs": [
        "S&P 500",
        "SPX",
        "SPY",
        "IWM",
        "AAPL",
        "GOOGL",
        "META",
        "MSFT",
        "NVDA",
        "TSLA",
        "IBIT",
        "Mag7",
… [truncated — full response 22,699 chars]
```


> **Note:** Example shows `/v1/me/user` (gated) — account profile with memberships.
