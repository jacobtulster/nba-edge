# NBA Edge

A shared website that updates itself with **model cover probabilities**, **sportsbook spreads**, and **expected value (EV)**.

You and your friend just open the link. No Colab. No manual refresh every hour.

## How to use it

1. Open the GitHub Pages URL for this repo
2. Read the **ATS** board (primary) and the **Moneyline** bonus tab under ROI

The model shows **likelihoods**, not guaranteed covers.  
**ATS EV** = cover_prob × decimal odds − 1 (best available US **spread**).  
**Moneyline** is logged separately as a bonus book — never mixed into ATS ROI.

Each hourly run auto-logs +EV ATS (and +EV ML) topsides into `docs/picks.json`, grades them when games finish, and updates each book’s equity curve.

## What runs in the background

Every hour from **8:00 AM to 11:00 PM Eastern**:

1. Update the games database (BallDontLie)
2. Train/score Model B (win prob → spread cover)
3. Pull live spreads + moneylines (The Odds API)
4. Publish `docs/ev_board.json` + `docs/picks.json`

Overnight hours are skipped on purpose.

## One-time setup

### 1. Put this on GitHub

Create a repo, push this project, and invite your friend as a collaborator if you want.

### 2. Add API keys (Secrets)

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret name | Where to get it |
|-------------|-----------------|
| `BALLDONTLIE_API_KEY` | https://app.balldontlie.io/account |
| `ODDS_API_KEY` | https://dash.the-odds-api.com/ (spreads + moneylines) |

### 3. Turn on GitHub Pages

Repo → **Settings** → **Pages**

- Source: **Deploy from a branch**
- Branch: `main` (or `master`)
- Folder: `/docs`

Your site will be: `https://<your-username>.github.io/<repo-name>/`

### 4. First run (optional but recommended)

Repo → **Actions** → **NBA Edge hourly pipeline** → **Run workflow**

After that, the hourly schedule keeps the board fresh.

## Run locally (optional)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# put your keys in .env

python scripts/pipeline.py --force
```

Then open `docs/index.html` or serve the `docs/` folder.

## Notes

- Free API quotas still apply. Incremental refreshes keep usage down.
- Primary book is **NBA ATS / spreads**; moneyline is a **bonus** ledger (Model B from the Colab research).
