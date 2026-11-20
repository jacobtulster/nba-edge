function pct(value) {
  if (value == null || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function odds(value) {
  if (value == null || Number.isNaN(value)) return "—";
  return Number(value).toFixed(2);
}

function evText(value) {
  if (value == null || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(1)}%`;
}

function evClass(value) {
  if (value == null || Number.isNaN(value)) return "";
  return value > 0 ? "ev-pos" : "ev-neg";
}

function topSide(game) {
  if (!game.best_side || game.best_ev == null) return "—";
  const team =
    game.best_side === "home"
      ? game.home_abbreviation
      : game.away_abbreviation;
  const hot = game.best_ev > 0 ? " hot" : "";
  return `<span class="pill${hot}">${team} · ${evText(game.best_ev)}</span>`;
}

async function loadBoard() {
  const meta = document.getElementById("meta");
  const rows = document.getElementById("rows");
  const footnote = document.getElementById("footnote");

  try {
    const response = await fetch(`./ev_board.json?t=${Date.now()}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    meta.textContent = data.generated_at_et
      ? `Updated ${data.generated_at_et} · ${data.game_count || 0} games · trained on ${data.training_games || 0} games`
      : "Board not generated yet — waiting for the first hourly run.";

    footnote.textContent = data.note || "";

    if (!data.games || data.games.length === 0) {
      rows.innerHTML =
        '<tr><td colspan="7">No upcoming games on the board right now.</td></tr>';
      return;
    }

    rows.innerHTML = data.games
      .map((game) => {
        return `<tr>
          <td class="matchup">${game.away_abbreviation} @ ${game.home_abbreviation}</td>
          <td>${pct(game.home_win_probability)}</td>
          <td>${odds(game.home_decimal)}</td>
          <td class="${evClass(game.home_ev)}">${evText(game.home_ev)}</td>
          <td>${odds(game.away_decimal)}</td>
          <td class="${evClass(game.away_ev)}">${evText(game.away_ev)}</td>
          <td>${topSide(game)}</td>
        </tr>`;
      })
      .join("");
  } catch (error) {
    meta.textContent = "Could not load the board.";
    rows.innerHTML = `<tr><td colspan="7">${error.message}</td></tr>`;
  }
}

loadBoard();
