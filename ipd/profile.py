"""Character sketch of a strategy: how aggressive, retaliatory, forgiving
and responsive it is, measured by probe matches against simple test
opponents and (for lookup tables) by reading the table itself."""
from __future__ import annotations

import random

from .engine import C, D, Settings, gene_index, play_match
from . import strategies as S

PROBE_TURNS = 100


def _lapses(n):
    """Cooperates, except n defections in a row from move 11."""
    class Lapse(S.Strategy):
        name = f"{n} lapses"

        def move(self, me, opp):
            return D if 10 <= len(me) < 10 + n else C
    return Lapse


def _play(cls, opp, seed=1, turns=PROBE_TURNS):
    st = Settings(turns=turns, tell_length=False)
    return play_match(cls(), opp(), turns, st, random.Random(seed))


def _runs(cls, opp, runs, turns=PROBE_TURNS):
    return [_play(cls, opp, seed=k, turns=turns) for k in range(runs)]


def _settled(r, start):
    """Move (1-based) from which both cooperate to the end, or None."""
    for k in range(start, r.turns - 20):
        if all(x == C for x in r.a[k:]) and all(x == C for x in r.b[k:]):
            return k + 1
    return None


def _recovery(rs, start, usual):
    """(share of runs where its cooperation over the last 30 moves is back to
    its usual level, mean moves until steady cooperation or None, its
    cooperation over the last 30 moves)."""
    back = [r for r in rs if r.a[-30:].count(C) / 30 >= usual - 0.1]
    times = [x for x in (_settled(r, start) for r in back) if x is not None]
    late = sum(r.a[-30:].count(C) for r in rs) / (30 * len(rs))
    return (len(back) / len(rs), (sum(times) / len(times) - start) if times else None, late)


def measure(cls) -> dict:
    runs = 20 if cls.stochastic else 1
    m = {}
    allc = _runs(cls, S.AllC, runs)
    m["d_vs_allc"] = sum(r.a.count(D) for r in allc) / (runs * PROBE_TURNS)
    firsts = [r.a.index(D) + 1 for r in allc if D in r.a]
    m["first_defect_vs_allc"] = min(firsts) if firsts else None
    m["d_vs_tft"] = sum(r.a.count(D) for r in _runs(cls, S.TitForTat, runs)) / (runs * PROBE_TURNS)
    alld = _runs(cls, S.AllD, runs)
    m["c_vs_alld"] = sum(r.a.count(C) for r in alld) / (runs * PROBE_TURNS)
    m["c_vs_allc"] = 1 - m["d_vs_allc"]
    # Retaliation: chance it defects right after 1, 2, 3 defections in a
    # row from a cooperative partner, over and above its usual rate.
    m["answer"] = {}
    m["settle"] = {}
    for n in (1, 2, 3):
        rs = _runs(cls, _lapses(n), runs)
        reply = [r.a[10 + n] for r in rs]     # its move right after the n-th defection
        m["answer"][n] = max(0.0, reply.count(D) / len(reply) - m["d_vs_allc"])
        m["settle"][n] = _recovery(rs, 10 + n, m["c_vs_allc"])
    # Reconciliation: 10 defections, then cooperation for good.
    m["reconcile"] = _recovery(_runs(cls, _lapses(10), runs), 20, m["c_vs_allc"])
    if cls.stochastic:   # streak timings only mean something without dice
        m["settle"] = {n: (f, None, late) for n, (f, _, late) in m["settle"].items()}
        f, _, late = m["reconcile"]
        m["reconcile"] = (f, None, late)
    # Reaction to the latest move, against a random player.
    cc = cn = dc = dn = 0
    for k in range(10):
        r = _play(cls, S.RandomPlayer, seed=100 + k, turns=300)
        for t in range(1, r.turns):
            if r.b[t - 1] == C:
                cn += 1
                cc += r.a[t] == C
            else:
                dn += 1
                dc += r.a[t] == C
    m["c_after_c"] = cc / cn if cn else 0
    m["c_after_d"] = dc / dn if dn else 0
    return m


def table_facts(table: str) -> dict:
    """What the 64 entries depend on."""
    def idx(bits):
        return int("".join("1" if x == D else "0" for x in bits), 2)
    opp_last = own_last = opp_any = 0
    for i in range(64):
        bits = list(format(i, "06b").replace("0", C).replace("1", D))
        # positions: 0 my1 1 their1 2 my2 3 their2 4 my3 5 their3 (3 = latest)
        def flipped(pos):
            b = bits[:]
            b[pos] = C if b[pos] == D else D
            return table[idx(b)] != table[i]
        opp_last += flipped(5)
        own_last += flipped(4)
        opp_any += any(flipped(p) for p in (1, 3, 5))
    tft = sum(1 for i in range(64) if table[i] == format(i, "06b").replace("0", C).replace("1", D)[5])
    return dict(opp_last=opp_last / 64, own_last=own_last / 64, opp_any=opp_any / 64,
                coop_entries=table.count(C), like_tft=tft)


def _level(x, cuts, words):
    for c, w in zip(cuts, words):
        if x <= c:
            return w
    return words[-1]


def describe(cls) -> list[tuple[str, str]]:
    """(trait, plain sentence) pairs."""
    m = measure(cls)
    out = []
    pct = lambda x: f"{100 * x:.0f}%"  # noqa: E731
    # Aggression
    if m["first_defect_vs_allc"] is None and m["d_vs_tft"] == 0:
        out.append(("Aggression", "None. It is never the first to defect (Axelrod's 'nice')."))
    else:
        share = m["d_vs_allc"]
        word = _level(share, (0.05, 0.25, 0.6), ("Low", "Moderate", "High", "Very high"))
        out.append(("Aggression", f"{word}. Against a partner who always cooperates it first defects on move "
                    f"{m['first_defect_vs_allc']} and defects on {pct(share)} of moves."))
    # Retaliation
    if m["d_vs_allc"] >= 0.9:
        out.append(("Retaliation", "Not applicable: it defects whatever the other does."))
    else:
        a = m["answer"]
        if a[1] >= 0.8:
            txt = "Immediate. It answers even a single defection."
        elif a[1] >= 0.2:
            txt = f"Occasional. It answers a single defection about {pct(a[1])} of the time."
        elif a[2] >= 0.5:
            txt = ("Patient. It lets a single defection pass but answers two in a row."
                   if a[1] < 0.2 else "Patient. It answers two defections in a row.")
        elif a[3] >= 0.5:
            txt = "Very patient. It lets one or two defections in a row pass and answers only three."
        elif max(a.values()) > 0.1:
            txt = "Weak. Defections are seldom answered."
        else:
            txt = "None. Even three defections in a row go unanswered."
        out.append(("Retaliation", txt))
    # Forgiveness
    if m["d_vs_allc"] < 0.9:
        outcome = {}
        for n in (1, 2, 3):
            frac, after, late = m["settle"][n]
            if frac >= 0.9:
                txt = "cooperation returns" + ("" if after is None else " at once" if after <= 2
                                                else f" within about {after:.0f} moves")
            elif frac > 0:
                txt = f"cooperation returns in only {pct(frac)} of trials"
            else:
                txt = f"it never goes back to full cooperation and ends up defecting on {pct(1 - late)} of moves"
            outcome.setdefault(txt, []).append(n)
        names = {1: "one", 2: "two", 3: "three"}
        parts = []
        for txt, ns in outcome.items():
            if len(ns) == 3:
                when = "after one, two or three defections in a row"
            elif len(ns) == 2:
                when = f"after {names[ns[0]]} or {names[ns[1]]} defections in a row"
            else:
                when = ("after a single defection" if ns[0] == 1 else f"after {names[ns[0]]} defections in a row")
            parts.append(f"{when}, {txt}")
        n_ok = sum(1 for n in (1, 2, 3) if m["settle"][n][0] >= 0.9)
        word = {3: "Forgiving", 0: "Unforgiving"}.get(n_ok, "Partly forgiving")
        out.append(("Forgiveness", f"{word}. Against a partner who goes straight back to cooperating: "
                    + "; ".join(parts) + "."))
        frac, after, late = m["reconcile"]
        if frac >= 0.9:
            out.append(("Reconciliation", "Makes peace with a player who defected for 10 moves and then reformed"
                        + ("." if after is None or after <= 2 else f" (within about {after:.0f} moves).")))
        else:
            out.append(("Reconciliation", "Does not make peace with a player who defected for 10 moves and "
                        f"then reformed: it ends up defecting on {pct(1 - late)} of moves against it."))
    # Responsiveness
    gap = m["c_vs_allc"] - m["c_vs_alld"]
    word = _level(abs(gap), (0.15, 0.4, 0.75), ("Hardly", "Somewhat", "Strongly", "Almost entirely"))
    out.append(("Responsiveness", f"{word} shaped by the other's behaviour: it cooperates on "
                f"{pct(m['c_vs_allc'])} of moves with a constant cooperator and {pct(m['c_vs_alld'])} with a "
                f"constant defector.  Against a random player it cooperates {pct(m['c_after_c'])} of the time "
                f"after a cooperation and {pct(m['c_after_d'])} after a defection (Tit for Tat: 100% and 0%)."))
    # Defence
    c = m["c_vs_alld"]
    if c <= 0.03:
        out.append(("Defence", "Firm. It gives a steady defector almost nothing."))
    else:
        out.append(("Defence", f"Exploitable. It still cooperates on {pct(c)} of moves against Always Defect."))
    table = getattr(cls, "table", None)
    if table and len(table) == 64:
        f = table_facts(table)
        out.append(("Table", f"Changing only the other's latest move changes its reply in {pct(f['opp_last'])} "
                    f"of the 64 situations; changing only its own latest move, in {pct(f['own_last'])}.  It agrees "
                    f"with Tit for Tat in {f['like_tft']} of 64 and cooperates in {f['coop_entries']} of 64."))
    return out


def describe_text(cls) -> str:
    return "  ".join(f"{k}: {v}" for k, v in describe(cls))


_CACHE: dict = {}


def character_html(cls) -> str:
    """Cached HTML block for a strategy's measured character."""
    import html
    key = (cls.name, getattr(cls, "table", None), getattr(cls, "premise", None))
    if key not in _CACHE:
        rows = "".join(f"<tr><td valign=top><b>{html.escape(k)}</b></td><td>{html.escape(v)}</td></tr>"
                       for k, v in describe(cls))
        _CACHE[key] = ("<h4>Character (measured)</h4>"
                       "<p><small>From probe games: a partner who always cooperates, one who always "
                       "defects, partners who lapse once, twice or three times in a row and then "
                       "cooperate, one who defects for 10 moves and then reforms, and a random "
                       "player.</small></p><table cellpadding=3>" + rows + "</table>")
    return _CACHE[key]
