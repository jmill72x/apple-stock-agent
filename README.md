# apple-stock-agent

An OpenClaw agent that watched Apple's refurbished Mac mini inventory until it found the machine it was looking for. Retired July 2026. Mission complete.

## The problem

Apple pulled the 32GB configuration from the new Mac mini lineup during the 2026 memory shortage, and refurbished units surfaced unpredictably and sold out fast. I needed to know within 15 minutes of a qualifying unit appearing, without checking a webpage 40 times a day.

## How it ran

A cron job every 15 minutes, 8am to 10pm Eastern (nobody buys a refurb at 3am), each run in an isolated session with a model fallback chain. Failure alerts only fired after 3 consecutive misses with a one-hour cooldown, so a single flaky run never paged me. Silent unless something qualified.

## Alert logic

- First time an item is seen in stock: alert
- Back in stock after going out of stock: alert
- Still in stock 7 days after the last alert: reminder
- Everything else: silence

## Version history, which is where the lessons are

**v1: prompt-driven, web_fetch.** The agent read a markdown skill file and fetched the refurb page directly. Apple's page is heavily JS-rendered, so fetches came back empty and runs blew through a 120-second timeout.

**v2: prompt-driven, web_search.** Rewrote the skill to use search with site-scoped queries and a 300-second timeout. It worked, and found five qualifying listings on its first clean run. But results were nondeterministic and the model occasionally freelanced on formatting and delivery.

**v3: deterministic Python.** The current version. Regex extraction against the page, a JSON state file implementing the alert logic above, and the LLM reduced to a thin wrapper that runs the script and delivers output. Timeouts stopped mattering and behavior became identical every run.

The lesson: use the model where judgment is required, and code where it is not. The agent's job shrank as the script got better. That is the point.

## Side quest

Midway through its life the agent picked up a second target, the Aqara U400 smart lock, using button-state detection (Sold Out vs Add to Bag) rather than listing regex. One trap worth documenting: Apple's pages contain generic "unavailable" text in store-pickup messaging even when an item is in stock, so matching on that produces false negatives. Match the button.

## Files

- `apple_stock_check.py`: the v3 script
- `skill.md`: the wrapper skill the cron invoked
- `cron-config.json`: the sanitized OpenClaw cron job definition
- `docs/skill-v2.md`: the v2 prompt-driven skill, for the version history

## Outcome

It found an M4 Mac mini with 32GB. I bought it. The successor now runs Claude Code on that machine, and this agent gets an archive banner.
