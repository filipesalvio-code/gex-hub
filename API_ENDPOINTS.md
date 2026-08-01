# MenthorQ API Endpoint Catalog

Discovered 2026-07-25 via network capture + Next.js bundle analysis of `dashboard.menthorq.io`,
verified with live authenticated calls (user's own Premium session). Source of truth: `menthorq.db` table `api_endpoints`.

## Architecture

- **SPA**: `https://dashboard.menthorq.io` (Next.js/turbopack, NextAuth)
- **Auth**: OIDC — menthorq.com (WordPress) → AWS Cognito (`main-app.auth.us-east-2.amazoncognito.com`) → SPA session at `GET /api/auth/session` returns `{accessToken, idToken, expiresAt, groups}`. API calls use `Authorization: Bearer <accessToken>` (CORS preflight from origin `https://dashboard.menthorq.io`).
- **Gateways**: `https://gateway.menthorq.io/<service>/api/web/v1/...` and mirror `https://cf.menthorq.io/<service>/...` (CloudFront).
- **Services**: `clickhouse-api` (market data), `qbot-service` (news/events/assets), `user-service` (profile/watchlists/preferences), `chat-service` (QUIN chats/screeners/templates).

## Endpoints

| Service | Method | Path | Params | Verified |
|---|---|---|---|---|
| chat-service | GET | `/api/web/v1/chat-context` | — | 200 |
| chat-service | GET | `/api/web/v1/chats` | — | 200 |
| chat-service | GET | `/api/web/v1/screener-templates` | — | 200 |
| chat-service | GET | `/api/web/v1/screener-templates/{id}` | — | 200 |
| chat-service | GET | `/api/web/v1/screeners` | — | 200 |
| chat-service | GET | `/api/web/v1/templates` | type=suggested | 200 |
| clickhouse-api | GET | `/api/web/v1/dealer-positioning/{ticker}` | — | 200 |
| clickhouse-api | GET | `/api/web/v1/gamma-insights/{ticker}` | limit | 200 |
| clickhouse-api | GET | `/api/web/v1/gamma-insights/{ticker}/expirations` | frequency | 200 |
| clickhouse-api | GET | `/api/web/v1/gamma-levels/{ticker}/intraday` | — | 200 |
| clickhouse-api | GET | `/api/web/v1/gamma-levels/{ticker}/{frequency}` | eod|intraday | 200 |
| clickhouse-api | GET | `/api/web/v1/levels-report` | — | 404 |
| clickhouse-api | GET | `/api/web/v1/market-status/{exchange}` | — | 200 |
| clickhouse-api | GET | `/api/web/v1/metrics/{ticker}/eod?fields=option&fields=momentum&fields=volatility&fields=seasonality&limit=30` | — | 200 |
| clickhouse-api | GET | `/api/web/v1/metrics/{ticker}/intraday` | fields=option&fields=volatility&limit=30 | 422 |
| clickhouse-api | GET | `/api/web/v1/metrics/{ticker}/{frequency}` | fields,limit | 200 |
| clickhouse-api | GET | `/api/web/v1/options/matrix/{ticker}` | frequency | 200 |
| clickhouse-api | GET | `/api/web/v1/options/put-call-ratio/{ticker}` | — | 200 |
| clickhouse-api | GET | `/api/web/v1/price-ratios` | — | 405 |
| clickhouse-api | GET | `/api/web/v1/prices` | tickers | 200 |
| clickhouse-api | GET | `/api/web/v1/screeners` | columns,tickers | 200 |
| clickhouse-api | GET | `/api/web/v1/screeners/columns` | — | 200 |
| clickhouse-api | GET | `/api/web/v1/screeners?columns={columns}&tickers={tickers}` | columns=name,quote_type,sector,industry,market_cap,volume&tickers=SPX,SPY,QQQ,NVDA,TSLA,AAPL,MSFT,AMZN,META,GOOGL | 200 |
| clickhouse-api | GET | `/api/web/v1/tickers` | — | 200 |
| clickhouse-api | GET | `/api/web/v1/tickers/{ticker}/candles` | interval,from,to,countBack | 200 |
| clickhouse-api | GET | `/api/web/v1/tickers/{ticker}/tradingview` | — | 200 |
| clickhouse-api | GET | `/api/web/v1/volatility-insights/{ticker}` | — | 200 |
| dashboard | GET | `/api/auth/session` | — | 200 |
| qbot-service | GET | `/api/web/v1/assets` | — | 200 |
| qbot-service | GET | `/api/web/v1/company-news` | ticker,date,number | 200 |
| qbot-service | GET | `/api/web/v1/events` | ticker,kind,start_date,end_date | 200 |
| user-service | GET | `/api/web/v1/user-preferences` | type | 200 |
| user-service | GET | `/api/web/v1/users/me` | — | 200 |
| user-service | GET | `/api/web/v1/watchlists` | — | 200 |

## Notes from probing

- `metrics/{ticker}/eod` accepts `fields=option|momentum|volatility|seasonality` (+`limit`); `metrics/{ticker}/intraday` only accepts literal fields `iv_1m_50d, iv_3m_50d, iv_0dte_50d, skew_1m, skew_3m, skew_0dte` (30-min bars).
- `tickers/{ticker}/candles` requires `from`/`to` (ms epoch) + `countBack`; `interval` is case-sensitive: `1m..45m, 1h..4h, 1D, 1W, 1M`.
- `options/put-call-ratio/{ticker}` requires `frequency=eod|intraday`; returns latest snapshot only.
- `dealer-positioning/{ticker}` → 200 (net_gex/net_dex, DTE buckets).
- `market-status/{exchange}` supports NYSE, NASDAQ only (others 404).
- `price-ratios` → 405 on GET (likely POST-only); `levels-report` → 404 (dead/renamed).
- `prices` and `screeners` accept comma-separated `tickers` batches.
- Classic account area (`menthorq.com/account/`) is server-rendered WordPress, no JSON API; new data platform is the gateway above.