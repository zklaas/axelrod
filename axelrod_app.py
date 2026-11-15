#!/usr/bin/env python3
"""Axelrod - test strategies for the iterated prisoner's dilemma.

    axelrod                      open the window
    axelrod list                 every strategy, with a one-line summary
    axelrod explain NAME         full explanation of one strategy
    axelrod run [options]        a tournament in the terminal
    axelrod match A B [options]  one match, move by move
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ipd import strategies as S  # noqa: E402
from ipd.engine import Payoffs, Settings, ecological, play_match, run_tournament  # noqa: E402

FIELDS = {
    "first": ("Axelrod's first tournament", lambda c: c.origin == S.FIRST, 0.0),
    "second": ("Axelrod's second tournament (entries here)",
               lambda c: c.origin == S.SECOND or c.name in ("Tit For Tat", "Random"), 0.99654),
    "mine": ("New strategies vs both tournaments", lambda c: c.origin in (S.FIRST, S.SECOND, S.MINE), 0.99654),
    "all": ("Everything", lambda c: True, 0.0),
}


def wrap(s, indent="    "):
    return textwrap.fill(s, 88, initial_indent=indent, subsequent_indent=indent)


def find(name):
    cls = S.by_name(name)
    if cls is None:
        from ipd.gui import load_bred
        key = name.strip().lower()
        cls = next((c for c in load_bred() if c.name.lower() == key), None)
    if cls is None:
        sys.exit(f"No strategy matches '{name}'.  Try: axelrod list")
    return cls


def cmd_list(a):
    for g in S.GROUPS:
        members = [c for c in S.REGISTRY if c.origin == g]
        if not members:
            continue
        print(f"\n{g}")
        for c in members:
            print(f"  {c.name}" + (f"  ({c.place})" if c.place else ""))
            print(wrap(c.gist))


def cmd_explain(a):
    from ipd.profile import describe
    cls = find(" ".join(a.name))
    text = S.strategy_info(cls)
    print("\n".join(textwrap.fill(p, 88) if p else "" for p in text.split("\n")))
    print("\nCharacter (measured in probe games):")
    for k, v in describe(cls):
        print(textwrap.fill(f"{k}: {v}", 88, initial_indent="  ", subsequent_indent="    "))


def settings_from(a, w_default=0.0):
    w = a.w if a.w is not None else w_default
    return Settings(turns=a.turns, w=w, tell_length=not a.secret_length, repetitions=a.reps,
                    noise=a.noise / 100, self_play=not a.no_self, payoffs=Payoffs(*a.payoffs), seed=a.seed)


def cmd_run(a):
    title, pick, w = FIELDS[a.field]
    entries = [(c, 1) for c in S.REGISTRY if pick(c)]
    for extra in a.add or []:
        cls = find(extra)
        if cls not in [c for c, _ in entries]:
            entries.append((cls, 1))
    st = settings_from(a, w)
    res = run_tournament(entries, st)
    length = f"{st.turns} moves" if st.w <= 0 else f"random length, w={st.w} (mean {res.mean_turns:.0f})"
    print(f"{title}: {len(entries)} entrants, {st.repetitions} repetitions, {length}, noise {a.noise:g}%")
    print(f"{'#':>3}  {'Strategy':30} {'/move':>6} {'/match':>8} {'won':>4} {'coop%':>6}")
    for s in sorted(res.standings, key=lambda s: s.rank):
        print(f"{s.rank:3}  {s.name:30} {s.mean:6.3f} {s.per_match:8.1f} {s.wins:4} {100 * s.coop:6.1f}")
    if a.ecology:
        hist = ecological(res.matrix, a.ecology)
        fin = hist[-1]
        print(f"\nEcology after {a.ecology} generations:")
        for i in sorted(range(len(fin)), key=lambda i: -fin[i])[:10]:
            print(f"  {res.names[i]:30} {100 * fin[i]:6.2f}%")


def cmd_match(a):
    A, B = find(a.a), find(a.b)
    st = settings_from(a)
    rng = random.Random(a.seed)
    length = st.draw_length(rng)          # a.turns when fixed, random when --w is given
    r = play_match(A(), B(), length, st, rng)
    for k in range(0, r.turns, 50):
        print(f"{k + 1:4}  A {''.join(r.a[k:k + 50])}")
        print(f"      B {''.join(r.b[k:k + 50])}")
    print("\n" + (f"Fixed length, {length} moves, players {'told' if st.tell_length else 'not told'}."
                  if st.w <= 0 else f"Random length (w = {st.w:g}): {length} moves, players not told."))
    print(f"A {A.name}: {r.score_a:g} ({r.score_a / r.turns:.3f} a move)")
    print(f"B {B.name}: {r.score_b:g} ({r.score_b / r.turns:.3f} a move)")


def common(p):
    p.add_argument("--turns", type=int, default=200, help="match length (default 200)")
    p.add_argument("--w", type=float, default=None, help="random length: continuation probability, e.g. 0.99654")
    p.add_argument("--secret-length", action="store_true", help="don't tell strategies the length")
    p.add_argument("--reps", type=int, default=5)
    p.add_argument("--noise", type=float, default=0.0, help="percent chance a move is flipped")
    p.add_argument("--no-self", action="store_true", help="no matches against own twin")
    p.add_argument("--payoffs", type=float, nargs=4, default=[5, 3, 1, 0], metavar=("T", "R", "P", "S"))
    p.add_argument("--seed", type=int, default=1)


def main():
    if len(sys.argv) == 1 or sys.argv[1] in ("gui",):
        from ipd.gui import main as gui_main
        return gui_main(sys.argv[:1])
    ap = argparse.ArgumentParser(prog="axelrod", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list strategies").set_defaults(fn=cmd_list)
    p = sub.add_parser("explain", help="explain a strategy")
    p.add_argument("name", nargs="+")
    p.set_defaults(fn=cmd_explain)
    p = sub.add_parser("run", help="run a tournament")
    p.add_argument("--field", choices=sorted(FIELDS), default="first")
    p.add_argument("--add", action="append", help="add a strategy to the field (repeatable)")
    p.add_argument("--ecology", type=int, default=0, metavar="GENERATIONS")
    common(p)
    p.set_defaults(fn=cmd_run)
    p = sub.add_parser("match", help="play one match")
    p.add_argument("a")
    p.add_argument("b")
    common(p)
    p.set_defaults(fn=cmd_match)
    a = ap.parse_args()
    a.fn(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
