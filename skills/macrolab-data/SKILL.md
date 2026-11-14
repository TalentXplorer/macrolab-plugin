---
name: macrolab-data
description: Analyse Korean and US macro data from Macro Lab (macrolab.kr) — interest rates, inflation, growth, money, credit, FX, stocks, commodities, housing, sentiment, AI and startup series, monthly since 2001 plus daily twins, and Seoul apartment sales by complex (단지별 실거래, 2006 on). Use when a question needs Korean/US economic time series (금리·물가·성장·환율·주가·부동산 등), one Seoul apartment complex's prices, a relationship between two indicators, where an indicator stands today, or a chart/table from this data. Reads the public-licence data through the Macro Lab MCP tools (members; OAuth).
---

# Macro Lab data

Macro Lab (macrolab.kr) collects Korean and US macro series from ECOS (한국은행), FRED, 한국부동산원 (R-ONE) and 국토교통부 실거래가,
and opens the **public-licence part** of it to its members' AI agents through its MCP server (the server signs the
member in through OAuth the first time an agent connects). This skill tells you how to get the data, how to read each series without
misreading it, and how to report what you find.

What you get, through the MCP tools: the monthly panel (one value per series per month, `YYYY-MM`, 2001-01 onward), the data dictionary
(what every series is), public daily / weekly twins of the headline series (US Treasury yields, the Fed funds rate, oil, the dollar,
Korean rates, the won, the KOSPI …), every Bank of Korea monetary policy board and FOMC rate decision since 2001, holds included, and the
국토교통부 apartment sales of every Seoul complex since 2006 (per month and size type: the count, the median, the median per ㎡, plus the latest
individual sales). The panel is rebuilt monthly, the daily data twice a day, the apartment sales daily. Every call answers a capped window —
there is no bulk download.

What you do NOT get: Macro Lab's models, rules, forecasts and track record, derived variables, and series whose owner restricts
redistribution (Nasdaq, Cboe VIX, Moody's, Coinbase, U. Michigan, individual stock prices). Do not claim any of those from this data.

## 1. Get the data

Use the MCP tools in this order — `list_datasets` (what exists, the rules, the daily ids) → `search_variables` (ids by Korean or English
words, group or country; when no variable holds your words it tries related ones and its `hint` says what to try next) → `get_series` for monthly values, `get_daily` for daily twins, `latest` for "지금", `describe_variable` for one
series in full. Every call is capped (12 ids × 600 months, 8000 cells; 8 daily ids × 600 rows), so ask for the window the question needs:
the last 120 months by default, `from`/`to` or `last` to move. The resources `macrolab://dictionary.json` (every series' entry) and
`macrolab://series/<id>.csv` (one series' history) give one piece at a time.

Do not copy rows out of a tool answer to calculate with them — let the server calculate: `compute` resamples (daily → weekly or
monthly), transforms (`diff`, `pct`, `log`, `yoy_pct`, `yoy_diff`, or `auto` = the dictionary's unit), and returns summary statistics, a
correlation matrix with leads and lags (`max_lag`), an OLS with Newey–West t (`regress`, x lagged by `lag`) or event windows (`events:
bok_mpc` / `fomc`, optionally `decision: hold`, or your own `event_dates`) — small answers whatever the history length. `get_decisions`
lists the BOK and FOMC decisions themselves (a hold leaves no trace in the rate series). With `get_daily`, `align: common` keeps only
the dates every requested series has.

One Seoul apartment complex: `find_apartments` (part of the name in Korean — 은마, 헬리오시티, 잠실주공5단지; or a 구 / 법정동 alone for that
area's most traded complexes) gives its id, the 동, the year built and the size types sold; `get_apartment_trades` (the id; `area` = one size
type, `from`/`to`, `period` month · quarter · year, `sales` = how many of the latest individual sales to list, 0–200) gives the table and the
latest sales. To compare complexes, pass up to ten in `ids` instead of `id`: one table and one sales list with an id column (3 latest sales
each unless `sales` says otherwise) — compare the same size type.

If you can run code (Claude Code, Codex, a notebook), keep what a tool answered in a local file for the session and calculate there when
`compute` does not cover it — fetch the series and the window the question needs, not the whole panel. If the server answers 401, the user
connects Macro Lab once (macrolab.kr → sign in → 「AI 연결」); never ask the user for a password or a token.

## 2. Read a column right

Read the dictionary entry of every series **before** you compute anything (`search_variables` lists the key fields, `describe_variable`
gives one in full, the resource `macrolab://dictionary.json` all of them). Each entry has:

- `label` / `label_en`, `group` (금리·물가·성장·통화·유동성·신용·외환·주식·원자재·대체자산·부동산·심리·AI·스타트업), `country` (KR, US, GL = global
  markets and commodities, JP, DE, CN), `description` (the source table and how the value is taken: month-end close, monthly average, YoY …).
- `unit` — how an h-month change of the series is measured: `pct` (an index or price: use **% changes**, never differences of the level),
  `bp` (an interest rate in %: changes in **basis points** = difference × 100), `level` (everything else: the difference in its own unit;
  `unit_label` says `%p` when the level is already a percentage). `is_index` = true means the level drifts: analyse growth rates.
- `nature` — `trend` (a drifting level: prices, indices, counts), `rate` (a yield-like level: interest rates, YoY inflation / growth / M2),
  `stationary` (fluctuates around a long-run level: spreads, sentiment surveys, unemployment, ratios). It tells you the honest benchmark
  for any forecast: a random walk for `rate`, the harder of random walk and drift for `trend`, mean reversion for `stationary`.
- `outcome` — false means the series is **explanatory only** (already a YoY rate stored as an input, or a policy index). Never use it as a
  thing to be explained or forecast. `policy` = true marks the Korean housing-tax stance indices (`kr_tax_*`): explanatory only.
- `index_of` — a YoY column's index twin (`inflation` → `kr_cpi`, `growth` → `kr_ip`, `liquidity` → `kr_m2`, `fx` → `usdkrw`, `hh_loans_yoy` →
  `hh_loans`). When you want the level, use the twin; when you want the rate, use the YoY column — do not compute a YoY of a YoY.
- `first`, `last`, `months`, `missing` — coverage. Many series start after 2001; a quarterly source is placed monthly with its publication
  lag and carried; the last one or two months of a slow source can be empty. Say the sample you actually used.
- `source` (FRED series page or ECOS table), `construction` (how the builder made the column), `licence` (`attribution` entries carry the
  line you must print; `public` needs no line), `daily_twin` (the `get_daily` id of the same quantity at daily frequency).

Facts about the panel as a whole: values are the **current vintage** (revised data, not what was known at the time — a backtest on them is
exploratory); `kr_eq` / `us_eq` are OECD share-price indices (2015 = 100, monthly averages), not KOSPI / S&P 500 (`kospi` is the KOSPI
month-end close); `kr_apt_*` 실거래 columns are contract-based with composition not held fixed; FX is 원/달러 (a rise = a weaker won).

Apartment sales by complex (`get_apartment_trades`):

- 매매 only, cancelled (해제) deals left out; Seoul's 25 districts, 2006-01 on. Each listed sale says `deal`: brokered (중개거래) or direct
  (직거래) — the portal marks it from 2021-11 on, so earlier sales have none. Without `deal` the table counts brokered sales (unmarked ones
  included, as the panel's `kr_apt_*` columns do) and the list shows every sale; `deal: direct` or `all` when the question is about 직거래.
  직거래 are often between relatives and below the market: never read one as the complex's price, and say which kind a number is.
- `area` is the exclusive area (전용면적) cut to a whole ㎡ — 84 = 84.00–84.99㎡, the type sold as 34평 — never the supply area (공급면적). Prices are
  in 만원 (10,000 KRW), nominal; `ppsm` is the median 만원 per ㎡ of exclusive area.
- A month's median is the median of that month's sales: a few sales, or a different floor or size mix, move it. Read a trend by quarter or year
  within one size type, and give the number of sales next to every median.
- A sale is reported within 30 days of the contract: the months from `reporting_from` on are still being filled — their counts can grow. Say so
  when you use them.
- No 동·호수, address or party to a sale is in the data; the floor is. A rebuilt complex has a new name and id (둔촌주공 → 올림픽파크포레온): the
  old and the new are different complexes.

Daily data (`get_daily`): `date` = `YYYY-MM-DD`, one column per daily id, blank where a series has no observation that day (weekends,
holidays, weekly series; `align: common` keeps only the dates every requested series has). A daily twin is the same quantity as its panel series (`DGS10` ↔ `us10y`, `KR_CD91` ↔ `cd`, `KR_KOSPI` ↔ `kospi`), so the monthly
value is an average or month-end of it as the description says.

## 3. Analyse

- Work in the unit the dictionary gives (% change of an index, bp change of a rate, difference of a level). State the horizon (h months).
- A relationship between X and Y: X's state at t (its level, or its h-month change) against Y's change over the **next** h months. Report
  the sample period, the number of non-overlapping observations (overlapping monthly changes inflate t-statistics: count every h-th month
  or use HAC errors and say so), the sign, the size per one standard deviation of X in Y's unit, and whether it holds in the first and
  second halves of the sample. A relationship that holds only in one era is reported as that, not as a law.
- Compare any forecast with the series' benchmark (`nature`). Being better than nothing is not the bar; beating the random walk is.
- Regimes: split by the economy of Y (Korean Y → ESI · BSI · CCSI, 소비자물가, 기준금리; US Y → 미시간 심리 (not served) / US CPI / Fed funds).
  Never apply a Korean regime to a US outcome.
- Do not fill gaps silently, do not extrapolate a missing month, do not rebuild a restricted series from public ones.
- "지금": the monthly panel ends with the last complete month; `latest` / `get_daily` give today's level of the headline series. Say which
  date each number is from. A daily value older than ~10 days is stale — fall back to the panel month and say so. The tools add a series'
  months after its last panel value from its daily twin when they are already in (`from_daily`, or a `#` line under the CSV): say that
  those months come from the daily data.

## 4. Say it right

- A result is a **relationship with its sample and condition**, never a cause: "관계가 성립했다", not "때문에". Say sign and significance
  apart. |t| < 2 is "뚜렷한 관계가 안 보였다", never "관계가 없다".
- Korean terms follow Bank of Korea / KDI paper usage: 모형 (not 모델), 예측력 (for skill), 전년동월비 (YoY), 임의보행 대비 예측력, 예측시계 (horizon),
  설명변수 (regressor), 표본외 예측 (out of sample), 유의 (significant), 방향성 적중률 (hit rate), 공표시차 (publication lag). The gap between two
  percentages is %p (pp in English). Hedge estimates ("~것으로 추정됩니다"), forecasts ("~할 것으로 예측됩니다"), interpretations ("~로 보입니다").
- Neutral wording: direction and size, never 호재 / 악재 / 부담. Nothing from this data is investment advice; say so once when you give a
  forecast or a portfolio-like conclusion.
- Under every chart or table that shows an attribution-licence series, print its `licence.attribution` line (e.g. "출처: BIS",
  "출처: 국토교통부 실거래가 공개시스템 (공공누리 제1유형)"). Credit Macro Lab (macrolab.kr) as the compiler.
- Numbers: 2 decimals for t, the series' own precision otherwise; dates as `YYYY-MM` (monthly) or `YYYY-MM-DD` (daily).

## 5. Don't

- Don't invent values, ids or dates. If an id is not in the dictionary, it is not in the data.
- Don't present Macro Lab's models, verdicts or forecasts as if they were in this data — they are not. Point to macrolab.kr for those.
- Don't call a complex's median sale price its 시세 or the value of a unit: it is what sold, in that window.
- Don't republish the data as your own dataset or hand it to a third party; credit the sources as in §4.
