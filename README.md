# Internship job watcher

Polls **171** public job-board feeds for internship-related titles, remembers what you've already seen in **SQLite**, and sends **Telegram** notifications for new US-matching postings (see `config.json` for keywords and filters). Runs for free, 24/7, on **GitHub Actions** — no server required.

A companion webapp (`webapp/`, deployed separately) lets you browse tracked companies, mark applications, track OA/interview deadlines, and tailor your resume.

---

## Setting this up for yourself

This is a from-scratch setup guide — follow it top to bottom on a fresh fork/clone.

### 1. Fork and clone

```bash
git clone https://github.com/<your-username>/Job_Notifier.git
cd Job_Notifier
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install --with-deps chromium   # needed for ~13 JS-rendered career sites
```

### 2. Create your own Telegram bot

1. Open a chat with [@BotFather](https://t.me/BotFather) in Telegram, send `/newbot`, and follow the prompts. You'll get a **bot token** (looks like `123456789:AAH…`).
2. Get your numeric **chat ID** — message [@userinfobot](https://t.me/userinfobot) or [@getidsbot](https://t.me/getidsbot) and it replies with your user id. (Or add the bot to a group and use that group's id — group ids are usually negative.)
3. Open a private chat with your new bot and tap **Start** so it's allowed to message you.

### 3. Configure secrets locally

```bash
cp .env.example .env
```

Edit `.env`:

```env
TELEGRAM_BOT_TOKEN=paste_token_from_botfather
TELEGRAM_CHAT_ID=paste_numeric_chat_id

# Optional — only needed for the NASA source, get a free key at https://developer.usajobs.gov/apirequest/
USAJOBS_API_KEY=
USAJOBS_USER_AGENT=your.email@example.com
```

`.env` is git-ignored — never commit it.

### 4. Test locally

```bash
.venv/bin/python main.py --once
```

This does a single poll of all 171 sources (~20–25 minutes, mostly HTTP requests plus Playwright for the JS-heavy sites) and messages you for every internship-matching posting found. **The first run will likely send a lot of messages** since `state.db` starts empty and everything looks "new" — that's expected. After that, only genuinely new postings per source trigger a message.

### 5. Run it 24/7 for free (GitHub Actions — recommended)

No VM, no always-on laptop required. The included workflow (`.github/workflows/watch.yml`) polls every 30 minutes and persists `state.db` back into the repo between runs.

1. Push your fork to GitHub (if you haven't already).
2. Repo → **Settings → Secrets and variables → Actions → New repository secret**, add:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `USAJOBS_API_KEY` / `USAJOBS_USER_AGENT` (optional, only for NASA)
3. Repo → **Settings → Actions → General → Workflow permissions** → select **Read and write permissions** (the workflow commits the updated `state.db` after each run).
4. Repo → **Actions** tab → run **"Internship watcher poll"** once manually (`Run workflow`) to seed `state.db`, or just wait for the next scheduled run.

That's it — it now runs indefinitely on GitHub's infrastructure, even with your laptop off.

### 6. (Alternative) Self-hosted VM

If you'd rather run it on your own always-on machine instead of GitHub Actions, see **[`deploy/oracle/STEPS.txt`](deploy/oracle/STEPS.txt)** for a full Oracle Cloud Always-Free walkthrough with `systemd`. Not required if you're using GitHub Actions.

---

## Configuration

- **`config.json`** — the 171 sources (`sources`), poll interval, title keywords (`intern`, `internship`, `student`), and `location_filter` (`countries: ["US"]`) with heuristics in `main.py`.
- **`scripts/build_config.py`** — regenerates `config.json` from the `SOURCES` list in that script. Edit sources there, then run:

  ```bash
  .venv/bin/python scripts/build_config.py
  ```

- Fetcher types supported (see `main.py`): `workday`, `greenhouse`, `lever`, `ashby`, `smartrecruiters`, `workable`, `pcsx`, `google_careers`, `amazon`, `oracle_careers`, `usajobs`, `phenom`, `successfactors`, `avature`, and `playwright` (custom browser-driven scrapers in `scripts/playwright_fetch.py` for bot-protected/JS-only sites like Apple, Meta, Tesla, Wells Fargo, etc.).
- **`scripts/ats_detect.py`**, **`scripts/discover_*.py`**, **`scripts/probe_*.py`** — one-off tools used to find/verify each company's ATS and slug when adding new sources or fixing a broken one.

### Customizing the keyword filter (e.g. switching from all-internships to Engineering/CompE-only)

By default this watcher is **not** SWE-specific — `title_keywords` (`intern`, `internship`, `student`) matches *any* internship title at the configured companies (software, hardware, business, finance, marketing, whatever the company happens to post). It just looks tech-heavy because most of the 171 configured companies are tech companies.

To narrow it to a specific discipline, edit `config.json` and add a **`title_require_any`** list. If set, a posting must match `title_keywords` **and** at least one entry in `title_require_any` to trigger a notification — everything else (marketing/finance/business-only internships, etc.) is filtered out.

```json
{
  "title_keywords": ["intern", "internship", "student"],
  "title_require_any": [
    "engineer",
    "engineering",
    "computer engineering",
    "electrical",
    "hardware",
    "firmware",
    "embedded",
    "systems engineer",
    "swe"
  ]
}
```

- Leave `title_require_any` as `[]` (the default) to keep every internship, unfiltered by discipline.
- Matching is case-insensitive substring matching (same rules as `title_keywords`) — so `"engineer"` also matches `"Engineering"`, `"Data Engineer"`, etc. Add/remove terms to taste.
- No restart needed for a local run; for GitHub Actions, just commit and push the change — the next scheduled poll picks it up.
- If you regenerate `config.json` via `scripts/build_config.py`, edit the `title_require_any` line in that script's `CONFIG` dict too so it doesn't get overwritten back to `[]`.

---

## Companion webapp — is it usable by other people?

**Short answer: as deployed at the live URL, no — it's wired to one person's Telegram bot and shared data. To use it yourself, deploy your own copy (10 minutes).**

Longer answer — how the webapp is built:

- **Browsing companies** (`index.html`) is fully static and safe for anyone to view — same `companies.json` for everyone.
- **"Mark applied"** state lives in each visitor's own browser `localStorage`, so that part is already private per-visitor.
- **Telegram sync** (cross-device sync of applied/notes/deadlines, plus the "test message" button) goes through a Vercel serverless proxy (`webapp/api/telegram.js`) that injects **one hardcoded bot token and chat ID from that Vercel project's own environment variables**. Every visitor to the live URL who uses sync is reading/writing the *same* pinned Telegram message and sending messages to the *same* chat — not their own. That's a deliberate simplification (it's built for one person: the deployer) and means it is **not currently multi-tenant**.

To get your own fully private instance of the webapp:

1. Fork `webapp/` (it's its own repo — see `webapp/README.md`) or copy the folder into your own repo.
2. Update `webapp/companies.json` from your `config.json` (`scripts/build_config.py` output already matches it 1:1 in structure).
3. Deploy to Vercel: `cd webapp && npx vercel --prod`.
4. In the Vercel project settings, set **your own** `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` env vars (same bot/chat as step 2/3 above) — this is what makes the sync/test-message features work for *your* Telegram, privately.
5. Optional: set `OPENAI_API_KEY` for the Resume and Recruiter-follow-up tabs.
6. Run `.venv/bin/python scripts/bootstrap_pinned.py` once (from `Job_Notifier`, with your `.env` filled in) to create the pinned sync message your bot and webapp share.

Full details, troubleshooting, and the embed snippet are in [`webapp/README.md`](webapp/README.md).

---

## License / ops

- Never commit `.env` or private SSH keys.
- If self-hosting, ensure outbound HTTPS (443) is allowed to job boards and `api.telegram.org`.
