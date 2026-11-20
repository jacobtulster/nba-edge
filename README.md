# NBA Edge

A shared website that updates itself with **model win probabilities**, **sportsbook prices**, and **expected value (EV)**.

You and your friend just open the link. No Colab. No manual refresh every hour.

## How to use it

1. Open the GitHub Pages URL for this repo
2. Read the board

The model shows **likelihoods**, not guaranteed winners.  
**EV** = model probability × decimal odds − 1 (best available US book moneyline).

## What runs in the background

Every hour from **8:00 AM to 11:00 PM Eastern**:

1. Update the games database (BallDontLie)
2. Train/score Model B (moneyline)
3. Pull live odds (The Odds API)
4. Publish `docs/ev_board.json` to the website

Overnight hours are skipped on purpose.

## One-time setup

### 1. Put this on GitHub

Create a repo, push this project, and invite your friend as a collaborator if you want.

### 2. Add API keys (Secrets)

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret name | Where to get it |
|-------------|-----------------|
| `BALLDONTLIE_API_KEY` | https://app.balldontlie.io/account |
| `ODDS_API_KEY` | https://dash.the-odds-api.com/ |

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
- v1 is **NBA moneyline EV only** (Model B from the Colab research).
- NHL / player props can come later.
