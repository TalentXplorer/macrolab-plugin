# Macro Lab plugin — Korean & US macro data for your AI

Macro Lab (macrolab.kr) opens the public-licence part of its macro data to its members' AI agents: 200+ monthly series for Korea, the US
and global markets since 2001 (ECOS, FRED, 한국부동산원 R-ONE, 국토교통부 실거래가) plus public daily twins — without applying for an API key at
any of those sources. Membership is free (Google or Kakao sign-in at https://macrolab.kr); the server asks your agent to sign you in once
(OAuth) the first time it connects. This plugin gives
Claude Code, Codex and ChatGPT two things at once:

- the **Macro Lab MCP server** (`https://macrolab.kr/mcp`, read-only, members only — OAuth): `list_datasets`, `search_variables`, `describe_variable`,
  `get_series`, `get_daily`, `latest`, `compute` (statistics computed on the server: changes, correlations, regressions, event windows),
  `get_decisions` (Bank of Korea and FOMC rate decisions since 2001, holds included), and resources (`macrolab://dictionary.json`, `macrolab://series/<id>.csv`);
- the **macrolab-data skill**: how to pull the files (`scripts/pull.py`, standard library only), how to read each column (unit, nature,
  explanatory-only series, index twins, coverage, licence) and how to report a result without over-claiming.

## Install

Claude Code:

```
/plugin marketplace add TalentXplorer/macrolab-plugin
/plugin install macrolab@macrolab
```

Codex:

```
codex plugin marketplace add TalentXplorer/macrolab-plugin
codex plugin add macrolab
```
or install **Macro Lab** from `/plugins` (or the Plugins tab of the ChatGPT desktop app).

MCP server only, without the plugin (then `/mcp` → Authenticate in Claude Code, `codex mcp login macrolab` in Codex — a browser window signs
you in to Macro Lab and asks you to allow the connection):

```
claude mcp add --transport http macrolab https://macrolab.kr/mcp
codex mcp add macrolab --url https://macrolab.kr/mcp
```

Claude app (web, desktop, mobile): Customize → Connectors → Add custom connector → `https://macrolab.kr/mcp` → Add → sign in to Macro Lab →
Allow. Members find every route, with one-click links, under 「AI 연결」 in the header of https://macrolab.kr.

## Files only (no plugin)

The files need a 연결 키 (a bearer token, valid a year): sign in at https://macrolab.kr, press 「AI 연결」 in the header, 「연결 키 만들기」.

```
curl -sL -H "Authorization: Bearer $MACROLAB_TOKEN" https://macrolab.kr/data/manifest.json   # what exists, immutable file URLs
MACROLAB_TOKEN=<key> python3 skills/macrolab-data/scripts/pull.py                            # → ./.macrolab/panel.csv, dictionary.json, daily.csv, README.md
```

Stable addresses: `https://macrolab.kr/data/latest/panel.csv` (redirects to the current version) — send the same header from DuckDB (`httpfs`
bearer secret) or pandas.

## What this plugin runs, sends and fetches

Nothing runs at install. The plugin adds two things to your agent:

- an **MCP server entry** for `https://macrolab.kr/mcp`: your agent sends JSON-RPC requests there (tool names and their arguments — variable
  ids, date windows) and receives public macro data back. The first call answers 401 with the server's OAuth discovery document; your agent
  then opens a browser window where you sign in to Macro Lab and allow the connection, and keeps the access and refresh tokens it is given
  (the server stores nothing about the connection). No cookie, no personal data in the requests; the server logs the request line (address,
  path, status), the client's name at `initialize` and the tool names, never the arguments and never who you are.
- a **skill** (`skills/macrolab-data/SKILL.md`) with one script, `scripts/pull.py`, that your agent runs only when you ask it to pull the files:
  it fetches `https://macrolab.kr/data/manifest.json` and the files it lists with your 연결 키 (`MACROLAB_TOKEN` or `--token`) in the
  Authorization header, verifies them by sha256 and writes them to a cache folder (`./.macrolab` by default, `MACROLAB_CACHE` or `--dir`
  otherwise) with a `.gitignore`. Standard library only, no other host is contacted, nothing is sent except the GET requests and that header.

No hooks, no executables, no credentials, no third-party packages.

## Licence

Plugin code: MIT. Data: public-domain and attribution-licence series only; the attribution lines are in `dictionary.json` and the
snapshot's `README.md` — print them under a published chart or table. Series whose owner restricts redistribution are not served.
Nothing here is investment advice. Macro Lab's models, rules and track record are not part of the data.
