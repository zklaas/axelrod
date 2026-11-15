"""Axelrod - PyQt6 window for testing iterated prisoner's dilemma strategies."""
from __future__ import annotations

import csv
import html
import json
import os
import sys
import random
import traceback

from PyQt6.QtCore import QEvent, QSettings, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDoubleSpinBox,
    QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog,
    QLabel, QMainWindow, QMessageBox, QProgressBar, QPushButton, QRadioButton, QScrollArea,
    QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget, QTextBrowser, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from . import strategies as S
from .charts import HeatMap, LineChart, MoveStrip
from .profile import character_html
from .engine import Payoffs, Settings, classify, ecological, ecology_shift, evolve, play_match, run_tournament

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _config_dir() -> str:
    """Config folder: %APPDATA% / %LOCALAPPDATA% on Windows, ~/Library on macOS,
    the usual XDG folder on Linux."""
    if os.name == "nt":
        return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Axelrod")
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Axelrod")
    return os.path.join(os.path.expanduser("~"), ".config", "axelrod")


BRED_FILE = os.path.join(_config_dir(), "bred.json")
W_SECOND = 0.99654

# --------------------------------------------------------------- bred store


def load_bred():
    try:
        with open(BRED_FILE) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    out = []
    for d in data:
        try:
            out.append(S.bred_class(d["table"], d["premise"], d["name"], d.get("note", "")))
        except (KeyError, TypeError):
            pass
    return out


def save_bred(classes):
    os.makedirs(os.path.dirname(BRED_FILE), exist_ok=True)
    data = [dict(name=c.name, table=c.table, premise=c.premise, note=getattr(c, "note", "")) for c in classes]
    with open(BRED_FILE, "w") as f:
        json.dump(data, f, indent=1)


# ------------------------------------------------------------------ worker

class Worker(QThread):
    progress = pyqtSignal(object)
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.cancelled = False

    def run(self):
        try:
            res = self.fn(self.progress.emit, lambda: self.cancelled)
        except InterruptedError:
            self.failed.emit("Stopped.")
            return
        except Exception:
            self.failed.emit(traceback.format_exc())
            return
        self.done.emit(res)


# ----------------------------------------------------------------- texts

INTRO = """
<h2>The iterated prisoner's dilemma</h2>
<p>Two players each choose, at the same moment, to <b>cooperate</b> (C) or
<b>defect</b> (D).  With the usual payoffs:</p>
<table border=1 cellpadding=4 cellspacing=0>
<tr><th></th><th>They cooperate</th><th>They defect</th></tr>
<tr><th>You cooperate</th><td>R = 3 each (reward)</td><td>you S = 0, they T = 5</td></tr>
<tr><th>You defect</th><td>you T = 5 (temptation), they S = 0 (sucker)</td><td>P = 1 each (punishment)</td></tr>
</table>
<p>Whatever the other does, defecting pays more this move - yet two defectors
end up worse off than two cooperators.  Played once, the logic says defect.
Played over and over with the same partner, the future casts a shadow back on
the present, and cooperation can pay.</p>

<h2>Axelrod's tournaments</h2>
<p>In 1979-80 the political scientist <b>Robert Axelrod</b> invited game
theorists, economists, psychologists, sociologists, mathematicians and
computer hobbyists to submit computer programs to play the iterated dilemma
in a round robin.  The <b>first tournament</b> had 14 entries plus RANDOM,
each pair meeting for 200 moves; the <b>second</b> drew 62 entries plus
RANDOM, with the game's length left uncertain (a 0.00346 chance of ending
after each move, a median of about 200 moves).  Both times the winner was the
shortest program entered, Anatol Rapoport's <b>Tit for Tat</b>.</p>
<p>In <i>The Evolution of Cooperation</i> (1984) Axelrod drew out what the
successful rules shared:</p>
<ul>
<li><b>Nice</b> - never be the first to defect;</li>
<li><b>Retaliatory</b> - answer a defection promptly;</li>
<li><b>Forgiving</b> - return to cooperation once the other does;</li>
<li><b>Clear</b> - be easy for the other to read.</li>
</ul>
<p>He also ran an <b>ecological</b> analysis (strategies that score well
become more common in the next generation) and, in 1987, bred strategies with
a <b>genetic algorithm</b>.  Later work by Axelrod and others asked what
happens when moves are sometimes <b>misread or mis-made</b> (noise): Wu and
Axelrod (1995) found that generous and contrite variants of Tit for Tat cope
best.  This program lets you rerun all of these experiments.  The work grew
out of Axelrod's interest in how cooperation - and peace - can emerge
among self-interested parties without a central authority.</p>

<h2>Using this program</h2>
<ul>
<li><b>Strategies</b> (left): tick the entrants; <i>Copies</i> enters a
strategy more than once (try several Southampton Servants).  Double-click a
name (or select it and press <i>Details...</i>) for an explanation; so does
double-clicking a row of the tournament standings.  <i>Field</i> loads a ready-made line-up with matching
settings.</li>
<li><b>Guide</b>: this page.</li>
<li><b>Tournament</b>: a round robin with Axelrod's settings by default.
The heat map shows every pairing.</li>
<li><b>Head to head</b>: watch one match move by move.</li>
<li><b>Ecology</b>: Axelrod's population simulation, from the last tournament.</li>
<li><b>Evolve</b>: breed a strategy with a genetic algorithm against the
ticked strategies, and add it to the list.</li>
</ul>
<p>Scores are average points per move, so 3.0 means full mutual cooperation.
Axelrod reported points per 200-move match (multiply by 200); the table shows
both.</p>
<p>Historical entries follow Axelrod's published descriptions (cross-checked
with the open-source Axelrod-Python project).  Several original programs were
never published in full; those marked <i>reconstructed</i> follow the
description, so rerunning a tournament gives close but not identical results.</p>
"""


PAYOFF_GUIDE = """
<h2>When the payoffs are not a prisoner's dilemma</h2>
<p>The Tournament tab lets you set the four payoffs freely.  The game is a
prisoner's dilemma only when they are in this order:</p>
<p align=center><b>T &gt; R &gt; P &gt; S</b> &nbsp; and &nbsp; <b>2R &gt; T + S</b></p>
<ul>
<li><b>T &gt; R</b> - cheating a cooperator pays more than cooperating with it (the <i>temptation</i>);</li>
<li><b>P &gt; S</b> - defecting against a defector beats being cheated (the <i>fear</i>);</li>
<li><b>R &gt; P</b> - yet mutual cooperation beats mutual defection (the <i>dilemma</i>);</li>
<li><b>2R &gt; T + S</b> - and steady cooperation beats taking turns cheating each other.</li>
</ul>
<p>Break any of these and the program still runs - the strategies just play
their rules - but it is a different game with a different lesson.  A label
under the payoff boxes names the game you have set up, and the results
window and the 'Last run' line repeat it.</p>

<h3>How the label sorts the games</h3>
<p>Four different payoffs can be put in order 24 ways, but they fall into a
handful of games.  Two questions decide the family - what is the better reply
when the other player <b>cooperates</b> (compare T with R), and when it
<b>defects</b> (compare P with S)?</p>
<table border=1 cellpadding=4 cellspacing=0>
<tr><th></th><th>Other defects: defect is better (P &gt; S)</th><th>Other defects: cooperate is better (S &gt; P)</th></tr>
<tr><th>Other cooperates: defect is better (T &gt; R)</th>
<td><b>Defect regardless.</b><br>Prisoner's dilemma if R &gt; P;<br>Deadlock if P &gt; R.</td>
<td><b>Do the opposite of the other.</b><br>Chicken, Leader or Hero if R &gt; P;<br>Anti-coordination if P &gt; R.</td></tr>
<tr><th>Other cooperates: cooperate is better (R &gt; T)</th>
<td><b>Do the same as the other.</b><br>Stag hunt if R &gt; P;<br>Coordination on defection if P &gt; R.</td>
<td><b>Cooperate regardless.</b><br>Harmony if R &gt; P;<br>Reversed dilemma if P &gt; R.</td></tr>
</table>
<p>The last question, <b>R against P</b>, asks whether the two players are
better off cooperating together or defecting together.  Results quoted below
are from this program with every strategy entered.</p>

<h3>Chicken (also hawk-dove or snowdrift): T &gt; R &gt; S &gt; P</h3>
<p>Being cheated is bad, but mutual defection is the worst outcome of all -
two cars driving at each other, neither swerving.  Example: T 5, R 3, S 1, P 0.
The fear is gone: against a defector it is better to give in.  So
<b>punishment hurts the punisher</b>.  Grudges become very costly
(Friedman's Grudger falls from about 23rd to 26th of 38), Always Cooperate
rises into the top ten, and strategies that read the other player and avoid
long feuds do best (Envoy wins and takes about 40% of the population in the
Ecology tab).</p>

<h3>Stag hunt (assurance game): R &gt; T, P &gt; S, and R &gt; P (e.g. R &gt; T &gt; P &gt; S)</h3>
<p>The story is the political philosopher Jean-Jacques Rousseau's.  A stag can only be brought down by hunters who
each hold their post; a hare can be caught by one hunter alone.  So
<b>cooperating means staying at your post for the stag</b>, and
<b>defecting means leaving it to grab a hare for yourself</b>.  A hunter left
waiting alone for the stag goes home with nothing.  Example: T 3, R 5, P 1, S 0.  Nobody is tempted by greed - a share of the
stag beats any hare.  The danger is <b>doubt</b>: if you suspect the other
will leave for a hare, leaving first is the safe move, because the hare is
guaranteed and the empty-handed outcome is not.  There is <b>no conflict of
interest</b>, only a question of trust, which is why it is also called the
assurance game.  In this program almost every nice strategy reaches steady
cooperation, the scores of the top half are nearly equal (Champion,
Eatherley and Envoy within 0.02 of each other), and the ecology barely moves.
Only players who defect first are punished: by leaving for the hare they lose
the stag.</p>

<h3>Deadlock: T &gt; R, P &gt; S, and P &gt; R (e.g. T &gt; P &gt; R &gt; S)</h3>
<p>Mutual defection beats mutual cooperation, so both players actually prefer
to defect.  Example: T 5, R 1, P 3, S 0.  There is <b>nothing to
cooperate for</b>.  Always Defect and the two Downing strategies, which
calculate what pays, rise to the top; Always Cooperate comes last; Tit for
Tat sinks to the middle.  Axelrod's advice to be nice is simply wrong here.</p>

<h3>Harmony: R &gt; T, S &gt; P, and R &gt; P</h3>
<p>Cooperating is best whatever the other does.  Example: T 3, R 5, P 0, S 1.
There is <b>no dilemma at all</b>.  Always Cooperate and Generous Tit for Tat
come out on top; any defection, even in retaliation, only costs the one who
makes it.</p>

<h3>Leader (battle of the sexes): T &gt; S &gt; R &gt; P</h3>
<p>Do the opposite of the other, and both unequal outcomes beat both equal
ones: the cheated player still does better than under mutual cooperation.
Example: T 5, S 4, R 2, P 0.  The best a pair can do is <b>take turns</b>
leading.  Alternator wins; Always Defect comes last and Always Cooperate does
well; in the ecology Tranquilizer, Alternator and Suspicious Tit for Tat
(which falls into alternating with Tit for Tat-like players) take over.</p>

<h3>Hero: S &gt; T &gt; R &gt; P</h3>
<p>Like Leader, but now the player who gives in by cooperating while the
other defects does best of all.  Example: S 5, T 4, R 2, P 0.  The results
look like Leader's - Alternator first, Always Defect last - because turn-taking
again beats any steady pattern.</p>

<h3>Anti-coordination: T &gt; R, S &gt; P, and P &gt; R</h3>
<p>Do the opposite of the other, and mutual cooperation is the worst result
of all.  Example: T 5, S 4, P 2, R 0.  Alternator wins again, random players
do surprisingly well because they often mismatch, and the cooperative
reciprocators, which settle into mutual cooperation, sink to the bottom half.</p>

<h3>Coordination on defection: R &gt; T, P &gt; S, and P &gt; R</h3>
<p>Do the same as the other, and matching on defection is better than
matching on cooperation.  Example: P 5, R 3, T 1, S 0.  Always Defect wins
and the Downing strategies follow; Always Cooperate and Alternator come last.
'Cooperate' is just the worse convention here.</p>

<h3>Reversed dilemma: S &gt; P &gt; R &gt; T</h3>
<p>The mirror image of the prisoner's dilemma: cooperating is best whatever
the other does, yet both would be better off defecting together.  Example:
S 5, P 3, R 1, T 0.  Since 'cooperate' and 'defect' have in effect swapped
roles, strategies built to cooperate do badly (Tit for Tat 23rd, Always
Cooperate 26th), and in the ecology Suspicious Tit for Tat ends up as the
whole population.</p>

<h3>Turn-taking pays: T &gt; R &gt; P &gt; S but 2R &le; T + S</h3>
<p>The order is right, but cheating is so lucrative that two players who take
turns - one cheats while the other cooperates, then they swap - average
(T + S)/2 a move, at least as much as steady cooperation's R.  Example:
T 10, R 3, P 1, S 0.  Here <b>Alternator wins</b>, Tester and Tranquilizer,
who cheat on alternate moves, do very well, and in the ecology Tranquilizer,
Alternator and Suspicious Tit for Tat take over.  Axelrod required 2R &gt; T + S
precisely to rule this out.</p>

<h3>Ties</h3>
<p>When two payoffs are equal, one choice stops mattering.  T = R: cheating a
cooperator gains nothing.  P = S: cooperating with a defector costs nothing.
R = P: cooperation earns nothing more than mutual defection - with T 5, R 2,
P 2, S 0 the calculating Downing strategies and Always Defect lead.  With all
four equal every strategy scores the same, and the ranking is only the order
the strategies happen to be listed in.</p>

<h3>Things that do not change the game</h3>
<ul>
<li><b>Adding the same amount to all four payoffs, or multiplying all four by
the same positive number,</b> leaves the game the same.  For example,
T 0, R -2, P -4, S -5 gives the same rankings as the usual 5, 3, 1, 0.  The
exceptions are the strategies built around the usual numbers: Graaskamp and
Katzen's score schedule (23 points by move 11, and so on) and Tideman and
Chieruzzi's '10 points ahead' test.</li>
<li><b>Negative or zero scores</b> are fine for tournaments.  The Ecology tab
grows each strategy in proportion to its score, which needs every score above
zero, so it then adds the same amount to all scores first (and says so).</li>
</ul>
<p>The strategies were written for the usual 5, 3, 1, 0, and most of them do
not look at the payoffs at all: Tit for Tat copies, Grudger holds a grudge,
whatever the numbers.  Only Downing, Revised Downing, Generous Tit for Tat,
Envoy and the score-schedule strategies use them.  That is part of what
these experiments show - a rule that is wise in one game can be foolish in
another.</p>
"""


def strategy_html(cls) -> str:
    e = html.escape
    rows = []
    if cls.author:
        rows.append(f"<b>By:</b> {e(cls.author)}")
    rows.append(f"<b>From:</b> {e(cls.origin)}" + (f" &mdash; placed {e(cls.place)}" if cls.place else ""))
    rows.append("<b>Random element:</b> " + ("yes" if cls.stochastic else "no (deterministic)"))
    out = f"<h3>{e(cls.name)}</h3><p>" + "<br>".join(rows) + "</p>"
    if cls.gist:
        out += f"<p><b>In short:</b> {e(cls.gist)}</p>"
    out += f"<p><b>The rules:</b> {e(cls.blurb)}</p>"
    return out


GA_TIPS = {
    "gens": "How many rounds of selection and breeding.  More = better tuned to the field, slower.",
    "pop": "How many candidate tables live at once.  Bigger = more variety, slower per generation.",
    "turns": "Length of each scoring game.  Axelrod used 151.  Tables cannot count moves, so this "
             "mostly sets how much the opening matters.",
    "seed": "Starting point for the random numbers.  Same seed + same settings = same result; "
            "change it to get a different run.",
    "mut": "Chance that each of the 70 letters flips when a child is made.  0.01 is about one flip "
           "per child; much higher and good tables get scrambled.",
}

EVOLVE_HELP = """
<h3>Breeding a strategy</h3>
<p>This is the experiment Axelrod reported in 1987.  A candidate strategy is a
<b>table of 64 moves</b>, one for each possible pattern of the last three rounds
(each round is one of four outcomes: both cooperated, you were cheated, you
cheated, both defected; 4 &times; 4 &times; 4 = 64).  Six more letters, the
<b>premise</b>, stand in for the three rounds 'before' the game so the table also
decides the opening moves.  Random tables are scored, the better ones become
parents, and their children mix the parents' tables (crossover) with an
occasional random change (mutation).</p>

<h4>How to use it</h4>
<ol>
<li><b>Tick the opponents</b> in the list on the left.  They are the whole
world the tables grow up in: each candidate plays one game against each ticked
strategy (with Copies counted), and its score is its average points per move.
Noise, payoffs and whether the length is announced come from the Tournament tab.</li>
<li><b>Set the parameters</b> (hover each box for a reminder) and press
<b>Evolve</b>.  The chart shows the best and the average score each
generation; when the average catches up with the best, the run has settled.</li>
<li><b>Add the best to the strategy list</b> and give it a name.  It then
appears under 'Bred in this app' (and is remembered between sessions).</li>
<li><b>Test it in a tournament</b>, ideally against a <i>different</i> field
from the one it was bred against.  A table can score very well against its
training partners simply by learning their quirks.</li>
</ol>

<h4>How the Evolved Reciprocator was bred</h4>
<p>Of my three strategies, only the Evolved Reciprocator was bred; Envoy and
Peacekeeper were designed by hand.  For it I used:</p>
<table border=1 cellpadding=3 cellspacing=0>
<tr><td>Opponents</td><td>all 23 entries of the first and second tournaments, one copy each</td></tr>
<tr><td>Generations</td><td>60</td></tr>
<tr><td>Population</td><td>24</td></tr>
<tr><td>Moves a game</td><td>151 (Axelrod's figure)</td></tr>
<tr><td>Mutation</td><td>0.01</td></tr>
<tr><td>Crossover</td><td>0.6 (fixed in this program)</td></tr>
<tr><td>Noise, payoffs</td><td>none; T 5, R 3, P 1, S 0</td></tr>
<tr><td>Seeds</td><td>1, 2, 3 and 4; I kept the best (seed 4, about 2.95 a move),
then checked all four in full tournaments, where seed 4 also did best</td></tr>
</table>
<p><b>Load my recipe</b> sets all of this (with seed 4) so you can watch it happen;
each run takes about 20 seconds.</p>

<h4>Choosing your own settings</h4>
<ul>
<li><b>Start with my recipe and change one thing</b>, so you can tell what made the difference.</li>
<li><b>Run several seeds.</b>  Breeding is a random search; different seeds find
different tables, and a single run can get stuck.  Keep the best of 3-5.</li>
<li><b>Generations 30-100, population 20-50</b> is a good range.  Time grows with
generations &times; population &times; number of opponents.</li>
<li><b>Mutation 0.005-0.02.</b>  Too low and the population stops exploring; above
about 0.05 good tables are scrambled faster than they are selected.</li>
<li><b>Choose the opponents for the question you are asking.</b>  Axelrod
used eight representative strategies from his second tournament.  To breed something
robust, include tough opponents (Always Defect, Tester, Extort-2) and
forgiving ones; a field of only nice strategies breeds tables that never learn
to defend themselves.  The Evolved Reciprocator shows this: no unconditional
defector was in its field, and it keeps offering cooperation to Always Defect.</li>
<li><b>Add 1% noise</b> on the Tournament tab to breed tables that cope with mistakes.</li>
</ul>
"""

def result_html(r, opponents, character="") -> str:
    """The bred table, laid out as 64 readable rows."""
    t, prem = r.best_table, r.best_premise
    pair = {"CC": "both C", "CD": "was cheated", "DC": "cheated", "DD": "both D"}
    cells = []
    for idx in range(64):
        bits = format(idx, "06b").replace("0", "C").replace("1", "D")
        rounds = " &rarr; ".join(pair[bits[k:k + 2]] for k in (0, 2, 4))
        mv = t[idx]
        col = "#3a9a5b" if mv == "C" else "#d1495b"
        cells.append(f"<td>{rounds}</td><td align=center style='color:{col}'><b>{mv}</b></td>")
    rows = "".join("<tr>" + cells[i] + cells[i + 32] + "</tr>" for i in range(32))
    opening = " ".join(f"({prem[k]},{prem[k + 1]})" for k in (0, 2, 4))
    return (
        f"<h3>Best table: {r.best_fitness:.3f} points a move</h3>"
        f"<p>Bred over {len(r.history)} generations against {len(opponents)} strategies: "
        f"{html.escape(', '.join(opponents))}.</p>"
        f"<p>It cooperates in <b>{t.count('C')}</b> of the 64 situations.  After three rounds of "
        f"mutual cooperation it plays <b>{t[0]}</b>; after three of mutual defection, <b>{t[63]}</b>.  "
        f"Its imagined opening history (premise) is {opening}, written (mine, theirs).</p>"
        + character +
        "<h4>The table</h4><p>Each row: the last three rounds, oldest first, as seen by the bred strategy "
        "(<i>was cheated</i> = it cooperated and the other defected; <i>cheated</i> = the reverse), "
        "and the move it then makes.</p>"
        "<table border=1 cellspacing=0 cellpadding=3>"
        "<tr><th>Last three rounds</th><th>Move</th><th>Last three rounds</th><th>Move</th></tr>"
        + rows + "</table>"
        f"<p>Raw table: <code>{t}</code> &nbsp; premise <code>{prem}</code></p>")


# ------------------------------------------------------------------ window

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Axelrod - iterated prisoner's dilemma")
        self.settings_store = QSettings("Axelrod", "Axelrod")
        self.bred = load_bred()
        self.worker = None
        self.last_result = None
        self.copies: dict[str, QSpinBox] = {}
        self.items: dict[str, QTreeWidgetItem] = {}

        split = QSplitter()
        split.addWidget(self.build_left())
        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_guide(), "Guide")
        self.tabs.addTab(self.build_tournament(), "Tournament")
        self.tabs.addTab(self.build_match(), "Head to head")
        self.tabs.addTab(self.build_ecology(), "Ecology")
        self.tabs.addTab(self.build_evolve(), "Evolve")
        split.addWidget(self.tabs)
        split.setStretchFactor(1, 1)
        split.setSizes([420, 900])
        self.setCentralWidget(split)
        self.status = self.statusBar()
        self.build_menu()
        self.apply_preset(0)
        self.resize(1320, 840)
        geo = self.settings_store.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)

    # ---------------------------------------------------------- left panel
    def build_left(self):
        w = QWidget()
        v = QVBoxLayout(w)
        row = QHBoxLayout()
        row.addWidget(QLabel("Field:"))
        self.preset = QComboBox()
        self.presets = [
            ("Axelrod's first tournament (1980)", self.preset_first),
            ("Axelrod's second tournament (entries here)", self.preset_second),
            ("New strategies vs both tournaments", self.preset_mine),
            ("Everything, with 1% noise", self.preset_noise),
            ("Everything", self.preset_all),
        ]
        for name, _ in self.presets:
            self.preset.addItem(name)
        self.preset.activated.connect(self.apply_preset)
        row.addWidget(self.preset, 1)
        v.addLayout(row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Strategy", "Copies"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.header().setStretchLastSection(False)
        self.tree.setColumnWidth(1, 64)
        self.tree.itemDoubleClicked.connect(
            lambda it, col: self.show_details(it.data(0, Qt.ItemDataRole.UserRole)) if col == 0 else None)
        self.tree.itemChanged.connect(self.tree_changed)
        self.tree.setToolTip("Tick strategies to enter them.  Double-click a name (or select it and "
                             "press Details...) to read how it works.")
        v.addWidget(self.tree, 1)
        self.count_label = QLabel()
        self.fill_tree()

        row = QHBoxLayout()
        for label, fn in (("All", lambda: self.check_all(True)), ("None", lambda: self.check_all(False)),
                          ("Details...", self.show_details)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addWidget(self.count_label, 1)
        v.addLayout(row)
        hint = QLabel("Double-click a strategy, or select it and press Details..., to read how it works.")
        hint.setWordWrap(True)
        v.addWidget(hint)
        return w

    def all_classes(self):
        return list(S.REGISTRY) + list(self.bred)

    def fill_tree(self):
        self.tree.blockSignals(True)
        checked = {n for n, it in self.items.items() if it.checkState(0) == Qt.CheckState.Checked}
        self.tree.clear()
        self.items.clear()
        self.copies.clear()
        for g in S.GROUPS:
            members = [c for c in self.all_classes() if c.origin == g]
            if not members:
                continue
            top = QTreeWidgetItem([g])
            top.setFlags(top.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
            f = top.font(0)
            f.setBold(True)
            top.setFont(0, f)
            self.tree.addTopLevelItem(top)
            for c in members:
                it = QTreeWidgetItem([c.name])
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(0, Qt.CheckState.Checked if c.name in checked else Qt.CheckState.Unchecked)
                it.setData(0, Qt.ItemDataRole.UserRole, c.name)
                it.setToolTip(0, c.gist)
                top.addChild(it)
                sb = QSpinBox()
                sb.setRange(1, 20)
                sb.setToolTip("How many separate entries of this strategy to enter")
                sb.valueChanged.connect(self.update_count)
                self.tree.setItemWidget(it, 1, sb)
                self.copies[c.name] = sb
                self.items[c.name] = it
            top.setExpanded(True)
        self.tree.blockSignals(False)
        self.update_count()

    def tree_changed(self, item, col):
        self.update_count()

    def check_all(self, on):
        self.set_checked({c.name for c in self.all_classes()} if on else set())

    def set_checked(self, names):
        self.tree.blockSignals(True)
        for n, it in self.items.items():
            it.setCheckState(0, Qt.CheckState.Checked if n in names else Qt.CheckState.Unchecked)
            self.copies[n].setValue(1)
        self.tree.blockSignals(False)
        self.tree.viewport().update()
        self.update_count()

    def entries(self):
        out = []
        for c in self.all_classes():
            it = self.items.get(c.name)
            if it is not None and it.checkState(0) == Qt.CheckState.Checked:
                out.append((c, self.copies[c.name].value()))
        return out

    def update_count(self, *_):
        n = sum(k for _, k in self.entries())
        self.count_label.setText(f"{n} entrant{'s' if n != 1 else ''}")

    def show_details(self, name=None):
        """A strategy's description and character in its own window: the
        one named, else the one selected in the list."""
        if not name:
            it = self.tree.currentItem()
            name = it.data(0, Qt.ItemDataRole.UserRole) if it else None
        cls = next((c for c in self.all_classes() if c.name == name), None)
        if cls is None:
            QMessageBox.information(self, "Axelrod", "Select a strategy in the list first.")
            return
        d = QDialog(self)
        d.setWindowTitle(f"Axelrod - {cls.name}")
        d.resize(760, 720)
        v = QVBoxLayout(d)
        tb = QTextBrowser()
        tb.setHtml(strategy_html(cls) + character_html(cls))
        v.addWidget(tb)
        b = QPushButton("Close")
        b.clicked.connect(d.close)
        v.addWidget(b, 0, Qt.AlignmentFlag.AlignRight)
        d.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        d.show()

    # ---------------------------------------------------------- presets
    def apply_preset(self, idx):
        self.preset.setCurrentIndex(idx)
        self.presets[idx][1]()
        self.update_count()

    def _settings(self, w=0.0, noise=0.0, reps=5):
        self.len_fixed.setChecked(w == 0)
        self.len_random.setChecked(w > 0)
        self.turns.setValue(200)
        self.w.setValue(w or W_SECOND)
        self.noise.setValue(noise * 100)
        self.reps.setValue(reps)
        self.self_play.setChecked(True)
        self.tell.setChecked(True)
        self.length_mode_changed()

    def preset_first(self):
        self.set_checked({c.name for c in S.REGISTRY if c.origin == S.FIRST})
        self._settings()

    def preset_second(self):
        self.set_checked({c.name for c in S.REGISTRY if c.origin == S.SECOND} | {"Tit For Tat", "Random"})
        self._settings(w=W_SECOND)

    def preset_mine(self):
        self.set_checked({c.name for c in S.REGISTRY if c.origin in (S.FIRST, S.SECOND, S.MINE)})
        self._settings(w=W_SECOND)

    def preset_noise(self):
        self.set_checked({c.name for c in self.all_classes()})
        self._settings(w=W_SECOND, noise=0.01, reps=3)

    def preset_all(self):
        self.set_checked({c.name for c in self.all_classes()})
        self._settings(reps=3)

    # ---------------------------------------------------------- tournament tab
    def build_tournament(self):
        w = QWidget()
        v = QVBoxLayout(w)
        box = QGroupBox("Settings")
        g = QGridLayout(box)
        self.len_fixed = QRadioButton("Fixed length, turns:")
        self.len_random = QRadioButton("Random length, continue with chance w:")
        bg = QButtonGroup(w)
        bg.addButton(self.len_fixed)
        bg.addButton(self.len_random)
        self.len_fixed.toggled.connect(self.length_mode_changed)
        self.turns = QSpinBox()
        self.turns.setRange(1, 100000)
        self.turns.setValue(200)
        self.w = QDoubleSpinBox()
        self.w.setDecimals(5)
        self.w.setRange(0.5, 0.99999)
        self.w.setSingleStep(0.001)
        self.w.setValue(W_SECOND)
        self.w.setToolTip("Axelrod's second tournament used w = 0.99654 (median length about 200).")
        self.w_label = QLabel()
        self.w_label.setWordWrap(True)
        self.w.valueChanged.connect(self.update_w_label)
        self.tell = QCheckBox("Strategies are told the length")
        self.tell.setToolTip("In the first tournament everyone knew a game lasted 200 moves; "
                             "some entries defect at the end when they know.")
        self.reps = QSpinBox()
        self.reps.setRange(1, 1000)
        self.reps.setValue(5)
        self.noise = QDoubleSpinBox()
        self.noise.setRange(0, 50)
        self.noise.setDecimals(2)
        self.noise.setSuffix(" %")
        self.noise.setToolTip("Chance that each intended move comes out the opposite way.")
        self.self_play = QCheckBox("Each entrant also plays its own twin")
        self.self_play.setChecked(True)
        self.seed = QSpinBox()
        self.seed.setRange(0, 10 ** 9)
        self.seed.setValue(1)
        self.pay = {}
        payrow = QHBoxLayout()
        for k, val in (("T", 5), ("R", 3), ("P", 1), ("S", 0)):
            sb = QDoubleSpinBox()
            sb.setRange(-100, 100)
            sb.setDecimals(1)
            sb.setValue(val)
            self.pay[k] = sb
            payrow.addWidget(QLabel(k))
            payrow.addWidget(sb)
        self.game_label = QLabel()
        self.game_label.setWordWrap(True)
        for sb in self.pay.values():
            sb.valueChanged.connect(self.update_game_label)
        payrow.addStretch()
        g.addWidget(self.len_fixed, 0, 0)
        g.addWidget(self.turns, 0, 1)
        g.addWidget(self.tell, 0, 2)
        g.addWidget(self.len_random, 1, 0)
        g.addWidget(self.w, 1, 1)
        g.addWidget(self.w_label, 1, 2)
        g.addWidget(QLabel("Repetitions:"), 2, 0)
        g.addWidget(self.reps, 2, 1)
        g.addWidget(self.self_play, 2, 2)
        g.addWidget(QLabel("Noise:"), 3, 0)
        g.addWidget(self.noise, 3, 1)
        g.addWidget(QLabel("Random seed:"), 4, 0)
        g.addWidget(self.seed, 4, 1)
        pl = QLabel("Payoffs: T temptation, R reward, P punishment, S sucker:")
        pl.setWordWrap(True)
        g.addWidget(pl, 3, 2)
        pw = QWidget()
        pw.setLayout(payrow)
        g.addWidget(pw, 4, 2)
        g.addWidget(self.game_label, 5, 0, 1, 3)
        self.update_game_label()
        v.addWidget(box)

        row = QHBoxLayout()
        self.run_btn = QPushButton("Run tournament")
        self.run_btn.clicked.connect(self.run_tournament)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_worker)
        self.progress = QProgressBar()
        row.addWidget(self.run_btn)
        row.addWidget(self.stop_btn)
        row.addWidget(self.progress, 1)
        v.addLayout(row)
        row = QHBoxLayout()
        self.t_last = QLabel("No tournament run yet.  The results open in their own window.")
        self.t_last.setWordWrap(True)
        self.t_show = QPushButton("Show results...")
        self.t_show.setEnabled(False)
        self.t_show.clicked.connect(self.show_results_dialog)
        row.addWidget(self.t_last, 1)
        row.addWidget(self.t_show)
        v.addLayout(row)
        v.addStretch(1)

        # The results window: standings, heat map, notes, export.
        self.t_dialog = QDialog(self)
        self.t_dialog.setWindowTitle("Axelrod - tournament results")
        self.t_dialog.resize(1100, 780)
        dv = QVBoxLayout(self.t_dialog)
        self.result_tabs = QTabWidget()
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.horizontalHeader().sectionResized.connect(
            lambda *_: self.table.resizeRowsToContents())
        self.table.itemDoubleClicked.connect(self.table_details)
        self.table.viewport().installEventFilter(self)
        self.table.setToolTip("Double-click a row to read how that strategy works.")
        self.result_tabs.addTab(self.table, "Standings")
        self.heat = HeatMap()
        sc = QScrollArea()
        sc.setWidget(self.heat)
        self.result_tabs.addTab(sc, "Pairings heat map")
        self.summary = QTextBrowser()
        self.result_tabs.addTab(self.summary, "Notes")
        dv.addWidget(self.result_tabs, 1)
        drow = QHBoxLayout()
        self.export_btn = QPushButton("Export CSV...")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_csv)
        close = QPushButton("Close")
        close.clicked.connect(self.t_dialog.close)
        drow.addWidget(self.export_btn)
        drow.addStretch()
        drow.addWidget(close)
        dv.addLayout(drow)
        return w

    def show_results_dialog(self):
        self.t_dialog.show()
        self.t_dialog.raise_()
        self.t_dialog.activateWindow()
        QTimer.singleShot(0, self.table.resizeRowsToContents)

    def update_game_label(self, *_):
        name, why = classify(Payoffs(*(self.pay[k].value() for k in "TRPS")))
        ok = name == "Prisoner's dilemma"
        colour = "#3a9a5b" if ok else "#d1495b"
        self.game_label.setText(f"<span style='color:{colour}'><b>Game: {html.escape(name)}.</b></span> "
                                + html.escape(why)
                                + ("" if ok else "  See the Guide: 'When the payoffs are not a prisoner's dilemma'."))

    def update_w_label(self, *_):
        import math as _m
        w = self.w.value()
        mean = 1 / (1 - w)
        median = _m.ceil(_m.log(0.5) / _m.log(w))
        self.w_label.setText(f"= matches average {mean:.0f} moves (median {median}); players are not told")

    def length_mode_changed(self, *_):
        fixed = self.len_fixed.isChecked()
        self.turns.setEnabled(fixed)
        self.tell.setEnabled(fixed)
        self.w.setEnabled(not fixed)
        self.w_label.setEnabled(not fixed)
        self.update_w_label()

    def current_settings(self) -> Settings:
        pay = Payoffs(*(self.pay[k].value() for k in "TRPS"))
        return Settings(turns=self.turns.value(),
                        w=0.0 if self.len_fixed.isChecked() else self.w.value(),
                        tell_length=self.tell.isChecked(), repetitions=self.reps.value(),
                        noise=self.noise.value() / 100, self_play=self.self_play.isChecked(),
                        payoffs=pay, seed=self.seed.value())

    def busy(self, on, label=""):
        for b in (self.run_btn, self.match_btn, self.eco_btn, self.evo_btn):
            b.setEnabled(not on)
        self.stop_btn.setEnabled(on)
        self.evo_stop.setEnabled(on)
        if not on and hasattr(self, "evo_progress") and self.evo_result is None and self.evo_progress.value():
            self.evo_status.setText("Stopped.")
        if label:
            self.status.showMessage(label)

    def start(self, fn, on_done, on_progress=None, label="Working..."):
        if self.worker and self.worker.isRunning():
            return
        self.worker = Worker(fn)
        if on_progress:
            self.worker.progress.connect(on_progress)
        self.worker.done.connect(lambda r: (self.busy(False, "Done."), on_done(r)))
        self.worker.failed.connect(self.worker_failed)
        self.busy(True, label)
        self.worker.start()

    def worker_failed(self, msg):
        self.busy(False, "Stopped." if msg == "Stopped." else "Error.")
        if msg != "Stopped.":
            QMessageBox.warning(self, "Axelrod", msg[-3000:])

    def stop_worker(self):
        if self.worker:
            self.worker.cancelled = True

    def run_tournament(self):
        entries = self.entries()
        if sum(k for _, k in entries) < 2:
            QMessageBox.information(self, "Axelrod", "Tick at least two strategies (or one with two copies).")
            return
        st = self.current_settings()
        self.progress.setValue(0)

        def job(emit, cancelled):
            return run_tournament(entries, st, progress=lambda d, t: emit((d, t)), cancel=cancelled)

        def prog(dt):
            d, t = dt
            self.progress.setMaximum(t)
            self.progress.setValue(d)

        self.start(job, self.show_tournament, prog, "Running tournament...")

    def show_tournament(self, res):
        self.last_result = res
        self.export_btn.setEnabled(True)
        rows = sorted(res.standings, key=lambda s: s.rank)
        self.table.setSortingEnabled(False)
        self.table.clear()
        heads = ["Rank", "Strategy", "Score / move", "Score / match", "Matches won", "Cooperation %", "In short"]
        self.table.setColumnCount(len(heads))
        self.table.setHorizontalHeaderLabels(heads)
        self.table.setRowCount(len(rows))
        by = {c.name: c for c in self.all_classes()}
        for r, s in enumerate(rows):
            base = s.name.rsplit(" #", 1)[0]
            vals = [s.rank, s.name, round(s.mean, 3), round(s.per_match, 1), s.wins, round(100 * s.coop, 1),
                    by[base].gist if base in by else ""]
            for c, val in enumerate(vals):
                it = QTableWidgetItem()
                if isinstance(val, (int, float)):
                    it.setData(Qt.ItemDataRole.DisplayRole, val)
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    it.setText(str(val))
                if c == 1:
                    it.setData(Qt.ItemDataRole.UserRole, base)
                if base in by and c == 6:
                    it.setToolTip(by[base].blurb)
                self.table.setItem(r, c, it)
        self.table.setSortingEnabled(True)
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        for c in range(len(heads) - 1):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(len(heads) - 1, QHeaderView.ResizeMode.Stretch)
        self.table.resizeRowsToContents()
        QTimer.singleShot(0, self.table.resizeRowsToContents)   # again, once the widths have settled
        order = [res.names.index(s.name) for s in rows]
        names = [res.names[i] for i in order]
        mat = [[res.matrix[i][j] for j in order] for i in order]
        p = res.settings.payoffs
        self.heat.set_data(names, mat, p.P, p.R)
        st = res.settings
        length = (f"{st.turns} moves (told: {'yes' if st.tell_length else 'no'})" if st.w <= 0
                  else f"random, w = {st.w} (mean {res.mean_turns:.0f} moves played)")
        win = rows[0]
        nice = [s.name for s in rows[:max(1, len(rows) // 2)]]
        self.summary.setHtml(
            f"<h3>Tournament</h3><p>{len(rows)} entrants, {st.repetitions} repetitions, length {length}, "
            f"noise {st.noise * 100:g}%, payoffs T={p.T:g} R={p.R:g} P={p.P:g} S={p.S:g}, "
            f"self-play {'on' if st.self_play else 'off'}, seed {st.seed}.  "
            f"Game: {html.escape(classify(p)[0])}.</p>"
            f"<p><b>Winner:</b> {html.escape(win.name)} with {win.mean:.3f} a move "
            f"({win.per_match:.0f} a match).</p>"
            "<p>Rows of the heat map are the scorer, columns the opponent.  Dark green = R (mutual "
            "cooperation) or better, pale yellow = halfway, red = P (mutual defection) or worse.  "
            "Hover a cell for both players' scores.  The Ecology tab now uses these results.</p>"
            "<p>Top half: " + html.escape(", ".join(nice)) + "</p>")
        self.status.showMessage(f"Winner: {win.name} ({win.mean:.3f} a move)")
        self.t_last.setText(f"Last run: {len(rows)} entrants, {html.escape(classify(p)[0]).lower()}; "
                            f"winner <b>{html.escape(win.name)}</b> with {win.mean:.3f} a move.")
        self.t_show.setEnabled(True)
        self.t_dialog.setWindowTitle(f"Axelrod - tournament results ({len(rows)} entrants, winner {win.name})")
        self.result_tabs.setCurrentIndex(0)
        self.show_results_dialog()
        self.eco_source.setText(f"Using the last tournament: {len(rows)} entrants, winner {win.name}.")

    def eventFilter(self, obj, ev):
        # Re-wrap the standings whenever the table changes size.
        if obj is self.table.viewport() and ev.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self.table.resizeRowsToContents)
        return super().eventFilter(obj, ev)

    def table_details(self, item):
        it = self.table.item(item.row(), 1)
        if it is not None:
            self.show_details(it.data(Qt.ItemDataRole.UserRole))

    def export_csv(self):
        res = self.last_result
        if not res:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export results", "axelrod-tournament.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["rank", "strategy", "score_per_move", "score_per_match", "wins", "cooperation"])
            for s in sorted(res.standings, key=lambda s: s.rank):
                w.writerow([s.rank, s.name, f"{s.mean:.4f}", f"{s.per_match:.2f}", s.wins, f"{s.coop:.4f}"])
            w.writerow([])
            w.writerow(["score per move: row vs column"] + res.names)
            for n, row in zip(res.names, res.matrix):
                w.writerow([n] + [f"{v:.4f}" for v in row])
        self.status.showMessage(f"Saved {path}")

    # ---------------------------------------------------------- match tab
    def build_match(self):
        w = QWidget()
        v = QVBoxLayout(w)
        row1 = QHBoxLayout()
        self.ma = QComboBox()
        self.mb = QComboBox()
        self.fill_match_combos()
        self.match_btn = QPushButton("Play")
        self.match_btn.clicked.connect(self.play_match)
        for lab, wd in (("A:", self.ma), ("B:", self.mb)):
            row1.addWidget(QLabel(lab))
            row1.addWidget(wd)
        row1.addWidget(self.match_btn)
        row1.addStretch()
        copy = QPushButton("Use Tournament tab settings")
        copy.setToolTip("Copy length, noise and seed from the Tournament tab")
        copy.clicked.connect(self.copy_match_settings)
        row1.addWidget(copy)
        v.addLayout(row1)

        row2 = QHBoxLayout()
        self.m_fixed = QRadioButton("Fixed length:")
        self.m_random = QRadioButton("Random length, w:")
        bg = QButtonGroup(w)
        bg.addButton(self.m_fixed)
        bg.addButton(self.m_random)
        self.m_fixed.setChecked(True)
        self.m_turns = QSpinBox()
        self.m_turns.setRange(1, 100000)
        self.m_turns.setValue(200)
        self.m_turns.setSuffix(" moves")
        self.m_tell = QCheckBox("players are told the length")
        self.m_tell.setChecked(True)
        self.m_w = QDoubleSpinBox()
        self.m_w.setDecimals(5)
        self.m_w.setRange(0.5, 0.99999)
        self.m_w.setSingleStep(0.001)
        self.m_w.setValue(W_SECOND)
        self.m_w.setToolTip("Chance the match continues after each move.  0.99654 = Axelrod's second "
                            "tournament (average about 289 moves, median 200); players are not told.")
        self.m_noise = QDoubleSpinBox()
        self.m_noise.setRange(0, 50)
        self.m_noise.setDecimals(2)
        self.m_noise.setSuffix(" %")
        self.m_seed = QSpinBox()
        self.m_seed.setRange(0, 10 ** 9)
        self.m_seed.setValue(1)
        self.m_seed.setToolTip("Same seed = same match (including a random length).  Change it for another draw.")
        for wd in (self.m_fixed, self.m_turns, self.m_tell):
            row2.addWidget(wd)
        row2.addSpacing(16)
        row2.addWidget(self.m_random)
        row2.addWidget(self.m_w)
        row2.addSpacing(16)
        for lab, wd in (("Noise:", self.m_noise), ("Seed:", self.m_seed)):
            row2.addWidget(QLabel(lab))
            row2.addWidget(wd)
        row2.addStretch()
        v.addLayout(row2)
        self.m_fixed.toggled.connect(self.match_mode_changed)
        self.match_mode_changed()

        self.m_text = QLabel("Pick two strategies and press Play.  Green = cooperate, red = defect.  "
                             "Payoffs come from the Tournament tab.")
        self.m_text.setWordWrap(True)
        v.addWidget(self.m_text)
        self.strip = MoveStrip()
        sc = QScrollArea()
        sc.setWidget(self.strip)
        sc.setWidgetResizable(True)
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(sc)
        self.m_chart = LineChart()
        split.addWidget(self.m_chart)
        split.setSizes([330, 400])
        v.addWidget(split, 1)
        return w

    def match_mode_changed(self, *_):
        fixed = self.m_fixed.isChecked()
        self.m_turns.setEnabled(fixed)
        self.m_tell.setEnabled(fixed)
        self.m_w.setEnabled(not fixed)

    def copy_match_settings(self):
        fixed = self.len_fixed.isChecked()
        self.m_fixed.setChecked(fixed)
        self.m_random.setChecked(not fixed)
        self.m_turns.setValue(self.turns.value())
        self.m_tell.setChecked(self.tell.isChecked())
        self.m_w.setValue(self.w.value())
        self.m_noise.setValue(self.noise.value())
        self.m_seed.setValue(self.seed.value())
        self.match_mode_changed()

    def fill_match_combos(self):
        for cb, default in ((self.ma, "Tit For Tat"), (self.mb, "Joss")):
            cur = cb.currentText() or default
            cb.clear()
            for c in self.all_classes():
                cb.addItem(c.name)
            i = cb.findText(cur)
            cb.setCurrentIndex(max(0, i))

    def play_match(self):
        by = {c.name: c for c in self.all_classes()}
        A, B = by[self.ma.currentText()], by[self.mb.currentText()]
        st = self.current_settings()
        st.noise = self.m_noise.value() / 100
        rng = random.Random(self.m_seed.value())
        if self.m_fixed.isChecked():
            st.w = 0
            st.turns = self.m_turns.value()
            st.tell_length = self.m_tell.isChecked()
            length = st.turns
            how = (f"Fixed length, {length} moves; the players "
                   + ("were told the length." if st.tell_length else "were not told the length."))
        else:
            st.w = self.m_w.value()
            length = st.draw_length(rng)
            how = (f"Random length (w = {st.w:g}, average {1 / (1 - st.w):.0f} moves): this match lasted "
                   f"{length} moves; the players were not told.")
        r = play_match(A(), B(), length, st, rng)
        na, nb = A.name, B.name
        self.strip.set_moves(r.a, r.b, na, nb)
        ca, cb = [], []
        x = y = 0.0
        for k, (a, b) in enumerate(zip(r.a, r.b), 1):
            p, q = st.payoffs.pair(a, b)
            x += p
            y += q
            ca.append(x / k)
            cb.append(y / k)
        self.m_chart.set_data([(f"A: {na}", ca), (f"B: {nb}", cb)], "Running average score per move",
                              "move", "score", 0, max(st.payoffs.T, 1))
        self.m_text.setText(
            f"A {na}: {r.score_a:g} points ({r.score_a / r.turns:.2f} a move, cooperated "
            f"{100 * r.a.count('C') / r.turns:.0f}%)   -   B {nb}: {r.score_b:g} points "
            f"({r.score_b / r.turns:.2f} a move, cooperated {100 * r.b.count('C') / r.turns:.0f}%).  "
            f"{how}  Noise {st.noise * 100:g}%.  Green = cooperate, red = defect; hover for move numbers.")

    # ---------------------------------------------------------- ecology tab
    def build_ecology(self):
        w = QWidget()
        v = QVBoxLayout(w)
        eco_intro = QLabel(
            "Axelrod's ecological analysis: start with equal shares of each strategy; each generation "
            "a strategy's share grows in proportion to its average score against the current mix.  "
            "Exploiters fade once their prey dies out.")
        eco_intro.setWordWrap(True)
        v.addWidget(eco_intro)
        row = QHBoxLayout()
        self.eco_source = QLabel("Run a tournament first.")
        row.addWidget(self.eco_source, 1)
        row.addWidget(QLabel("Generations:"))
        self.eco_gens = QSpinBox()
        self.eco_gens.setRange(10, 100000)
        self.eco_gens.setValue(1000)
        row.addWidget(self.eco_gens)
        self.eco_log = QCheckBox("Log scale shares")
        row.addWidget(self.eco_log)
        self.eco_btn = QPushButton("Run ecology")
        self.eco_btn.clicked.connect(self.run_ecology)
        row.addWidget(self.eco_btn)
        v.addLayout(row)
        split = QSplitter(Qt.Orientation.Vertical)
        self.eco_chart = LineChart()
        split.addWidget(self.eco_chart)
        self.eco_table = QTableWidget()
        self.eco_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.eco_table.verticalHeader().setVisible(False)
        split.addWidget(self.eco_table)
        split.setSizes([500, 200])
        v.addWidget(split, 1)
        return w

    def run_ecology(self):
        res = self.last_result
        if not res:
            QMessageBox.information(self, "Axelrod", "Run a tournament first; the ecology uses its scores.")
            return
        hist = ecological(res.matrix, self.eco_gens.value())
        shift = ecology_shift(res.matrix)
        n = len(res.names)
        final = hist[-1]
        order = sorted(range(n), key=lambda i: -final[i])
        shown = order[:12]
        import math as _m
        log = self.eco_log.isChecked()

        def tr(x):
            return _m.log10(max(x, 1e-6)) if log else x * 100

        series = [(res.names[i], [tr(h[i]) for h in hist]) for i in shown]
        self.eco_chart.set_data(series, "Population shares (top 12 at the end)", "generation",
                                "log10 share" if log else "share %", -6 if log else 0, None)
        self.eco_table.clear()
        self.eco_table.setColumnCount(4)
        self.eco_table.setHorizontalHeaderLabels(["Strategy", "Start %", "Peak %", "End %"])
        self.eco_table.setRowCount(n)
        for r, i in enumerate(order):
            peak = max(h[i] for h in hist)
            for c, val in enumerate([res.names[i], round(100 * hist[0][i], 2), round(100 * peak, 2),
                                     round(100 * final[i], 2)]):
                it = QTableWidgetItem(str(val))
                self.eco_table.setItem(r, c, it)
        self.eco_table.resizeColumnsToContents()
        dead = [res.names[i] for i in range(n) if final[i] == 0]
        self.status.showMessage(f"After {len(hist) - 1} generations: {res.names[order[0]]} leads "
                                f"({100 * final[order[0]]:.1f}%); {len(dead)} extinct."
                                + (f"  Some scores were zero or negative, so {shift:.2f} was added to every "
                                   "score first." if shift else ""))

    # ---------------------------------------------------------- evolve tab
    def build_evolve(self):
        w = QWidget()
        h = QHBoxLayout(w)

        # Left column: the settings and the buttons, with room to breathe.
        left = QWidget()
        left.setMaximumWidth(340)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        box = QGroupBox("Settings")
        form = QFormLayout(box)
        self.ga = {}
        for key, lab, lo, hi, val in (("gens", "Generations", 1, 1000, 50), ("pop", "Population", 4, 200, 20),
                                      ("turns", "Moves a game", 10, 1000, 151), ("seed", "Seed", 0, 10 ** 6, 1)):
            sb = QSpinBox()
            sb.setRange(lo, hi)
            sb.setValue(val)
            sb.setToolTip(GA_TIPS[key])
            self.ga[key] = sb
            form.addRow(lab + ":", sb)
        self.ga_mut = QDoubleSpinBox()
        self.ga_mut.setRange(0, 0.5)
        self.ga_mut.setDecimals(3)
        self.ga_mut.setSingleStep(0.005)
        self.ga_mut.setValue(0.01)
        self.ga_mut.setToolTip(GA_TIPS["mut"])
        form.addRow("Mutation:", self.ga_mut)
        note = QLabel("Opponents = the ticked strategies.  Noise and payoffs come from the Tournament tab.")
        note.setWordWrap(True)
        form.addRow(note)
        lv.addWidget(box)

        recipe = QPushButton("Load my recipe")
        recipe.setToolTip("Set everything as it was when the Evolved Reciprocator was bred")
        recipe.clicked.connect(self.load_recipe)
        lv.addWidget(recipe)
        row = QHBoxLayout()
        self.evo_btn = QPushButton("Evolve")
        self.evo_btn.clicked.connect(self.run_evolve)
        self.evo_stop = QPushButton("Stop")
        self.evo_stop.setEnabled(False)
        self.evo_stop.clicked.connect(self.stop_worker)
        row.addWidget(self.evo_btn)
        row.addWidget(self.evo_stop)
        lv.addLayout(row)
        self.evo_progress = QProgressBar()
        self.evo_progress.setFormat("generation %v of %m")
        self.evo_progress.setValue(0)
        lv.addWidget(self.evo_progress)
        self.evo_status = QLabel("No run yet.")
        self.evo_status.setWordWrap(True)
        lv.addWidget(self.evo_status)
        self.evo_show = QPushButton("Show results...")
        self.evo_show.setToolTip("Open the results window (it also shows a run in progress)")
        self.evo_show.setEnabled(False)
        self.evo_show.clicked.connect(self.show_results_window)
        lv.addWidget(self.evo_show)
        lv.addSpacing(12)
        self.evo_del = QPushButton("Remove a bred strategy...")
        self.evo_del.clicked.connect(self.remove_bred)
        lv.addWidget(self.evo_del)
        lv.addStretch()
        h.addWidget(left)

        # Right: the explanation gets the rest of the tab.
        self.evo_help = QTextBrowser()
        self.evo_help.setHtml(EVOLVE_HELP)
        h.addWidget(self.evo_help, 1)

        self.evo_result = None
        self.evo_dialog = None
        return w

    def results_window(self):
        """The (non-modal) results window, created on first use."""
        if self.evo_dialog is None:
            d = QDialog(self)
            d.setWindowTitle("Axelrod - breeding results")
            d.resize(980, 760)
            v = QVBoxLayout(d)
            split = QSplitter(Qt.Orientation.Vertical)
            self.evo_chart = LineChart()
            self.evo_chart.setMinimumHeight(260)
            split.addWidget(self.evo_chart)
            self.evo_text = QTextBrowser()
            self.evo_text.setHtml("<p>The bred table appears here when the run finishes.</p>")
            split.addWidget(self.evo_text)
            split.setSizes([330, 400])
            v.addWidget(split, 1)
            row = QHBoxLayout()
            self.evo_add = QPushButton("Add the best to the strategy list...")
            self.evo_add.setEnabled(self.evo_result is not None)
            self.evo_add.clicked.connect(self.add_bred)
            close = QPushButton("Close")
            close.clicked.connect(d.close)
            row.addWidget(self.evo_add)
            row.addStretch()
            row.addWidget(close)
            v.addLayout(row)
            self.evo_dialog = d
        return self.evo_dialog

    def show_results_window(self):
        d = self.results_window()
        self.refresh_results()
        d.show()
        d.raise_()
        d.activateWindow()

    def refresh_results(self):
        if self.evo_dialog is None:
            return
        hist = getattr(self, "evo_hist", [])
        if hist:
            n = getattr(self, "evo_gens", len(hist))
            self.evo_chart.set_data([("best", [x[0] for x in hist]), ("population mean", [x[1] for x in hist])],
                                    f"Generation {len(hist)} of {n}", "generation", "score per move")
        if self.evo_result is not None:
            r = self.evo_result
            cand = S.bred_class(r.best_table, r.best_premise, "this table")
            self.evo_text.setHtml(result_html(r, self.evo_names, character_html(cand)))
            self.evo_add.setEnabled(True)

    def load_recipe(self):
        """The settings used to breed the Evolved Reciprocator (seed 4 was
        the best of seeds 1-4)."""
        self.set_checked({c.name for c in S.REGISTRY if c.origin in (S.FIRST, S.SECOND)})
        self.preset.setCurrentIndex(-1)
        for key, val in (("gens", 60), ("pop", 24), ("turns", 151), ("seed", 4)):
            self.ga[key].setValue(val)
        self.ga_mut.setValue(0.01)
        self.noise.setValue(0)
        self.tell.setChecked(True)
        for k, val in (("T", 5), ("R", 3), ("P", 1), ("S", 0)):
            self.pay[k].setValue(val)
        self.status.showMessage("Recipe loaded: 23 first- and second-tournament entries ticked, 60 generations, "
                                "population 24, 151 moves, mutation 0.01, seed 4; noise 0 and standard payoffs "
                                "on the Tournament tab.  Press Evolve.")

    def run_evolve(self):
        opps = []
        for c, k in self.entries():
            opps += [c] * k
        if not opps:
            QMessageBox.information(self, "Axelrod", "Tick the strategies to breed against.")
            return
        st = self.current_settings()
        gens = self.ga["gens"].value()
        self.evo_hist = []
        self.evo_gens = gens
        self.evo_result = None
        if self.evo_dialog is not None:
            self.evo_add.setEnabled(False)
            self.evo_text.setHtml("<p>Breeding...  the bred table appears here when the run finishes.</p>")
        self.evo_progress.setMaximum(gens)
        self.evo_progress.setValue(0)
        self.evo_status.setText(f"Breeding against {len(opps)} opponents...")
        self.evo_show.setEnabled(True)

        def job(emit, cancelled):
            return evolve(opps, generations=gens, pop_size=self.ga["pop"].value(),
                          turns=self.ga["turns"].value(), mutation=self.ga_mut.value(),
                          seed=self.ga["seed"].value(), settings=st,
                          progress=lambda g, n, b, m: emit((g, n, b, m)), cancel=cancelled)

        def prog(x):
            g, n, b, m = x
            self.evo_hist.append((b, m))
            self.evo_progress.setValue(g)
            self.evo_status.setText(f"Generation {g} of {n}: best {b:.3f}, average {m:.3f} a move.")
            if self.evo_dialog is not None and self.evo_dialog.isVisible():
                self.refresh_results()

        self.evo_names = [c.name for c, _ in self.entries()]
        self.start(job, self.show_evolve, prog, "Evolving...")

    def show_evolve(self, r):
        self.evo_result = r
        self.evo_status.setText(f"Finished: best table scores {r.best_fitness:.3f} a move.  "
                                "Press Show results to see it and add it to the list.")
        self.refresh_results()

    def add_bred(self):
        r = self.evo_result
        if not r:
            return
        name, ok = QInputDialog.getText(self, "Name the strategy", "Name:",
                                        text=f"Bred {len(self.bred) + 1}")
        if not ok or not name.strip():
            return
        name = name.strip()
        if any(c.name == name for c in self.all_classes()):
            QMessageBox.information(self, "Axelrod", "That name is taken.")
            return
        note = (f"Bred over {len(r.history)} generations against: " + ", ".join(self.evo_names) + ".")
        self.bred.append(S.bred_class(r.best_table, r.best_premise, name, note))
        save_bred(self.bred)
        self.fill_tree()
        self.fill_match_combos()
        self.status.showMessage(f"Added {name} (saved in {BRED_FILE}).")

    def remove_bred(self):
        if not self.bred:
            QMessageBox.information(self, "Axelrod", "No bred strategies yet.")
            return
        name, ok = QInputDialog.getItem(self, "Remove", "Strategy:", [c.name for c in self.bred], 0, False)
        if ok:
            self.bred = [c for c in self.bred if c.name != name]
            save_bred(self.bred)
            self.fill_tree()
            self.fill_match_combos()

    # ---------------------------------------------------------- guide
    def build_guide(self):
        tb = QTextBrowser()
        parts = [INTRO, PAYOFF_GUIDE, "<h2>The strategies</h2>"]
        for g in S.GROUPS:
            members = [c for c in S.REGISTRY if c.origin == g]
            if not members:
                continue
            parts.append(f"<h2>{html.escape(g)}</h2>")
            for c in members:
                parts.append(strategy_html(c))
        parts.append("<h2>Sources</h2><ul>"
                     "<li>R. Axelrod, 'Effective Choice in the Prisoner's Dilemma', <i>Journal of Conflict "
                     "Resolution</i> 24 (1980) 3-25; 'More Effective Choice...', ibid. 379-403.</li>"
                     "<li>R. Axelrod, <i>The Evolution of Cooperation</i> (1984).</li>"
                     "<li>R. Axelrod, 'The Evolution of Strategies in the Iterated Prisoner's Dilemma' (1987).</li>"
                     "<li>J. Wu and R. Axelrod, 'How to Cope with Noise in the Iterated Prisoner's Dilemma', "
                     "<i>JCR</i> 39 (1995).</li>"
                     "<li>Press and Dyson, <i>PNAS</i> 109 (2012); Stewart and Plotkin, <i>PNAS</i> 109 (2012).</li>"
                     "<li>Kendall, Yao and Chong (eds.), <i>The Iterated Prisoners' Dilemma: 20 Years On</i> (2007).</li>"
                     "<li>The Axelrod-Python project (axelrod.readthedocs.io), used as a cross-check.</li></ul>")
        tb.setHtml("".join(parts))
        return tb

    # ---------------------------------------------------------- menu
    def build_menu(self):
        m = self.menuBar().addMenu("&File")
        a = QAction("Export results as CSV...", self)
        a.triggered.connect(self.export_csv)
        m.addAction(a)
        a = QAction("Quit", self)
        a.setShortcut("Ctrl+Q")
        a.triggered.connect(self.close)
        m.addAction(a)
        h = self.menuBar().addMenu("&Help")
        a = QAction("Guide", self)
        a.triggered.connect(lambda: self.tabs.setCurrentIndex(0))
        h.addAction(a)

    def closeEvent(self, ev):
        self.settings_store.setValue("geometry", self.saveGeometry())
        if self.worker and self.worker.isRunning():
            self.worker.cancelled = True
            self.worker.wait(3000)
        super().closeEvent(ev)


def main(argv):
    app = QApplication(argv)
    app.setApplicationName("Axelrod")
    app.setDesktopFileName("axelrod")
    icon = os.path.join(HERE, "icons", "axelrod.png")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))
    win = MainWindow()
    win.show()
    return app.exec()
