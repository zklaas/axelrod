# Axelrod

Tests strategies for the **iterated prisoner's dilemma**, after Robert
Axelrod's computer tournaments (1980), his ecological analysis and genetic
algorithm (1984, 1987), and later work on noise.  PyQt6 + Python stdlib.

    axelrod                        the window
    axelrod list                   every strategy with a one-line summary
    axelrod explain tester         full explanation of one strategy
    axelrod run --field first      a tournament in the terminal
    axelrod run --field mine --w 0.99654 --noise 1 --ecology 1000
    axelrod match "tit for tat" joss --turns 100 --noise 1

`run` fields: `first`, `second`, `mine` (both tournaments + the new
strategies), `all`; `--add NAME` adds a strategy.  Common options: `--turns`,
`--w` (random length), `--secret-length`, `--reps`, `--noise` (percent),
`--no-self`, `--payoffs T R P S`, `--seed`.

## The window

* **Strategies** (left): tick entrants, *Copies* enters one several times;
  double-click a name (or select it and press **Details...**)
  for its explanation in a window; double-clicking a standings row does the same.  *Field* loads a line-up with Axelrod's
  settings for it.
* **Guide** (first tab): the game, the tournaments, every strategy, sources.
* **Tournament**: round robin; fixed length (told or not) or random length
  with continuation chance *w* (the matching average length is shown);
  repetitions, noise, payoffs, self-play, seed.  A label names the game the
  payoffs make - every one of the 24 orderings is named, sorted by two
  questions (best reply to a cooperator, T vs R; to a defector, P vs S) and
  then R vs P: prisoner's dilemma, deadlock, chicken / leader / hero,
  anti-coordination, stag hunt, coordination on defection, harmony,
  reversed dilemma, plus turn-taking (2R <= T + S) and ties; the Guide's "When the payoffs are not a prisoner's
  dilemma" explains what changes in each, with results from this program.  Results (standings, pairing heat
  map, notes, CSV export) open in their own window when a run finishes;
  **Show results...** reopens it.
* **Head to head**: one match drawn move by move, with running averages;
  its own fixed or random length, noise and seed.
* **Ecology**: Axelrod's population dynamics on the last tournament's scores.
* **Evolve**: Axelrod's 1987 genetic algorithm (64-entry 3-round lookup
  table + 6-move premise) against the ticked strategies; the result can be
  added to the list (kept in `~/.config/axelrod/bred.json`).  Settings sit
  in a left column beside the how-to text; the chart and the bred table
  (64 readable rows) open in a separate window via **Show results**.  The tab has a
  how-to with advice on choosing settings, and **Load my recipe** reproduces
  the Evolved Reciprocator exactly: the 23 first- and second-tournament
  entries, 60 generations, population 24, 151 moves, mutation 0.01, crossover
  0.6, no noise, seed 4 (the best of seeds 1-4).

## Strategies

* **First tournament (1980)** - all 15 entries: Tit for Tat, Tideman and
  Chieruzzi, Nydegger, Grofman, Shubik, Stein and Rapoport, Friedman, Davis,
  Graaskamp, Downing, Feld, Joss, Tullock, Name Withheld, Random.
* **Second tournament (1980)** - the entries whose rules are documented:
  Champion, Borufsen, Graaskamp and Katzen, Eatherley, Tranquilizer, Tester,
  Tit for Two Tats, Revised Downing (Tit for Tat and Random also took part).
* **Later work** - Generous and Contrite Tit for Tat (Wu and Axelrod's noise
  study), Pavlov, Gradual, Extort-2 and ZD-GTFT-2 (zero-determinant), the
  Southampton master/servant collusion of the 2004 anniversary competition.
* **Baselines** - Always Cooperate, Always Defect, Alternator, Suspicious TFT.
* **New (Claude, 2026)**:
  * **Envoy** - learns how the opponent answers each kind of round and plans
    the best long-run reply (policy iteration on a 4-state model, with a
    Tit-for-Tat prior); never breaks mutual cooperation; defects on the last
    move when the length is announced.
  * **Peacekeeper** - cooperates after cooperation, retaliates with
    probability equal to the opponent's recent defection rate, accepts
    punishment for its own slips (contrite), and defects against random or
    hostile players until they offer three cooperations.
  * **Evolved Reciprocator** - a lookup table bred with the Evolve tab's
    genetic algorithm against both historical fields.

The names of the original programs don't say what they do, so each strategy
has an "In short" line and a full rule description (window, Guide tab,
`axelrod explain`).  Its Details window (and the breeding results window)
also shows its **measured character** - aggression, retaliation,
forgiveness, reconciliation, responsiveness, defence - from probe games
against simple test partners (`ipd/profile.py`); for bred tables this is the
main description.  Several original programs were never published in full;
those marked *reconstructed* follow Axelrod's prose.  Reruns therefore come
close to, but don't exactly reproduce, the original tables.  Without the new
strategies, Tit for Tat comes 2nd in the first-tournament field, behind Stein
and Rapoport's end-game defection.

## Results with the new strategies (seed 1, score per move)

| Field | Top places | Tit for Tat |
|---|---|---|
| First tournament + new 3; 200 moves, told; 10 reps | 1 Evolved Reciprocator 2.877, 2 Peacekeeper 2.832, 3 Envoy 2.793, 4 Stein & Rapoport 2.658 | 5th, 2.626 |
| First + second + new 3; w = 0.99654; 10 reps | 1 Evolved Reciprocator 2.904, 2 Peacekeeper 2.865, 3 Borufsen 2.842, 4 Envoy 2.832 | 9th, 2.706 |
| Everything (38); 1% noise; w = 0.99654; 5 reps | 1 Envoy 2.615, 2 Revised Downing 2.584, 3 Peacekeeper 2.565, 4 Evolved Reciprocator 2.546 | 19th, 2.243 |
| Everything; no noise; 200 moves; 10 reps | 1 Evolved Reciprocator 2.778, 2 Borufsen 2.746, 3 Peacekeeper 2.740, 4 Envoy 2.736 | 12th, 2.627 |

The Evolved Reciprocator was bred against the two historical fields, so its
wins there are partly home advantage; the noisy all-strategy run is the fairer
test.  Ecology (1000 generations): with a random length the new strategies
and Eatherley/Borufsen share the population; with a known length, Stein and
Rapoport and Envoy take over through their last-move defection; with noise,
Generous Tit for Tat ends up with about 70%.

## Files

`axelrod_app.py` entry point and CLI · `ipd/engine.py` matches, tournaments,
ecology, GA · `ipd/strategies.py` strategies and descriptions · `ipd/gui.py`,
`ipd/charts.py` window · `test_strategies.py` (`python3 -m unittest
test_strategies`) · `make_icon.py` icon (wheel axle + rod; Pillow) ·
`install.sh`, `install-desktop.sh`.

## Windows and macOS

The same code runs on Windows and macOS. To install it there:

* **Windows:** see [WINDOWS.md](WINDOWS.md) (`install.ps1`).
* **macOS:** see [MACOS.md](MACOS.md) (`install-macos.sh`).
