"""Iterated prisoner's dilemma engine: matches, round-robin tournaments,
Axelrod's ecological simulation and a genetic algorithm after Axelrod (1987).

Stdlib only.  Moves are the strings "C" and "D".
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

C, D = "C", "D"
FLIP = {C: D, D: C}


@dataclass
class Payoffs:
    """Standard names: T temptation, R reward, P punishment, S sucker."""
    T: float = 5.0
    R: float = 3.0
    P: float = 1.0
    S: float = 0.0

    def pair(self, a: str, b: str) -> tuple[float, float]:
        if a == C:
            return (self.R, self.R) if b == C else (self.S, self.T)
        return (self.T, self.S) if b == C else (self.P, self.P)

    def is_dilemma(self) -> bool:
        return self.T > self.R > self.P > self.S and 2 * self.R > self.T + self.S


@dataclass
class MatchInfo:
    """What a strategy is told before a match.

    length is the number of turns when the players know it (Axelrod's first
    tournament: 200), or None when the match ends at random (his second
    tournament: continuation probability w = 0.99654).
    """
    length: int | None
    payoffs: Payoffs
    noise: float = 0.0


@dataclass
class Settings:
    turns: int = 200                 # fixed length (used when w == 0)
    w: float = 0.0                   # continuation probability; > 0 = random length
    tell_length: bool = True         # strategies learn the length (fixed length only)
    repetitions: int = 5
    noise: float = 0.0               # chance each intended move is flipped
    self_play: bool = True           # each entry also meets its own twin
    payoffs: Payoffs = field(default_factory=Payoffs)
    seed: int = 1

    def draw_length(self, rng: random.Random) -> int:
        if self.w <= 0:
            return self.turns
        # Geometric: play a turn, continue with probability w.
        n = 1
        while rng.random() < self.w and n < 100000:
            n += 1
        return n


# --------------------------------------------------------------------- match

@dataclass
class MatchResult:
    a: list[str]          # moves actually made (after noise)
    b: list[str]
    score_a: float
    score_b: float

    @property
    def turns(self) -> int:
        return len(self.a)


def play_match(pa, pb, length: int, settings: Settings, rng: random.Random,
               seed_a: int | None = None, seed_b: int | None = None) -> MatchResult:
    """Play two fresh strategy instances against each other."""
    told = length if (settings.w <= 0 and settings.tell_length) else None
    info = MatchInfo(told, settings.payoffs, settings.noise)
    pa.reset(info, random.Random(rng.random() if seed_a is None else seed_a))
    pb.reset(info, random.Random(rng.random() if seed_b is None else seed_b))
    ha: list[str] = []
    hb: list[str] = []
    sa = sb = 0.0
    noise = settings.noise
    pay = settings.payoffs
    for _ in range(length):
        ma = pa.move(ha, hb)
        mb = pb.move(hb, ha)
        if noise:
            if rng.random() < noise:
                ma = FLIP[ma]
            if rng.random() < noise:
                mb = FLIP[mb]
        x, y = pay.pair(ma, mb)
        sa += x
        sb += y
        ha.append(ma)
        hb.append(mb)
    return MatchResult(ha, hb, sa, sb)


# ---------------------------------------------------------------- tournament

@dataclass
class Standing:
    name: str
    mean: float            # mean score per turn over all its matches
    per_match: float       # mean score per match (Axelrod's reporting unit)
    wins: int              # matches it outscored its opponent
    coop: float            # share of its moves that were C
    rank: int = 0


@dataclass
class TournamentResult:
    names: list[str]
    matrix: list[list[float]]       # matrix[i][j] = i's mean per-turn score vs j
    coop_matrix: list[list[float]]  # i's cooperation rate vs j
    standings: list[Standing]
    settings: Settings
    mean_turns: float


def entry_names(classes_with_copies) -> list[str]:
    names = []
    for cls, copies in classes_with_copies:
        for k in range(copies):
            names.append(cls.name if copies == 1 else f"{cls.name} #{k + 1}")
    return names


def run_tournament(entries, settings: Settings, progress=None, cancel=None) -> TournamentResult:
    """Round robin.  entries: list of (strategy class, copies).

    Every pair meets settings.repetitions times; with self_play each entry
    also meets a twin of itself (as in Axelrod's tournaments).
    """
    classes = []
    for cls, copies in entries:
        classes += [cls] * max(1, copies)
    names = entry_names(entries)
    n = len(classes)
    rng = random.Random(settings.seed)
    tot = [[0.0] * n for _ in range(n)]
    turns = [[0] * n for _ in range(n)]
    coops = [[0] * n for _ in range(n)]
    wins = [0] * n
    pairs = [(i, j) for i in range(n) for j in range(i, n) if i != j or settings.self_play]
    total_jobs = len(pairs) * settings.repetitions
    done = 0
    turn_sum = 0
    for rep in range(settings.repetitions):
        # Same match length for every pair within a repetition (as Axelrod did).
        length = settings.draw_length(rng)
        for i, j in pairs:
            if cancel and cancel():
                raise InterruptedError
            r = play_match(classes[i](), classes[j](), length, settings, rng)
            turn_sum += r.turns
            if i == j:
                # Twin match: count it once for the entry, as its average.
                tot[i][i] += (r.score_a + r.score_b) / 2
                turns[i][i] += r.turns
                coops[i][i] += (r.a.count(C) + r.b.count(C)) / 2
            else:
                tot[i][j] += r.score_a
                tot[j][i] += r.score_b
                turns[i][j] += r.turns
                turns[j][i] += r.turns
                coops[i][j] += r.a.count(C)
                coops[j][i] += r.b.count(C)
                if r.score_a > r.score_b:
                    wins[i] += 1
                elif r.score_b > r.score_a:
                    wins[j] += 1
            done += 1
            if progress and done % 20 == 0:
                progress(done, total_jobs)
    matrix = [[(tot[i][j] / turns[i][j]) if turns[i][j] else float("nan") for j in range(n)] for i in range(n)]
    cmat = [[(coops[i][j] / turns[i][j]) if turns[i][j] else float("nan") for j in range(n)] for i in range(n)]
    standings = []
    for i in range(n):
        cols = [j for j in range(n) if turns[i][j]]
        t = sum(turns[i][j] for j in cols)
        mean = sum(tot[i][j] for j in cols) / t if t else 0.0
        matches = len(cols) * settings.repetitions
        per_match = sum(tot[i][j] for j in cols) / matches if matches else 0.0
        coop = sum(coops[i][j] for j in cols) / t if t else 0.0
        standings.append(Standing(names[i], mean, per_match, wins[i], coop))
    order = sorted(range(n), key=lambda k: -standings[k].mean)
    for rank, k in enumerate(order, 1):
        standings[k].rank = rank
    if progress:
        progress(total_jobs, total_jobs)
    return TournamentResult(names, matrix, cmat, standings, settings,
                            turn_sum / max(1, total_jobs))


# ---------------------------------------------------------------- ecology

def ecological(matrix: list[list[float]], generations: int = 1000,
               shares: list[float] | None = None) -> list[list[float]]:
    """Axelrod's ecological analysis (The Evolution of Cooperation, ch. 2).

    Each generation a strategy's share grows in proportion to its average
    score against the current population mix.  Returns the share history.
    """
    n = len(matrix)
    x = list(shares) if shares else [1.0 / n] * n
    hist = [x[:]]
    m = [[0.0 if math.isnan(v) else v for v in row] for row in matrix]
    shift = ecology_shift(matrix)
    if shift:
        m = [[v + shift for v in row] for row in m]
    for _ in range(generations):
        fit = [sum(m[i][j] * x[j] for j in range(n)) for i in range(n)]
        new = [x[i] * fit[i] for i in range(n)]
        tot = sum(new)
        if tot <= 0:
            break
        x = [v / tot for v in new]
        # Treat vanishingly small shares as extinct.
        x = [v if v > 1e-9 else 0.0 for v in x]
        tot = sum(x)
        x = [v / tot for v in x]
        hist.append(x[:])
    return hist


def ecology_shift(matrix) -> float:
    """Growth in proportion to score needs every score above zero.  When some
    are zero or negative, return the amount added to all of them so the
    lowest becomes a tenth of the score range (or 0.1 if all are equal)."""
    vals = [v for row in matrix for v in row if not math.isnan(v)]
    if not vals or min(vals) > 0:
        return 0.0
    lo, hi = min(vals), max(vals)
    return -lo + (0.1 * (hi - lo) if hi > lo else 0.1)


def classify(p: Payoffs) -> tuple[str, str]:
    """Name the game these payoffs make, and a plain-language reason.

    Two questions sort every symmetric 2x2 game: what is the better reply
    when the other cooperates (T vs R) and when it defects (P vs S)?  That
    gives four families - defect regardless, cooperate regardless, copy the
    other, do the opposite - and within each, whether mutual cooperation
    (R) beats mutual defection (P) decides the name.
    """
    T, R, P, S = p.T, p.R, p.P, p.S
    if T == R or P == S or R == P:
        ties = []
        if T == R:
            ties.append("T = R: cheating a cooperator gains nothing")
        if P == S:
            ties.append("P = S: cooperating with a defector costs nothing")
        if R == P:
            ties.append("R = P: mutual cooperation earns no more than mutual defection")
        return "A game with ties", "; ".join(ties) + ", so some choices make no difference."
    tempted = T > R          # better to defect when the other cooperates
    afraid = P > S           # better to defect when the other defects
    joint = R > P            # both better off cooperating than defecting
    if tempted and afraid:
        if not joint:
            return "Deadlock", ("Defecting is best whatever the other does, and mutual defection (P) also "
                                "beats mutual cooperation (R): nothing to cooperate for.")
        if 2 * R > T + S:
            return "Prisoner's dilemma", "T > R > P > S and 2R > T + S."
        return ("Prisoner's dilemma with turn-taking",
                "T > R > P > S, but 2R is not more than T + S, so taking turns cheating pays as well as cooperating.")
    if not tempted and not afraid:
        if joint:
            return "Harmony", "Cooperating is best whatever the other does, and good for both: no conflict."
        return "Reversed dilemma", ("Cooperating is best whatever the other does, yet mutual defection (P) "
                                    "would be better for both than mutual cooperation (R).")
    if not tempted and afraid:      # best reply = copy the other
        if joint:
            return "Stag hunt (assurance game)", ("The best reply is to do what the other does, and mutual "
                                                   "cooperation is the better match: hold your post for the "
                                                   "shared stag, or leave for a sure hare if you doubt the other.")
        return "Coordination on defection", ("The best reply is to do what the other does, and mutual "
                                              "defection (P) is the better match.")
    # tempted and not afraid: best reply = do the opposite of the other
    if not joint:
        return "Anti-coordination", ("The best reply is to do the opposite of the other, and mutual "
                                     "cooperation (R) is the worst result of all.")
    if R > S:
        return "Chicken (hawk-dove, snowdrift)", ("The best reply is to do the opposite of the other; "
                                                   "being cheated (S) beats mutual defection (P).")
    if T > S:
        return "Leader (battle of the sexes)", ("The best reply is to do the opposite of the other; even the "
                                                 "cheated player (S) does better than mutual cooperation (R), "
                                                 "but the cheater (T) does best.")
    return "Hero", ("The best reply is to do the opposite of the other, and the cheated player (S) does "
                    "best of all: whoever 'gives in' by cooperating is the winner.")


# ---------------------------------------------------------------- genetics

def gene_index(me: list[str], opp: list[str], premise: str) -> int:
    """Index (0-63) of the last three rounds, padded by the 6-move premise.

    Rounds are read oldest first, each as (my move, their move), D = 1 bit.
    """
    pairs = []
    pad = [(premise[2 * k], premise[2 * k + 1]) for k in range(3)]
    hist = pad + list(zip(me, opp))
    for a, b in hist[-3:]:
        pairs += [a, b]
    idx = 0
    for m in pairs:
        idx = idx * 2 + (1 if m == D else 0)
    return idx


def make_lookup_class(table: str, premise: str, name: str):
    from .strategies import LookupStrategy
    return type("Lookup", (LookupStrategy,), dict(name=name, table=table, premise=premise))


@dataclass
class GAResult:
    best_table: str
    best_premise: str
    best_fitness: float
    history: list[tuple[float, float]]   # (best, mean) per generation


def evolve(opponents, generations=50, pop_size=20, turns=151, mutation=0.01,
           crossover=0.6, seed=1, settings: Settings | None = None,
           progress=None, cancel=None) -> GAResult:
    """Axelrod (1987): 70-gene chromosomes, fitness = mean score per turn
    against a fixed environment of strategies, sigma-scaled roulette selection,
    one-point crossover, point mutation."""
    rng = random.Random(seed)
    st = settings or Settings()
    st = Settings(turns=turns, w=0.0, tell_length=st.tell_length, repetitions=1,
                  noise=st.noise, payoffs=st.payoffs, seed=seed)
    L = 70

    def rand_chrom():
        return "".join(rng.choice("CD") for _ in range(L))

    def fitness(ch):
        cls = make_lookup_class(ch[:64], ch[64:], "candidate")
        tot = 0.0
        for opp in opponents:
            r = play_match(cls(), opp(), turns, st, rng)
            tot += r.score_a / turns
        return tot / len(opponents)

    pop = [rand_chrom() for _ in range(pop_size)]
    history = []
    best = (None, -1.0)
    for g in range(generations):
        if cancel and cancel():
            raise InterruptedError
        fits = [fitness(ch) for ch in pop]
        for ch, f in zip(pop, fits):
            if f > best[1]:
                best = (ch, f)
        mean = sum(fits) / len(fits)
        sd = math.sqrt(sum((f - mean) ** 2 for f in fits) / len(fits))
        history.append((max(fits), mean))
        if progress:
            progress(g + 1, generations, max(fits), mean)
        # Sigma scaling: expected offspring 1 + (f - mean) / sd, clipped.
        weights = [max(0.0, 1 + (f - mean) / sd) if sd > 1e-9 else 1.0 for f in fits]
        if sum(weights) <= 0:
            weights = [1.0] * len(fits)
        new = [best[0]]  # keep the best ever (elitism)
        while len(new) < pop_size:
            p1, p2 = rng.choices(pop, weights, k=2)
            if rng.random() < crossover:
                cut = rng.randrange(1, L)
                c1, c2 = p1[:cut] + p2[cut:], p2[:cut] + p1[cut:]
            else:
                c1, c2 = p1, p2
            for c in (c1, c2):
                c = "".join(FLIP[m] if rng.random() < mutation else m for m in c)
                if len(new) < pop_size:
                    new.append(c)
        pop = new
    ch = best[0]
    return GAResult(ch[:64], ch[64:], best[1], history)
