# MenthorQ MCP — Tool Reference with SPX Examples

Complete documentation for the `menthorq-mcp` server (`mcp/menthorq_mcp.py`).
Every tool wraps a live endpoint of the MenthorQ data platform
(`gateway.menthorq.io` — see `../API_ENDPOINTS.md` for the full API map).

## How it works

```
MCP client (Kimi)  ──stdio JSON-RPC──▶  menthorq_mcp.py  ──HTTPS──▶  gateway.menthorq.io
                                            │
                                            └─ auth: Cognito accessToken, resolved per call from
                                               MENTHORQ_TOKEN env var, or pulled live from your
                                               logged-in dashboard.menthorq.io Chrome tab (WebBridge)
```

- Transport: newline-delimited JSON-RPC 2.0 on stdio, protocol `2024-11-05`.
- Every tool returns one text content item with JSON
  `{"http_status": <int>, "data": <endpoint JSON>}`; `http_status >= 400`
  (or a failed request) also sets `isError: true`.
- Dates are `YYYY-MM-DD`; candle timestamps are millisecond epoch; token cache
  is in-memory only (5 min) — nothing is written to disk.
- Already registered in Kimi (`…/kimi-code/home/mcp.json`); new sessions see
  the tools automatically.

## Calling a tool

Natural language works in Kimi (e.g. *“get SPX gamma levels”*). On the wire,
a call looks like this:

```json
{"jsonrpc": "2.0", "id": 7, "method": "tools/call",
 "params": {"name": "menthorq_gamma_levels",
            "arguments": {"ticker": "SPX", "frequency": "eod"}}}
```

## Conventions used in the examples below

- All examples use **SPX** and come from real captured responses
  (archive date 2026-07-24/25, stored in `../menthorq.db`).
- Output is trimmed for readability: `… (+N more items)` markers show where.
- Personal data (profile, chat titles) is redacted.

---


### 1. `menthorq_tickers`

**Endpoint:** `clickhouse-api GET /api/web/v1/tickers`

Full instrument universe (~1250 stocks/ETFs/futures with contracts).

**When to use it:** Discover every instrument the platform covers — stocks, ETFs and futures (with contract chains). Use it to resolve provider-specific ticker formats such as `DATABENTO#ES`.

**Parameters:**

_No parameters._

**Example call:**

```json
{"name": "menthorq_tickers", "arguments": {}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": [
    {
      "ticker": "DATABENTO#6A",
      "symbol": "6A",
      "provider": "DATABENTO",
      "name": "Australian Dollar Futures",
      "exchange": "CME",
      "asset_type": "FUTURE",
      "category": "FOREX",
      "calendar_code": "CME_FX",
      "…": "(+2 more keys)"
    },
    {
      "ticker": "DATABENTO#6B",
      "symbol": "6B",
      "provider": "DATABENTO",
      "name": "British Pound Futures",
      "exchange": "CME",
      "asset_type": "FUTURE",
      "category": "FOREX",
      "calendar_code": "CME_FX",
      "…": "(+2 more keys)"
    },
    "… (+1254 more items)"
  ]
}
```

> **Note:** The full list has 1,256 entries and weighs ~300 KB; the example shows one futures entry.


---

### 2. `menthorq_prices`

**Endpoint:** `clickhouse-api GET /api/web/v1/prices?tickers={csv}`

Latest price snapshot (current/open/high/low/previous_close) for a comma-separated list of tickers.

**When to use it:** Quick price snapshot (current, open, high, low, previous close) for one or many tickers in a single batched call.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `tickers` | string | ✅ | — | Comma-separated tickers, e.g. 'SPX,SPY,QQQ' |

**Example call:**

```json
{"name": "menthorq_prices", "arguments": {"tickers": "SPX,SPY,QQQ"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": [
    {
      "ticker": "SPX",
      "current": 7411.99,
      "open": 7412.01,
      "high": 7461.02,
      "low": 7396.37,
      "previous_close": 7411.98
    },
    {
      "ticker": "SPY",
      "current": 738.18,
      "open": 738.51,
      "high": 743.72,
      "low": 737.29,
      "previous_close": 738.93
    },
    {
      "ticker": "QQQ",
      "current": 684.8,
      "open": 690.41,
      "high": 692.63,
      "low": 682.48,
      "previous_close": 684.23
    },
    "… (+5 more items)"
  ]
}
```


---

### 3. `menthorq_market_status`

**Endpoint:** `clickhouse-api GET /api/web/v1/market-status/{exchange}`

Market open/closed status and session times. Only NYSE and NASDAQ are supported.

**When to use it:** Check whether a venue is open before polling intraday data; returns session times in UTC and local time plus the next open date.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `exchange` | string | — | `"NYSE"` |  |

**Example call:**

```json
{"name": "menthorq_market_status", "arguments": {"exchange": "NYSE"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": {
    "exchange": "NYSE",
    "asset_type": "STOCK",
    "date": "2026-07-25",
    "status": "CLOSED",
    "is_open": false,
    "open_time_utc": "13:30",
    "close_time_utc": "20:00",
    "open_time_local": "09:30",
    "…": "(+7 more keys)"
  }
}
```

> **Note:** Only NYSE and NASDAQ are supported upstream; other exchanges return 404.


---

### 4. `menthorq_gamma_levels`

**Endpoint:** `clickhouse-api GET /api/web/v1/gamma-levels/{ticker}/{frequency}`

Gamma exposure key levels: gex_1..gex_10, call resistance, put support, 0DTE variants, gamma wall, HVL, 1-day expected move.

**When to use it:** The flagship MenthorQ levels: ten GEX strikes, call resistance / put support (incl. 0DTE variants), gamma wall, HVL (high-volatility level) and the 1-day expected move band. `eod` = previous close snapshot, `intraday` = latest 15-min update.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `ticker` | string | ✅ | — | Ticker symbol, e.g. SPX, SPY, NVDA. Futures use provider format like DATABENTO#ES (see menthorq_tickers). |
| `frequency` | string (`eod`\|`intraday`) | — | `"eod"` | eod = previous close snapshot; intraday = latest intraday update |

**Example call:**

```json
{"name": "menthorq_gamma_levels", "arguments": {"ticker": "SPX", "frequency": "eod"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": {
    "ticker": "SPX",
    "timestamp": "2026-07-24T20:00:00",
    "frequency": "eod",
    "gex_1": 7400.0,
    "gex_2": 7475.0,
    "gex_3": 7425.0,
    "gex_4": 7430.0,
    "gex_5": 7390.0,
    "…": "(+14 more keys)"
  }
}
```


---

### 5. `menthorq_gamma_insights`

**Endpoint:** `clickhouse-api GET /api/web/v1/gamma-insights/{ticker}?limit={n}`

Per-expiration gamma insights (GEX, percentiles) for a ticker.

**When to use it:** Per-expiration gamma positioning — GEX value and its 1-year percentile for each of the nearest expirations.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `ticker` | string | ✅ | — | Ticker symbol, e.g. SPX, SPY, NVDA. Futures use provider format like DATABENTO#ES (see menthorq_tickers). |
| `limit` | integer | — | `20` |  |

**Example call:**

```json
{"name": "menthorq_gamma_insights", "arguments": {"ticker": "SPX"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": [
    {
      "report_date": "2026-07-24",
      "gex": -272223669.08094794,
      "gex_percentile_1y": 0.17716535433070865
    },
    {
      "report_date": "2026-07-23",
      "gex": -441130503.57599556,
      "gex_percentile_1y": 0.13385826771653545
    },
    "… (+18 more items)"
  ]
}
```


---

### 6. `menthorq_gamma_insights_expirations`

**Endpoint:** `clickhouse-api GET /api/web/v1/gamma-insights/{ticker}/expirations?frequency={f}`

Gamma insight summary across expirations.

**When to use it:** The full expiration ladder for a ticker (SPX has 50+), each with GEX and percentile — the input for term-structure analysis.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `ticker` | string | ✅ | — | Ticker symbol, e.g. SPX, SPY, NVDA. Futures use provider format like DATABENTO#ES (see menthorq_tickers). |
| `frequency` | string (`eod`\|`intraday`) | — | `"eod"` | eod = previous close snapshot; intraday = latest intraday update |

**Example call:**

```json
{"name": "menthorq_gamma_insights_expirations", "arguments": {"ticker": "SPX", "frequency": "eod"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": [
    {
      "expiration_date": "2026-07-27",
      "net_gex": -43076663.746364474,
      "net_gex_share": -0.05984267223041534
    },
    {
      "expiration_date": "2026-07-28",
      "net_gex": -39829918.68741109,
      "net_gex_share": -0.055332250960962566
    },
    "… (+52 more items)"
  ]
}
```


---

### 7. `menthorq_metrics_eod`

**Endpoint:** `clickhouse-api GET /api/web/v1/metrics/{ticker}/eod?fields=…&limit={n}`

Daily metrics history (default 30 rows). Fields: option, momentum, volatility, seasonality.

**When to use it:** Daily history (default 30 rows) of four metric families: `option` (GEX/DEX positioning), `momentum`, `volatility`, `seasonality`.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `ticker` | string | ✅ | — | Ticker symbol, e.g. SPX, SPY, NVDA. Futures use provider format like DATABENTO#ES (see menthorq_tickers). |
| `fields` | array of string | — | `["option", "momentum", "volatility", "seasonality"]` |  |
| `limit` | integer | — | `30` |  |

**Example call:**

```json
{"name": "menthorq_metrics_eod", "arguments": {"ticker": "SPX"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": [
    {
      "date": "2026-07-24",
      "metrics": {
        "momentum": 2.0,
        "seasonality": -0.8539630261047333,
        "volatility": 2.0,
        "option": 1.0,
        "iv_1m_50d": null,
        "iv_3m_50d": null,
        "iv_0dte_50d": null,
        "skew_1m": null,
        "…": "(+2 more keys)"
      }
    },
    "… (+29 more items)"
  ]
}
```


---

### 8. `menthorq_metrics_intraday`

**Endpoint:** `clickhouse-api GET /api/web/v1/metrics/{ticker}/intraday?fields=…&limit={n}`

Intraday (30-min bar) IV/skew metrics. Valid fields only: iv_1m_50d, iv_3m_50d, iv_0dte_50d, skew_1m, skew_3m, skew_0dte.

**When to use it:** 30-minute-bar IV and skew series. Only these literal fields are accepted: `iv_1m_50d`, `iv_3m_50d`, `iv_0dte_50d`, `skew_1m`, `skew_3m`, `skew_0dte` — the family aliases used by `metrics_eod` return HTTP 422 here.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `ticker` | string | ✅ | — | Ticker symbol, e.g. SPX, SPY, NVDA. Futures use provider format like DATABENTO#ES (see menthorq_tickers). |
| `fields` | array of string | — | `["iv_1m_50d", "skew_1m"]` |  |
| `limit` | integer | — | `30` |  |

**Example call:**

```json
{"name": "menthorq_metrics_intraday", "arguments": {"ticker": "SPX"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": [
    {
      "timestamp": "2026-07-24T19:45:00Z",
      "metrics": {
        "iv_1m_50d": 0.14286156603823813,
        "skew_1m": 0.4597556736476058
      }
    },
    {
      "timestamp": "2026-07-24T19:15:00Z",
      "metrics": {
        "iv_1m_50d": 0.14126485286203508,
        "skew_1m": 0.46451276622580145
      }
    },
    "… (+28 more items)"
  ]
}
```


---

### 9. `menthorq_options_matrix`

**Endpoint:** `clickhouse-api GET /api/web/v1/options/matrix/{ticker}?frequency={f}`

Full option matrix: per-expiration strike grid with greeks/positioning and totals.

**When to use it:** The complete option matrix: every expiration with a per-strike grid (GEX/DEX/greeks) plus aggregated totals — the heaviest dataset (10–30 KB per call).

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `ticker` | string | ✅ | — | Ticker symbol, e.g. SPX, SPY, NVDA. Futures use provider format like DATABENTO#ES (see menthorq_tickers). |
| `frequency` | string (`eod`\|`intraday`) | — | `"eod"` | eod = previous close snapshot; intraday = latest intraday update |

**Example call:**

```json
{"name": "menthorq_options_matrix", "arguments": {"ticker": "SPX", "frequency": "eod"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": {
    "ticker": "SPX",
    "timestamp": "2026-07-24T20:00:00",
    "frequency": "eod",
    "spot_price": 7412.88,
    "totals": {
      "net_gex": -224874315.51156992,
      "abs_gex": 4481420366.784641,
      "net_dex": 951208133672.6595,
      "abs_dex": 3787110087226.3447,
      "net_oi": -2739182.0,
      "abs_oi": 17977856.0
    },
    "expirations": [
      {
        "expiration_date": "2026-07-27",
        "dte": 3,
        "net_gex": -43076663.746364474,
        "abs_gex": 134618895.5844001,
        "net_dex": -12364948307.482584,
        "abs_dex": 18079214283.94376,
        "…": "(+13 more keys)"
      },
      "… (+53 more items)"
    ]
  }
}
```

> **Note:** Example heavily trimmed; SPX carries ~54 expirations × ~19 strikes.


---

### 10. `menthorq_put_call_ratio`

**Endpoint:** `clickhouse-api GET /api/web/v1/options/put-call-ratio/{ticker}?frequency={f}`

Latest put/call ratio snapshot (volume-based).

**When to use it:** Latest volume-based put/call ratio with call/put volumes. Returns the most recent snapshot only, not a series. `frequency` is required.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `ticker` | string | ✅ | — | Ticker symbol, e.g. SPX, SPY, NVDA. Futures use provider format like DATABENTO#ES (see menthorq_tickers). |
| `frequency` | string (`eod`\|`intraday`) | — | `"eod"` | eod = previous close snapshot; intraday = latest intraday update |

**Example call:**

```json
{"name": "menthorq_put_call_ratio", "arguments": {"ticker": "SPX", "frequency": "eod"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": {
    "timestamp": "2026-07-24T20:00:00Z",
    "volume_calls": 618396,
    "volume_puts": 888166,
    "put_call_ratio": 1.4362415022089405
  }
}
```


---

### 11. `menthorq_dealer_positioning`

**Endpoint:** `clickhouse-api GET /api/web/v1/dealer-positioning/{ticker}`

Dealer positioning: net GEX/DEX current + 1h/1d deltas, GEX by DTE bucket.

**When to use it:** Estimated dealer book: net GEX / net DEX right now, 1h and 1d deltas, and GEX split by DTE bucket (0–7d, 8–30d, >30d).

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `ticker` | string | ✅ | — | Ticker symbol, e.g. SPX, SPY, NVDA. Futures use provider format like DATABENTO#ES (see menthorq_tickers). |

**Example call:**

```json
{"name": "menthorq_dealer_positioning", "arguments": {"ticker": "SPX"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": {
    "reference_timestamp": "2026-07-24T20:00:00Z",
    "net_gex": {
      "current": -272223669.08094794,
      "delta_1h": 206173249.7084276,
      "delta_1d": 168906834.49504763
    },
    "net_dex": {
      "current": 1083876964535.2682,
      "delta_1h": 42576126326.0332,
      "delta_1d": 27212621850.728638
    },
    "gex_dte_0_7d": {
      "current": -246366740.6218558,
      "delta_1h": 15239343.834411085,
      "delta_1d": -20756042.40390551
    },
    "gex_dte_8_30d": {
      "current": -158253752.3755536,
      "delta_1h": -15880046.73246038,
      "delta_1d": -35717504.700209856
    },
    "gex_dte_over_30d": {
      "current": 179746177.48583958,
      "delta_1h": 2971142.7383752167,
      "delta_1d": -538810.6515506506
    }
  }
}
```


---

### 12. `menthorq_volatility_insights`

**Endpoint:** `clickhouse-api GET /api/web/v1/volatility-insights/{ticker}`

Volatility dashboard: skew (0DTE/1M/3M + percentiles), ATM IV vs 50d, variance risk premium.

**When to use it:** Volatility dashboard in one call: skew (0DTE/1M/3M with percentiles), ATM IV vs its 50-day history, and variance risk premium (VRP with 63-day average and 1-year percentile).

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `ticker` | string | ✅ | — | Ticker symbol, e.g. SPX, SPY, NVDA. Futures use provider format like DATABENTO#ES (see menthorq_tickers). |

**Example call:**

```json
{"name": "menthorq_volatility_insights", "arguments": {"ticker": "SPX"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": {
    "skew": {
      "report_date": "2026-07-24",
      "skew_0dte": 0.3082603289442907,
      "skew_1m": 0.46611434433520743,
      "skew_3m": 0.4752221316440332,
      "history": [
        {
          "report_date": "2026-07-16",
          "skew_0dte": 0.3749282791561458,
          "skew_1m": 0.4451230195105469,
          "skew_3m": 0.45040791326538465
        },
        {
          "report_date": "2026-07-17",
          "skew_0dte": 0.44333190005301815,
          "skew_1m": 0.4926288924277708,
          "skew_3m": 0.4812563842156153
        },
        "… (+5 more items)"
      ]
    },
    "iv": {
      "report_date": "2026-07-24",
      "iv_0dte_50d": 0.09624759634877814,
      "iv_1m_50d": 0.13989553693068943,
      "iv_3m_50d": 0.14691880495181103,
      "iv_0dte_50d_percentile_1y": 0.2440944881889764,
      "iv_1m_50d_percentile_1y": 0.6141732283464567,
      "iv_3m_50d_percentile_1y": 0.547244094488189,
      "iv_0dte_50d_rank": 0.16704777907601592,
      "…": "(+6 more keys)"
    },
    "vrp": {
      "report_date": "2026-07-24",
      "vrp": 0.04004193704163235,
      "vrp_63": 0.019620024678281806,
      "vrp_percentile_1y": 0.7598425196850394,
      "vrp_63_percentile_1y": 0.4448818897637795,
      "nvrp": 0.4010064442956606,
      "nvrp_3m": 0.15412578687811382,
      "previous": {
        "report_date": "2026-07-23",
        "vrp": 0.05111917321820868,
        "vrp_63": 0.024832194846805516
      },
      "…": "(+1 more keys)"
    }
  }
}
```


---

### 13. `menthorq_candles`

**Endpoint:** `clickhouse-api GET /api/web/v1/tickers/{ticker}/candles?interval=…&from=…&to=…&countBack=…`

OHLC candles. Intervals (case-sensitive): 1m..45m, 1h..4h, 1D, 1W, 1M. from_ms/to_ms are millisecond epoch.

**When to use it:** OHLC bars for charting. Intervals are case-sensitive: `1m…45m`, `1h…4h`, `1D`, `1W`, `1M`. If you omit `from_ms`/`to_ms` the server uses the last 48 hours.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `ticker` | string | ✅ | — | Ticker symbol, e.g. SPX, SPY, NVDA. Futures use provider format like DATABENTO#ES (see menthorq_tickers). |
| `interval` | string | — | `"5m"` |  |
| `from_ms` | integer | — | — | Start, ms epoch (default: 48h ago) |
| `to_ms` | integer | — | — | End, ms epoch (default: now) |
| `count_back` | integer | — | `288` |  |

**Example call:**

```json
{"name": "menthorq_candles", "arguments": {"ticker": "SPX", "interval": "5m"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": [
    {
      "o": 7506.45,
      "h": 7507.61,
      "l": 7505.35,
      "c": 7507.4,
      "t": 1784650500000,
      "v": 0
    },
    {
      "o": 7507.58,
      "h": 7509.83,
      "l": 7507.15,
      "c": 7509.72,
      "t": 1784650800000,
      "v": 0
    },
    "… (+286 more items)"
  ]
}
```


---

### 14. `menthorq_tradingview`

**Endpoint:** `clickhouse-api GET /api/web/v1/tickers/{ticker}/tradingview`

TradingView chart configuration payload for a ticker.

**When to use it:** Symbol metadata formatted for TradingView chart embedding (ticker description, session, timezone, price scale).

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `ticker` | string | ✅ | — | Ticker symbol, e.g. SPX, SPY, NVDA. Futures use provider format like DATABENTO#ES (see menthorq_tickers). |

**Example call:**

```json
{"name": "menthorq_tradingview", "arguments": {"ticker": "SPX"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": {
    "ticker": "INTRINIO#SPX",
    "symbol": "SPX",
    "provider": "INTRINIO",
    "name": "S&P 500 Index",
    "exchange": "NYSE",
    "asset_type": "STOCK",
    "category": "INDEX",
    "calendar_code": "NYSE",
    "…": "(+4 more keys)"
  }
}
```


---

### 15. `menthorq_screener_columns`

**Endpoint:** `clickhouse-api GET /api/web/v1/screeners/columns`

Catalog of all ~90 screener columns (name, label, category, description).

**When to use it:** Catalog of all 90 screener columns with labels, categories and formatters — call this first to build valid `columns` lists for `menthorq_screener`.

**Parameters:**

_No parameters._

**Example call:**

```json
{"name": "menthorq_screener_columns", "arguments": {}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": [
    {
      "name": "ticker",
      "label": "Ticker",
      "category": "Identifiers",
      "subcategory": "",
      "description": "Stock symbol identifier",
      "formatter": {
        "type": "string",
        "unit": null
      }
    },
    {
      "name": "datetime_updated",
      "label": "Updated At",
      "category": "Identifiers",
      "subcategory": "",
      "description": "Last data update timestamp",
      "formatter": {
        "type": "datetime",
        "unit": null
      }
    },
    "… (+88 more items)"
  ]
}
```


---

### 16. `menthorq_screener`

**Endpoint:** `clickhouse-api GET /api/web/v1/screeners?columns={csv}&tickers={csv}`

Run screener over given tickers with chosen columns.

**When to use it:** Tabular fundamentals/positioning data across tickers — one row per ticker with the requested columns.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `tickers` | string | ✅ | — | Comma-separated tickers |
| `columns` | string | — | `"name,quote_type,sector,industry,market_cap,volume"` | Comma-separated column names, e.g. 'name,sector,market_cap,volume' |

**Example call:**

```json
{"name": "menthorq_screener", "arguments": {"tickers": "SPX,SPY,QQQ"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": [
    {
      "ticker": "AAPL",
      "data": {
        "name": "Apple Inc.",
        "quote_type": "EQUITY",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "market_cap": 4891182891008.0,
        "volume": 47283275
      }
    },
    {
      "ticker": "AMZN",
      "data": {
        "name": "Amazon.com",
        "quote_type": "EQUITY",
        "sector": "Consumer Cyclical",
        "industry": "Internet Retail",
        "market_cap": 2496832733184.0,
        "volume": 34680079
      }
    },
    "… (+8 more items)"
  ]
}
```


---

### 17. `menthorq_qbot_assets`

**Endpoint:** `qbot-service GET /api/web/v1/assets`

QBot asset catalog (~1400) with type, category, OI/volume percentiles.

**When to use it:** QBot's asset catalog (~1,400) with asset type, category and open-interest / volume percentiles.

**Parameters:**

_No parameters._

**Example call:**

```json
{"name": "menthorq_qbot_assets", "arguments": {}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": [
    {
      "ticker": "6AH2027",
      "assetType": "FUTURE",
      "shortName": "Australian Dollar Futures Futures Mar 2027",
      "category": "FOREX",
      "isGeneric": false,
      "oiPerc": 19,
      "volumePerc": 0
    },
    {
      "ticker": "6AU2026",
      "assetType": "FUTURE",
      "shortName": "Australian Dollar Futures Futures Sep 2026",
      "category": "FOREX",
      "isGeneric": false,
      "oiPerc": 58,
      "volumePerc": 89
    },
    "… (+1391 more items)"
  ]
}
```


---

### 18. `menthorq_events`

**Endpoint:** `qbot-service GET /api/web/v1/events?ticker=…&kind=…&start_date=…&end_date=…`

Significant market events for a ticker in a date range.

**When to use it:** Significant detected events for a ticker inside a date range (dates are `YYYY-MM-DD`).

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `ticker` | string | ✅ | — | Ticker symbol, e.g. SPX, SPY, NVDA. Futures use provider format like DATABENTO#ES (see menthorq_tickers). |
| `kind` | string | — | `"news_significant"` |  |
| `start_date` | string | ✅ | — | YYYY-MM-DD |
| `end_date` | string | ✅ | — | YYYY-MM-DD |

**Example call:**

```json
{"name": "menthorq_events", "arguments": {"ticker": "SPX", "start_date": "2026-07-11", "end_date": "2026-07-25"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": {
    "events": [
      {
        "ticker": "SPX",
        "kind": "news_significant",
        "date": "2026-07-17",
        "narrative": "The S&P 500 fell on July 17 as U.S. stocks slid and chip stocks extended losses for a third day. The index also finished below its 50-day mo…",
        "primary_news": {
          "id": "news#2026-07-17T13:04:45#3806850c",
          "title": "S&P500 and Nasdaq 100: US Stocks Drop as Chip Stocks Extend Losses",
          "text": "The Nasdaq and S&P 500 slid as chip stocks dropped for a third day. Read the latest stock market analysis and what could drive US indices ne…",
          "url": "https://www.fxempire.com/forecasts/article/sp500-and-nasdaq-100-us-stocks-drop-as-chip-stocks-extend-losses-1611127",
          "source": "fxempire.com",
          "published_date": "2026-07-17T13:04:45"
        },
        "supporting_news": [
          {
            "id": "news#2026-07-17T18:51:55#2458a76c",
            "title": "S&P 500 Snapshot: Index Drops Below 50-Day MA",
            "text": "The S&P 500 started and ended the week on a sour note, ultimately resulting in a 1.6% loss. Key Takeaways The S&P 500 posted a 1.6% weekly l…",
            "url": "https://www.etftrends.com/fixed-income-content-hub/sp-500-snapshot-index-drops-below-50-day-ma/",
            "source": "etftrends.com",
            "published_date": "2026-07-17T18:51:55"
          }
        ]
      }
    ],
    "total": 1
  }
}
```


---

### 19. `menthorq_company_news`

**Endpoint:** `qbot-service GET /api/web/v1/company-news?ticker=…&date=…&number=…`

Latest company news articles for a ticker.

**When to use it:** Curated company news articles for a given day, with title, source and sentiment fields.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `ticker` | string | ✅ | — | Ticker symbol, e.g. SPX, SPY, NVDA. Futures use provider format like DATABENTO#ES (see menthorq_tickers). |
| `date` | string | ✅ | — | YYYY-MM-DD |
| `number` | integer | — | `12` |  |

**Example call:**

```json
{"name": "menthorq_company_news", "arguments": {"ticker": "SPX", "date": "2026-07-25"}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": {
    "articles": [
      {
        "ticker": "SPX",
        "date": "2026-07-24",
        "title": "S&P 500 Snapshot: Index Ends Choppy Week in the Red",
        "summary": "The S&P 500 ended its choppy week in the red, ultimately finishing with a loss of 0.6%. This marks t…",
        "url": "https://www.etftrends.com/fixed-income-content-hub/sp-500-snapshot-index-ends-choppy-week-red/"
      },
      "… (+11 more items)"
    ],
    "total": 12
  }
}
```


---

### 20. `menthorq_user_me`

**Endpoint:** `user-service GET /api/web/v1/users/me`

Account profile of the logged-in MenthorQ user.

**When to use it:** The logged-in account's profile and entitlements (plan, features). Personal fields are redacted in this documentation.

**Parameters:**

_No parameters._

**Example call:**

```json
{"name": "menthorq_user_me", "arguments": {}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": {
    "id": "«redacted»",
    "wordpress_id": 12623,
    "email": "«redacted»",
    "phone": "«redacted»",
    "first_name": "«redacted»",
    "last_name": "«redacted»",
    "is_affiliate": false,
    "discord_user_id": "«redacted»",
    "…": "(+6 more keys)"
  }
}
```


---

### 21. `menthorq_watchlists`

**Endpoint:** `user-service GET /api/web/v1/watchlists`

User watchlists (user-service).

**When to use it:** The user's saved watchlists (empty list if none have been created).

**Parameters:**

_No parameters._

**Example call:**

```json
{"name": "menthorq_watchlists", "arguments": {}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": []
}
```


---

### 22. `menthorq_chats`

**Endpoint:** `chat-service GET /api/web/v1/chats`

QUIN chat list (chat-service, paginated).

**When to use it:** QUIN conversation list, paginated (`next_page` cursor for more).

**Parameters:**

_No parameters._

**Example call:**

```json
{"name": "menthorq_chats", "arguments": {}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": {
    "items": [
      {
        "id": "0d6e8289-d216-47df-8031-ea959bfe1213",
        "title": "«redacted»",
        "assistant_id": "«redacted»",
        "user_id": "«redacted»",
        "created_at": "2026-07-25T03:44:22.731896",
        "updated_at": "2026-07-25T04:02:07.895848"
      },
      "… (+9 more items)"
    ],
    "next_page": null
  }
}
```


---

### 23. `menthorq_screener_templates`

**Endpoint:** `chat-service GET /api/web/v1/screener-templates`

QUIN screener templates list.

**When to use it:** Pre-built screener templates (with their UUIDs); fetch one by ID via the same service path `/screener-templates/{id}`.

**Parameters:**

_No parameters._

**Example call:**

```json
{"name": "menthorq_screener_templates", "arguments": {}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": {
    "items": [
      {
        "id": "de82c774-0286-434b-a170-dd6eea6b63f1",
        "name": "Top 20 Stocks by Market Cap with Bearish Swing Bias",
        "category": {
          "slug": "SWING_TRADER",
          "label": "Swing Trader"
        },
        "initial_prompt": "Show the top 20 stocks by market cap with Swing Model Bias = Bearish",
        "created_at": "2026-03-09 08:58:06.681266",
        "allowed": true
      },
      "… (+42 more items)"
    ],
    "next_page": null
  }
}
```


---

### 24. `menthorq_chat_templates`

**Endpoint:** `chat-service GET /api/web/v1/templates?type=suggested`

Suggested QUIN chat templates.

**When to use it:** Suggested QUIN prompt templates grouped by use case — good inspiration for what the platform can answer.

**Parameters:**

_No parameters._

**Example call:**

```json
{"name": "menthorq_chat_templates", "arguments": {}}
```

**Example response** (real, trimmed):

```json
{
  "http_status": 200,
  "data": {
    "items": [
      {
        "id": "472b6bef-df3e-4a6f-8813-ad747cb20ae6",
        "sku": "0d1",
        "category": {
          "slug": "0DTE_TRADER",
          "label": "0DTE Trader"
        },
        "content": "Where is the largest gamma concentration relative to current price for SPX, and what are the next mo…",
        "created_at": "2026-03-06T08:34:35.006280"
      },
      "… (+41 more items)"
    ],
    "next_page": null
  }
}
```


---


## Error behavior

| Situation | What you get |
|---|---|
| Endpoint returns 4xx/5xx | `http_status` set accordingly, `isError: true`, upstream error body in `data` |
| Session expired | `isError: true`, message: “MenthorQ session expired — … log in again” |
| WebBridge unreachable | `isError: true`, message advising to open Chrome or set `MENTHORQ_TOKEN` |
| Rate limit (429) / 5xx | retried automatically with backoff (up to 3 attempts) |

## Tips

- Start with `menthorq_market_status` before requesting intraday series on
  weekends/holidays — markets closed means the latest bars end at Friday's close.
- `metrics_intraday` rejects the `option`/`momentum`/`volatility`/`seasonality`
  aliases (HTTP 422); use the literal IV/skew field names.
- Futures need provider tickers (`DATABENTO#ES`); find exact symbols via
  `menthorq_tickers`.
- Large payloads (`options_matrix`, `tickers`, `qbot_assets`) can exceed
  150 KB — prefer targeted calls in interactive sessions.

*Generated by `mcp/gen_docs.py` from the live server schema and the scrape
archive — regenerate after changing the server.*
