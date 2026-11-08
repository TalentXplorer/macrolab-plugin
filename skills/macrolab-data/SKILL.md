---
name: macrolab-data
description: Analyse Korean and US macro data from Macro Lab (macrolab.kr) — interest rates, inflation, growth, money, credit, FX, stocks, commodities, housing, sentiment, AI and startup series, monthly since 2001 plus daily twins. Use when a question needs Korean/US economic time series (금리·물가·성장·환율·주가·부동산 등), a relationship between two indicators, where an indicator stands today, or a chart/table from this data. Pulls the public-licence files with scripts/pull.py (no dependencies) or reads them through the Macro Lab MCP tools.
---

# Macro Lab data

Macro Lab (macrolab.kr) collects Korean and US macro series from ECOS (한국은행), FRED, 한국부동산원 (R-ONE) and 국토교통부 실거래가,
and opens the **public-licence part** of it to its members' AI agents as files and as MCP tools (membership is free; the MCP server signs
the member in through OAuth the first time an agent connects, the files take a 연결 키 the member makes at macrolab.kr → 「AI 연결」).
This skill tells you how to get the data, how to read each column without misreading it, and how to report what you find.

What you get: `panel.csv` (one row per month, `date` = `YYYY-MM`, one column per series; 2001-01 onward), `dictionary.json` (what every
column is), `daily.csv` (public daily / weekly twins of the headline series: US Treasury yields, the Fed funds rate, oil, the dollar,
Korean rates, the won, the KOSPI …), `policy_decisions.csv` (every Bank of Korea monetary policy board and FOMC rate decision since 2001,
holds included) and `README.md` (licence, attribution). The snapshot is rebuilt monthly for the panel and twice a day
for the daily file; the files are immutable per version and `manifest.json` lists the current versions.

What you do NOT get: Macro Lab's models, rules, forecasts and track record, derived variables, and series whose owner restricts
redistribution (Nasdaq, Cboe VIX, Moody's, Coinbase, U. Michigan, individual stock prices). Do not claim any of those from this data.

## 1. Get the data

**You can run code (Claude Code, Codex, Cursor, a notebook):** pull the files once, then work on them locally.

```bash
MACROLAB_TOKEN=<key> python3 scripts/pull.py   # → ./.macrolab/panel.csv, dictionary.json, daily.csv, policy_decisions.csv, README.md, manifest.json
python3 scripts/pull.py --check                # what would change, without downloading
```

The key is the user's Macro Lab 연결 키 (macrolab.kr → sign in → 「AI 연결」 → 「연결 키 만들기」; valid a year). If `MACROLAB_TOKEN` is not
set and the server answers 401, ask the user for the key rather than guessing one — never put a key into a file that is committed.

`pull.py` is in this skill's `scripts/` folder — in Claude Code at `${CLAUDE_PLUGIN_ROOT}/skills/macrolab-data/scripts/pull.py`, elsewhere next
to this SKILL.md; without the plugin, `curl -fsSO https://macrolab.kr/data/pull.py`. Standard library only, Python ≥ 3.8. It downloads only files whose sha256 changed since
the last pull, verifies every file, writes a `.gitignore` in the cache folder and prints the paths. The cache is `./.macrolab/` under the
current directory (set `MACROLAB_CACHE` or `--dir` for another place, e.g. `~/.cache/macrolab` shared across projects). Re-running it
in a new session costs one small request when nothing changed — never re-download by hand.

Then, for example:

```python
import pandas as pd, json
panel = pd.read_csv('.macrolab/panel.csv', parse_dates=['date']).set_index('date')
dic = {v['id']: v for v in json.load(open('.macrolab/dictionary.json', encoding='utf-8'))['variables']}
```

One-off question without a cache — DuckDB reads straight from the stable address (it follows the redirect to the current version):

```sql
SELECT date, cd, ktb3y, us10y FROM read_csv_auto('https://macrolab.kr/data/latest/panel.csv') WHERE date >= '2020-01' ORDER BY date;
```

**You cannot run code (a chat app with the Macro Lab connector):** use the MCP tools in this order — `list_datasets` (what exists, the
rules) → `search_variables` (ids by Korean or English words, group or country) → `get_series` for monthly values, `get_daily` for daily
twins, `latest` for "지금", `describe_variable` for one column in full. Every call is capped (12 ids × 600 months, 8000 cells), so ask for
windows: the last 120 months by default, `from`/`to` or `last` to move. The resources `macrolab://dictionary.json` and `macrolab://series/<id>.csv`
give one file at a time.

Do not copy rows out of a tool answer to calculate with them — let the server calculate: `compute` resamples (daily → weekly or
monthly), transforms (`diff`, `pct`, `log`, `yoy_pct`, `yoy_diff`, or `auto` = the dictionary's unit), and returns summary statistics, a
correlation matrix with leads and lags (`max_lag`), an OLS with Newey–West t (`regress`, x lagged by `lag`) or event windows (`events:
bok_mpc` / `fomc`, optionally `decision: hold`, or your own `event_dates`) — small answers whatever the history length. `get_decisions`
lists the BOK and FOMC decisions themselves (a hold leaves no trace in the rate series). With `get_daily`, `align: common` keeps only
the dates every requested series has.

## 2. Read a column right

Open `dictionary.json` **before** you compute anything. Each entry has:

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
  line you must print; `public` needs no line), `daily_twin` (the id in `daily.csv` for the same quantity at daily frequency).

Facts about the panel as a whole: values are the **current vintage** (revised data, not what was known at the time — a backtest on them is
exploratory); `kr_eq` / `us_eq` are OECD share-price indices (2015 = 100, monthly averages), not KOSPI / S&P 500 (`kospi` is the KOSPI
month-end close); `kr_apt_*` 실거래 columns are contract-based with composition not held fixed; FX is 원/달러 (a rise = a weaker won).

Daily file: `date` = `YYYY-MM-DD`, one column per daily id, blank where a series has no observation that day (weekends, holidays, weekly
series). A daily twin is the same quantity as its panel series (`DGS10` ↔ `us10y`, `KR_CD91` ↔ `cd`, `KR_KOSPI` ↔ `kospi`), so the monthly
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
- "지금": the monthly panel ends with the last complete month; `latest` / `daily.csv` give today's level of the headline series. Say which
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
- Don't send the cached files to a third party or republish them as your own dataset; the licence note in `README.md` applies.
