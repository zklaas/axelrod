"""Strategies for the iterated prisoner's dilemma.

Historical entries follow the rules as Axelrod described them in "Effective
Choice in the Prisoner's Dilemma" and "More Effective Choice in the
Prisoner's Dilemma" (Journal of Conflict Resolution 24, 1980) and The
Evolution of Cooperation (1984), cross-checked with the re-implementations in
the open-source Axelrod-Python project.  Where the original program text is
lost, the strategy says so in its notes ("reconstructed").

Each strategy is a class; a fresh instance plays each match.  move(me, opp)
receives both histories so far and returns "C" or "D".
"""
from __future__ import annotations

import math

from .engine import C, D, MatchInfo, gene_index

FIRST = "Axelrod's first tournament (1980)"
SECOND = "Axelrod's second tournament (1980)"
LATER = "Noise, evolution and later tournaments"
BASE = "Baselines"
MINE = "New strategies (Claude)"
BRED = "Bred in this app"
GROUPS = [FIRST, SECOND, LATER, BASE, MINE, BRED]

REGISTRY: list[type] = []


def register(cls):
    REGISTRY.append(cls)
    return cls


class Strategy:
    name = "?"
    author = ""
    origin = BASE
    place = ""          # finishing place in the original tournament
    stochastic = False
    blurb = ""
    gist = ""           # one-line plain-language summary

    def reset(self, info: MatchInfo, rng):
        self.info = info
        self.rng = rng
        self.init()

    def init(self):
        pass

    def move(self, me: list[str], opp: list[str]) -> str:
        raise NotImplementedError

    # helpers
    def scores(self, me, opp):
        a = b = 0.0
        pay = self.info.payoffs
        for x, y in zip(me, opp):
            p, q = pay.pair(x, y)
            a += p
            b += q
        return a, b

    def chance(self, p: float) -> bool:
        return self.rng.random() < p


def tft(opp):
    return opp[-1] if opp else C


# ======================================================== first tournament

@register
class TitForTat(Strategy):
    name = "Tit For Tat"
    author = "Anatol Rapoport"
    origin = FIRST
    place = "1st of 15 (and 1st of 63 in the second)"
    blurb = ("Cooperate on the first move, then do whatever the other player did "
             "on the previous move.  The shortest program entered, and the winner "
             "of both of Axelrod's tournaments: nice, retaliatory, forgiving and clear.")

    def move(self, me, opp):
        return tft(opp)


@register
class TidemanChieruzzi(Strategy):
    name = "Tideman and Chieruzzi"
    author = "T. Nicolaus Tideman and Paula Chieruzzi"
    origin = FIRST
    place = "2nd of 15"
    blurb = ("Tit for Tat with lengthening punishments: each new run of the other's "
             "defections is answered by one more defection than the last.  It gives "
             "the other a 'fresh start' (two cooperations, records wiped) when it is "
             "at least 10 points ahead, the other just cooperated, 20 moves have "
             "passed since the last fresh start, 10+ moves remain, and the other's "
             "defections differ from a 50-50 random player by over 3 standard deviations.")

    def init(self):
        self.retaliations = 0      # length of the last punishment
        self.punish_left = 0
        self.last_fresh = 0
        self.fresh_pending = False
        self.def_count = 0         # opponent defections since last fresh start
        self.base = 0              # index of last fresh start

    def move(self, me, opp):
        t = len(me)
        if t == 0:
            return C
        if opp[-1] == D:
            self.def_count += 1
        if self.fresh_pending:
            self.fresh_pending = False
            return C
        length = self.info.length or 200
        if (t - self.last_fresh >= 20 or self.last_fresh == 0) and opp[-1] == C \
                and length - t >= 10:
            mine, theirs = self.scores(me, opp)
            if mine - theirs >= 10:
                n = t - self.base
                sd = math.sqrt(n) / 2
                if abs(self.def_count - n / 2) > 3 * sd:
                    self.fresh_pending = True
                    self.last_fresh = t
                    self.base = t
                    self.retaliations = 0
                    self.punish_left = 0
                    self.def_count = 0
                    return C
        if self.punish_left > 0:
            self.punish_left -= 1
            return D
        # A new defection run starts when they defect after cooperating.
        if opp[-1] == D and (t < 2 or opp[-2] == C):
            self.retaliations += 1
            self.punish_left = self.retaliations - 1
            return D
        return tft(opp)


@register
class Nydegger(Strategy):
    name = "Nydegger"
    author = "Rudy Nydegger"
    origin = FIRST
    place = "3rd of 15"
    blurb = ("Tit for Tat for three moves (defecting on the third if it was the only "
             "one to cooperate on move one and the only one to defect on move two). "
             "Then it scores the last three rounds - 0 both cooperated, 2 only the "
             "other defected, 1 only Nydegger defected, 3 both defected - as "
             "A = 16a1 + 4a2 + a3, and defects only for 19 listed values of A.")
    DEFECT_ON = {1, 6, 7, 17, 22, 23, 26, 29, 30, 31, 33, 38, 39, 45, 49, 54, 55, 58, 61}
    VAL = {(C, C): 0, (C, D): 2, (D, C): 1, (D, D): 3}

    def move(self, me, opp):
        t = len(me)
        if t == 0:
            return C
        if t == 1:
            return tft(opp)
        if t == 2:
            if opp[0] == D and me[0] == C and me[1] == D and opp[1] == C:
                return D
            return tft(opp)
        a1 = self.VAL[(me[-1], opp[-1])]
        a2 = self.VAL[(me[-2], opp[-2])]
        a3 = self.VAL[(me[-3], opp[-3])]
        return D if 16 * a1 + 4 * a2 + a3 in self.DEFECT_ON else C


@register
class Grofman(Strategy):
    name = "Grofman"
    author = "Bernard Grofman"
    origin = FIRST
    place = "4th of 15"
    stochastic = True
    blurb = ("Cooperates whenever both players did the same thing last move; when "
             "they did different things it cooperates with probability 2/7.")

    def move(self, me, opp):
        if not me or me[-1] == opp[-1]:
            return C
        return C if self.chance(2 / 7) else D


@register
class Shubik(Strategy):
    name = "Shubik"
    author = "Martin Shubik"
    origin = FIRST
    place = "5th of 15"
    blurb = ("Tit for Tat with escalating retaliation: the first time the other "
             "defects while Shubik is cooperating it defects once, the next time "
             "twice, and so on.")

    def init(self):
        self.level = 0
        self.left = 0

    def move(self, me, opp):
        if not me:
            return C
        if self.left > 0:
            self.left -= 1
            return D
        if opp[-1] == D and me[-1] == C:
            self.level += 1
            self.left = self.level - 1
            return D
        return C


@register
class SteinRapoport(Strategy):
    name = "Stein and Rapoport"
    author = "William Stein and Amnon Rapoport"
    origin = FIRST
    place = "6th of 15"
    blurb = ("Cooperates on the first four moves, defects on the last two, and "
             "otherwise plays Tit for Tat - except that every 15 moves it runs a "
             "chi-squared test, and if the other player looks random it defects.")

    def init(self):
        self.random_opp = False

    def move(self, me, opp):
        t = len(me)
        if t < 4:
            return C
        L = self.info.length
        if L is not None and t >= L - 2:
            return D
        if t % 15 == 0:
            n = len(opp)
            c = opp.count(C)
            chi = ((c - n / 2) ** 2 + ((n - c) - n / 2) ** 2) / (n / 2)
            self.random_opp = chi < 3.841   # cannot reject 50-50 at 5%
        return D if self.random_opp else tft(opp)


@register
class Friedman(Strategy):
    name = "Friedman (Grudger)"
    author = "James W. Friedman"
    origin = FIRST
    place = "7th of 15"
    blurb = ("Cooperates until the other player defects even once, then defects for "
             "the rest of the game.  Also known as Grim Trigger.")

    def move(self, me, opp):
        return D if D in opp else C


@register
class Davis(Strategy):
    name = "Davis"
    author = "Morton Davis"
    origin = FIRST
    place = "8th of 15"
    blurb = "Cooperates for the first 10 moves, then plays like Friedman's Grudger."

    def move(self, me, opp):
        if len(me) < 10:
            return C
        return D if D in opp else C


@register
class Graaskamp(Strategy):
    name = "Graaskamp"
    author = "Jim Graaskamp"
    origin = FIRST
    place = "9th of 15"
    stochastic = True
    blurb = ("Tit for Tat for 50 moves, defects on move 51, then Tit for Tat for five "
             "more.  It then checks whether the other is random (defect for good), "
             "Tit for Tat or its own twin (keep playing Tit for Tat); otherwise it "
             "plays Tit for Tat but slips in a defection every 5-15 moves.")

    def init(self):
        self.mode = None
        self.next_d = None

    def move(self, me, opp):
        t = len(me)
        if t < 50:
            return tft(opp)
        if t == 50:
            return D
        if t < 56:
            return tft(opp)
        if self.mode is None:
            n = len(opp)
            c = opp.count(C)
            chi = ((c - n / 2) ** 2 + ((n - c) - n / 2) ** 2) / (n / 2)
            if chi < 3.841:
                self.mode = "random"
            elif opp[1:] == me[:-1] or opp == me:
                self.mode = "tft"
            else:
                self.mode = "probe"
                self.next_d = t + self.rng.randint(5, 15)
        if self.mode == "random":
            return D
        if self.mode == "probe" and t >= self.next_d:
            self.next_d = t + self.rng.randint(5, 15)
            return D
        return tft(opp)


@register
class Downing(Strategy):
    name = "Downing"
    author = "Leslie Downing"
    origin = FIRST
    place = "10th of 15"
    blurb = ("Models the other player as responsive: it estimates the chance the "
             "other cooperates after Downing cooperates and after Downing defects, "
             "and picks whichever move pays best in the long run.  It starts by "
             "assuming both chances are 1/2, which makes it defect at first - the "
             "flaw Axelrod singled out (see Revised Downing).")
    optimistic = False

    def init(self):
        self.cc = self.c_tot = 0   # their C after my C / my C
        self.dc = self.d_tot = 0   # their C after my D / my D

    def move(self, me, opp):
        t = len(me)
        if t >= 2:
            if me[-2] == C:
                self.c_tot += 1
                self.cc += opp[-1] == C
            else:
                self.d_tot += 1
                self.dc += opp[-1] == C
        if self.optimistic:
            a = (self.cc + 1) / (self.c_tot + 1)
            b = self.dc / (self.d_tot + 1) if self.d_tot else 0.0
        else:
            a = self.cc / self.c_tot if self.c_tot else 0.5
            b = self.dc / self.d_tot if self.d_tot else 0.5
        if t < 2 and not self.optimistic:
            return D
        pay = self.info.payoffs
        ev_c = a * pay.R + (1 - a) * pay.S
        ev_d = b * pay.T + (1 - b) * pay.P
        if ev_c > ev_d:
            return C
        if ev_c < ev_d:
            return D
        if not me:
            return C
        return D if me[-1] == C else C


@register
class Feld(Strategy):
    name = "Feld"
    author = "Scott Feld"
    origin = FIRST
    place = "11th of 15"
    stochastic = True
    blurb = ("Always defects after the other defects.  After a cooperation it "
             "cooperates with a probability that slides from 1.0 down to 0.5 over "
             "the 200 moves.")

    def move(self, me, opp):
        if not opp:
            return C
        if opp[-1] == D:
            return D
        L = self.info.length or 200
        p = max(0.5, 1.0 - 0.5 * len(me) / L)
        return C if self.chance(p) else D


@register
class Joss(Strategy):
    name = "Joss"
    author = "Johann Joss"
    origin = FIRST
    place = "12th of 15"
    stochastic = True
    blurb = ("Tit for Tat, except that after the other cooperates it sneaks in a "
             "defection 10% of the time.  Against Tit for Tat this sets off long "
             "echoes of mutual punishment - one of Axelrod's key lessons.")

    def move(self, me, opp):
        if not opp:
            return C
        if opp[-1] == D:
            return D
        return C if self.chance(0.9) else D


@register
class Tullock(Strategy):
    name = "Tullock"
    author = "Gordon Tullock"
    origin = FIRST
    place = "13th of 15"
    stochastic = True
    blurb = ("Cooperates for the first 11 moves, then cooperates 10% less often "
             "than the other player did over the previous 10 moves.")

    def move(self, me, opp):
        if len(me) < 11:
            return C
        rate = opp[-10:].count(C) / 10
        return C if self.chance(max(0.0, rate - 0.1)) else D


@register
class NameWithheld(Strategy):
    name = "Name Withheld"
    author = "(anonymous)"
    origin = FIRST
    place = "14th of 15"
    stochastic = True
    blurb = ("The anonymous entry's program was never published in detail.  "
             "Reconstructed as in Axelrod-Python: cooperate with a probability "
             "drawn afresh between 0.3 and 0.7 each move.")

    def move(self, me, opp):
        return C if self.chance(self.rng.uniform(0.3, 0.7)) else D


@register
class RandomPlayer(Strategy):
    name = "Random"
    author = "(Axelrod's control entry)"
    origin = FIRST
    place = "15th of 15"
    stochastic = True
    blurb = "Cooperates or defects with equal probability.  Axelrod's control entry in both tournaments."

    def move(self, me, opp):
        return C if self.chance(0.5) else D


# ======================================================= second tournament

@register
class Champion(Strategy):
    name = "Champion"
    author = "Danny Champion"
    origin = SECOND
    place = "2nd of 63"
    stochastic = True
    blurb = ("Cooperates for 10 moves, plays Tit for Tat for the next 15, then "
             "cooperates unless the other defected last move, has cooperated less "
             "than 60% of the time, and a random number exceeds its cooperation rate.")

    def move(self, me, opp):
        t = len(me)
        if t < 10:
            return C
        if t < 25:
            return tft(opp)
        rate = opp.count(C) / t
        if opp[-1] == D and rate < 0.6 and self.rng.random() > rate:
            return D
        return C


@register
class Borufsen(Strategy):
    name = "Borufsen"
    author = "Otto Borufsen"
    origin = SECOND
    place = "3rd of 63"
    blurb = ("Tit for Tat with two peace-making rules: after three rounds of mutual "
             "defection it cooperates once, and if the two are stuck alternating "
             "it swaps its next defection for a cooperation.  Every 25 moves it "
             "checks whether the other looks random or hostile and, if so, defects "
             "until the next check.")

    def init(self):
        self.defect_mode = False
        self.cc = self.cd = 0
        self.coop_since = 0
        self.normal_since = 0
        self.flip_next_d = False

    def move(self, me, opp):
        t = len(me)
        if t >= 2:
            if me[-2] == C and opp[-1] == C:
                self.cc += 1
            if me[-2] == D and opp[-1] == C:
                self.cd += 1
        if t:
            self.coop_since += opp[-1] == C
        if t == 0:
            return C
        if t >= 26 and (t - 26) % 25 == 0:
            was = self.defect_mode
            coops = self.coop_since
            ratio = self.cc / (self.cc + self.cd) if (self.cc + self.cd) else 1.0
            self.defect_mode = (7 <= coops <= 18 and ratio < 0.7) or coops < 3
            self.coop_since = 0
            self.cc = self.cd = 0
            if self.defect_mode:
                return D
            if was:
                self.normal_since = t
                return D
        if self.defect_mode:
            return D
        if t - self.normal_since >= 3:
            if me[-3:] == [D, D, D] and opp[-3:] == [D, D, D]:
                return C
            if all(me[-k] != opp[-k] for k in (1, 2, 3)) and me[-1] != me[-2]:
                self.flip_next_d = True
        m = tft(opp)
        if m == D and self.flip_next_d:
            self.flip_next_d = False
            return C
        return m


@register
class GraaskampKatzen(Strategy):
    name = "Graaskamp and Katzen"
    author = "Jim Graaskamp and Ken Katzen"
    origin = SECOND
    place = "6th of 63"
    blurb = ("Tit for Tat, but it gives up and defects for the rest of the game if "
             "its score falls behind a schedule: under 23 points by move 11, 53 by "
             "move 21, 83 by 31, 113 by 41, 143 by 51 or 293 by 101.")
    CHECKS = {10: 23, 20: 53, 30: 83, 40: 113, 50: 143, 100: 293}

    def init(self):
        self.gave_up = False

    def move(self, me, opp):
        t = len(me)
        if t in self.CHECKS and self.scores(me, opp)[0] < self.CHECKS[t]:
            self.gave_up = True
        if self.gave_up:
            return D
        return tft(opp)


@register
class Eatherley(Strategy):
    name = "Eatherley"
    author = "Graham Eatherley"
    origin = SECOND
    stochastic = True
    blurb = ("Cooperates unless the other just defected; then it defects with a "
             "probability equal to the other's overall defection rate.")

    def move(self, me, opp):
        if not opp or opp[-1] == C:
            return C
        return D if self.chance(opp.count(D) / len(opp)) else C


@register
class Tranquilizer(Strategy):
    name = "Tranquilizer"
    author = "Craig Feathers"
    origin = SECOND
    stochastic = True
    blurb = ("Axelrod's example of an exploiter: it lulls the other into a habit of "
             "cooperation, then defects now and then, never more than a quarter of "
             "the time and only after a run of mutual cooperation.  Reconstructed "
             "from Axelrod's description; the original program is far longer.")

    def move(self, me, opp):
        t = len(me)
        if t < 10:
            return tft(opp)
        if opp[-1] == D:
            return D
        run = 0
        for a, b in zip(reversed(me), reversed(opp)):
            if a == C and b == C:
                run += 1
            else:
                break
        if run >= 6 and me.count(D) < t / 4 and self.chance(0.25):
            return D
        return C


@register
class Tester(Strategy):
    name = "Tester"
    author = "David Gladstein"
    origin = SECOND
    place = "46th of 63"
    blurb = ("Defects on the first move to test the other.  If the other ever "
             "defects, it apologises by cooperating and plays Tit for Tat from "
             "then on; otherwise it cooperates on moves 2 and 3 and defects on "
             "every other move after that.")

    def init(self):
        self.caught = None

    def move(self, me, opp):
        t = len(me)
        if t == 0:
            return D
        if self.caught is None and D in opp:
            self.caught = t
            return C
        if self.caught is not None:
            return tft(opp)
        if t < 3:
            return C
        return D if t % 2 == 1 else C


@register
class TitForTwoTats(Strategy):
    name = "Tit For Two Tats"
    author = "John Maynard Smith"
    origin = SECOND
    place = "24th of 63"
    blurb = ("Defects only after the other defects twice in a row.  It would have "
             "won the first tournament, but in the second the entrants had learnt "
             "to exploit such forgiveness.")

    def move(self, me, opp):
        return D if opp[-2:] == [D, D] else C


@register
class RevisedDowning(Downing):
    name = "Revised Downing"
    author = "Leslie Downing / Stanley F. Quayle"
    origin = SECOND
    optimistic = True
    blurb = ("Downing's model-the-other rule, but starting from the assumption that "
             "the other is responsive, so it cooperates at first.  Axelrod showed "
             "this version would have won the first tournament; it was entered in "
             "the second.")


# ===================================================== later and noise work

@register
class GenerousTFT(Strategy):
    name = "Generous Tit For Tat"
    author = "Molander (1985); Nowak and Sigmund (1992)"
    origin = LATER
    stochastic = True
    blurb = ("Tit for Tat that forgives a defection with probability "
             "min(1 - (T-R)/(R-S), (R-P)/(T-P)) = 1/3 with the usual payoffs.  "
             "Wu and Axelrod (1995) showed generosity copes well with noise.")

    def move(self, me, opp):
        if not opp or opp[-1] == C:
            return C
        p = self.info.payoffs
        try:
            g = min(1 - (p.T - p.R) / (p.R - p.S), (p.R - p.P) / (p.T - p.P))
        except ZeroDivisionError:   # payoffs with ties: fall back to the usual 1/3
            g = 1 / 3
        return C if self.chance(min(1.0, max(0.0, g))) else D


@register
class ContriteTFT(Strategy):
    name = "Contrite Tit For Tat"
    author = "Sugden (1986); Boyd (1989); Wu and Axelrod (1995)"
    origin = LATER
    blurb = ("Tracks 'standing': a player who defects without provocation loses "
             "good standing.  It defects only when it is in good standing and the "
             "other is not, so it accepts punishment for its own (accidental) "
             "defections instead of starting an echo.  One of Wu and Axelrod's "
             "best answers to noise.")

    def init(self):
        self.good_me = True
        self.good_opp = True

    def move(self, me, opp):
        if me:
            a, b = me[-1], opp[-1]
            gm, go = self.good_me, self.good_opp
            self.good_me = a == C or (gm and not go)
            self.good_opp = b == C or (go and not gm)
        return D if (self.good_me and not self.good_opp) else C


@register
class Pavlov(Strategy):
    name = "Pavlov (Win-Stay Lose-Shift)"
    author = "Kraines and Kraines (1989); Nowak and Sigmund (1993)"
    origin = LATER
    blurb = ("Repeats its last move after a good payoff (R or T) and switches after "
             "a bad one (P or S) - i.e. cooperates when both players made the same "
             "move.  Corrects its own mistakes under noise and exploits unconditional "
             "cooperators.")

    def move(self, me, opp):
        if not me:
            return C
        return C if me[-1] == opp[-1] else D


@register
class Gradual(Strategy):
    name = "Gradual"
    author = "Beaufils, Delahaye and Mathieu (1996)"
    origin = LATER
    blurb = ("Answers the other's n-th defection with n defections, then two "
             "cooperations to calm things down.  Beat Tit for Tat in its authors' "
             "re-runs of Axelrod-style tournaments.")

    def init(self):
        self.queue: list[str] = []
        self.count = 0

    def move(self, me, opp):
        if self.queue:
            return self.queue.pop(0)
        if opp and opp[-1] == D:
            self.count += 1
            self.queue = [D] * (self.count - 1) + [C, C]
            return D
        return C


class _ZD(Strategy):
    probs = (1, 0, 1, 0)   # P(C) after CC, CD, DC, DD (my move first)
    stochastic = True

    def move(self, me, opp):
        if not me:
            return C
        k = {(C, C): 0, (C, D): 1, (D, C): 2, (D, D): 3}[(me[-1], opp[-1])]
        return C if self.chance(self.probs[k]) else D


@register
class Extort2(_ZD):
    name = "Extort-2"
    author = "Press and Dyson (2012)"
    origin = LATER
    probs = (8 / 9, 1 / 2, 1 / 3, 0)
    blurb = ("A zero-determinant strategy: memory-one probabilities (8/9, 1/2, 1/3, 0) "
             "that force its surplus over P to be twice the other's.  It never loses "
             "a match on points, yet does poorly in tournaments - the Axelrod lesson "
             "that beating your partner is not the point.")


@register
class ZDGTFT2(_ZD):
    name = "ZD Generous TFT-2"
    author = "Stewart and Plotkin (2012)"
    origin = LATER
    probs = (1, 1 / 8, 1, 1 / 4)
    blurb = ("The generous zero-determinant strategy (1, 1/8, 1, 1/4) with which "
             "Stewart and Plotkin topped their re-run of Axelrod's tournament.")


SOUTHAMPTON_CODE = [C, D, D, C, D, C, C, D, C]


class _Southampton(Strategy):
    role = C   # move 10 announces the role: C = master, D = servant

    def init(self):
        self.partner = None

    def move(self, me, opp):
        t = len(me)
        if t < len(SOUTHAMPTON_CODE):
            return SOUTHAMPTON_CODE[t]
        if t == len(SOUTHAMPTON_CODE):
            if opp[:t] != SOUTHAMPTON_CODE:
                self.partner = False
            return self.role
        if self.partner is None:
            if opp[:len(SOUTHAMPTON_CODE)] == SOUTHAMPTON_CODE:
                self.partner = opp[len(SOUTHAMPTON_CODE)]
            else:
                self.partner = False
        if self.partner is False:
            return self.outsider(me, opp)
        if self.role == C and self.partner == D:
            return D            # master milks its servant
        if self.role == D and self.partner == C:
            return C            # servant feeds its master
        return C                # teammates of the same rank cooperate


@register
class SouthamptonMaster(_Southampton):
    name = "Southampton Master"
    author = "Southampton team, 20th-anniversary competition (2004)"
    origin = LATER
    role = C
    blurb = ("Collusion, as in the 2004 anniversary competition: opens with a "
             "nine-move code and announces its rank on move 10.  A servant that "
             "answers the code cooperates while the master defects, feeding it "
             "points; outsiders get Tit for Tat.  Give the servants several copies "
             "to see the effect.  (Code and details simplified.)")

    def outsider(self, me, opp):
        return tft(opp)


@register
class SouthamptonServant(_Southampton):
    name = "Southampton Servant"
    author = "Southampton team, 20th-anniversary competition (2004)"
    origin = LATER
    role = D
    blurb = ("The master's helper: after the code it cooperates with a master and "
             "defects against every outsider, to drag rivals' scores down.")

    def outsider(self, me, opp):
        return D


# ================================================================ baselines

@register
class AllC(Strategy):
    name = "Always Cooperate"
    blurb = "Cooperates no matter what."

    def move(self, me, opp):
        return C


@register
class AllD(Strategy):
    name = "Always Defect"
    blurb = "Defects no matter what - the only equilibrium of a game of known, fixed length."

    def move(self, me, opp):
        return D


@register
class Alternator(Strategy):
    name = "Alternator"
    blurb = "Cooperates, then defects, then cooperates, and so on."

    def move(self, me, opp):
        return C if len(me) % 2 == 0 else D


@register
class SuspiciousTFT(Strategy):
    name = "Suspicious Tit For Tat"
    blurb = "Tit for Tat that opens with a defection."

    def move(self, me, opp):
        return opp[-1] if opp else D


# ===================================================== new strategies (mine)

@register
class Envoy(Strategy):
    name = "Envoy"
    author = "Claude (2026)"
    origin = MINE
    blurb = (
        "A modelling diplomat, in the spirit of Downing but done properly.  It "
        "learns how the other answers each of the four possible rounds (both "
        "cooperated, I was cheated, I cheated, both defected), starting from the "
        "belief that it faces a Tit for Tat, and each move solves the four-state "
        "planning problem for the move worth most over the rest of the game.  "
        "Reciprocators get steady cooperation and instant forgiveness; random "
        "or unconditional defectors get defection; it never defects first just "
        "to probe.  When the length is announced it defects on the final move, "
        "like Stein and Rapoport.")
    PRIOR = {C: 0.9, D: 0.1}   # Tit for Tat-like belief: they answer my move
    W = 2.0                    # weight of each prior, in pseudo-observations
    GAMMA = 0.96

    def init(self):
        self.cnt = {(a, b): [0, 0] for a in (C, D) for b in (C, D)}  # [their C, n]
        self.policy = None

    def estimates(self):
        """q[s] = P(they cooperate next | last round s), each state shrunk
        toward the pooled rate after the same move of mine, which in turn is
        shrunk toward the Tit for Tat prior."""
        q = {}
        for a in (C, D):
            c = sum(self.cnt[(a, b)][0] for b in (C, D))
            n = sum(self.cnt[(a, b)][1] for b in (C, D))
            pooled = (c + self.W * self.PRIOR[a]) / (n + self.W)
            for b in (C, D):
                cs, ns = self.cnt[(a, b)]
                q[(a, b)] = (cs + self.W * pooled) / (ns + self.W)
        return q

    def move(self, me, opp):
        t = len(me)
        if t >= 2:
            s = (me[-2], opp[-2])
            self.cnt[s][1] += 1
            self.cnt[s][0] += opp[-1] == C
        if t == 0:
            return C
        L = self.info.length
        if L is not None and t == L - 1:
            return D
        last = (me[-1], opp[-1])
        if last == (C, C):
            return C                       # never break a cooperation
        q = self.estimates()
        self.policy = plan(q, self.info.payoffs, self.GAMMA, self.policy)
        return self.policy[last]


STATES = [(C, C), (C, D), (D, C), (D, D)]


def plan(q, pay, g, policy=None):
    """Optimal policy for the four-state model q[s] = P(they cooperate next
    | last round s), by policy iteration (exact evaluation of each policy)."""
    u = {(a, b): pay.pair(a, b)[0] for a in (C, D) for b in (C, D)}
    pol = dict(policy) if policy else {s: C for s in STATES}
    for _ in range(8):
        # Evaluate: V = r + g P V  ->  (I - gP) V = r, 4x4 Gaussian elimination.
        A = [[0.0] * 5 for _ in range(4)]
        for i, s in enumerate(STATES):
            a = pol[s]
            A[i][i] += 1.0
            for o, pr in ((C, q[s]), (D, 1 - q[s])):
                A[i][STATES.index((a, o))] -= g * pr
                A[i][4] += pr * u[(a, o)]
        for c in range(4):
            piv = max(range(c, 4), key=lambda r: abs(A[r][c]))
            A[c], A[piv] = A[piv], A[c]
            for r in range(4):
                if r != c and A[r][c]:
                    f = A[r][c] / A[c][c]
                    A[r] = [x - f * y for x, y in zip(A[r], A[c])]
        V = {s: A[i][4] / A[i][i] for i, s in enumerate(STATES)}
        new = {}
        for s in STATES:
            val = {a: sum(pr * (u[(a, o)] + g * V[(a, o)])
                          for o, pr in ((C, q[s]), (D, 1 - q[s]))) for a in (C, D)}
            new[s] = pol[s] if val[pol[s]] >= val[FLIPM[pol[s]]] - 1e-12 else FLIPM[pol[s]]
        if new == pol:
            break
        pol = new
    return pol


FLIPM = {C: D, D: C}


@register
class Peacekeeper(Strategy):
    name = "Peacekeeper"
    author = "Claude (2026)"
    origin = MINE
    stochastic = True
    blurb = (
        "A reciprocator that keeps the peace.  It cooperates whenever the other "
        "just cooperated.  After a defection it hits back only with a probability "
        "equal to the other's defection rate over the last 20 moves, so rare "
        "lapses are forgiven and habitual ones are not.  It is contrite: when the "
        "other is only punishing its own earlier unprovoked defection (say, a "
        "noise error), it takes the punishment instead of starting an echo.  "
        "Every 10 moves from move 20 it checks whether the other cooperates under "
        "a third of the time, or cooperates no more after its cooperation than "
        "after its defection (a random or unconditional player); then it defects "
        "until the other shows three cooperations in a row.  Never defects first.")
    WINDOW = 20

    def init(self):
        self.hostile = False

    def move(self, me, opp):
        t = len(me)
        if t == 0:
            return C
        if t >= 20 and t % 10 == 0:
            rate = opp.count(C) / t
            r = responsiveness(me, opp)
            unresponsive = r is not None and r < 0.25 and 0.2 < rate < 0.85
            self.hostile = rate < 0.33 or unresponsive
        if self.hostile:
            if opp[-3:] == [C, C, C]:
                self.hostile = False
                return C
            return D
        if opp[-1] == C:
            return C
        if t >= 2 and me[-2] == D and opp[-2] == C:
            return C                    # they punish my defection: accept it
        recent = opp[-self.WINDOW:]
        return D if self.chance(recent.count(D) / len(recent)) else C


def responsiveness(me, opp, least=5):
    """P(they C after my C) - P(they C after my D), or None with too little data."""
    cc = cn = dc = dn = 0
    for k in range(len(me) - 1):
        if me[k] == C:
            cn += 1
            cc += opp[k + 1] == C
        else:
            dn += 1
            dc += opp[k + 1] == C
    if cn < least or dn < least:
        return None
    return cc / cn - dc / dn


class LookupStrategy(Strategy):
    """Plays from a 64-letter table indexed by the last three rounds, padded
    at the start by a 6-letter 'premise' (Axelrod 1987)."""
    table = "C" * 64
    premise = "CCCCCC"

    def move(self, me, opp):
        return self.table[gene_index(me, opp, self.premise)]


@register
class EvolvedReciprocator(LookupStrategy):
    name = "Evolved Reciprocator"
    author = "Claude (2026), bred with this app's genetic algorithm"
    origin = MINE
    table = "CCDDCCDDDCCCDCDDCDCCCDCDCCCCCDDDDCDDCDDDDDDDDCDCDCDDCCCDCDCDDCDC"
    premise = "CCCDCC"
    blurb = (
        "Not designed by hand: bred the way Axelrod did in 1987.  Its whole rule "
        "is a 64-entry table saying what to do after each possible pattern of the "
        "last three rounds; the best of four runs of 60 generations of 24 tables, "
        "scored over 151 moves against every first- and second-tournament entry, "
        "was kept.  What the table works out to: it never defects first; it lets "
        "one or two defections in a row pass (Joss's lapses go unanswered) and "
        "turns an opening test like Tester's into lasting cooperation; but three "
        "defections in a row flip it into a cooperate-defect-defect cycle that "
        "it keeps up even after the other has gone back to cooperating, so a "
        "reformed opponent is exploited rather than forgiven.  Against a steady "
        "defector it keeps offering short runs of cooperation - a costly habit it "
        "never had to unlearn, because no unconditional defector was in the field "
        "it was bred against.")


def by_name(name: str):
    key = name.strip().lower()
    for cls in REGISTRY:
        if cls.name.lower() == key:
            return cls
    hits = [c for c in REGISTRY if key in c.name.lower()]
    return hits[0] if len(hits) == 1 else None


def bred_class(table: str, premise: str, name: str, note: str = ""):
    """A strategy class for a table bred in the Evolve tab."""
    blurb = ("Bred in this app's Evolve tab: a 64-entry table giving the move for "
             "each pattern of the last three rounds (Axelrod's 1987 method). "
             + (note + " " if note else "") + f"Table {table}, premise {premise}.")
    return type("Bred_" + "".join(ch for ch in name if ch.isalnum()), (LookupStrategy,), dict(
        name=name, author="You, with the genetic algorithm", origin=BRED, note=note,
        table=table, premise=premise, blurb=blurb,
        gist="A table you bred; see 'Character (measured)' for how it behaves."))


GISTS = {
    "Tit For Tat": "Start nice, then copy whatever the other did last.",
    "Tideman and Chieruzzi": "Copy the other, punishing each new bout of defection a little longer, but wipe the slate clean when far ahead.",
    "Nydegger": "A fixed table of responses to the last three rounds; mostly cooperative, defects on specific patterns.",
    "Grofman": "Cooperate when the two of you agreed last move; when you disagreed, cooperate only 2 times in 7.",
    "Shubik": "Copy the other, but each new punishment lasts one move longer than the last.",
    "Stein and Rapoport": "Copy the other, defect against random-looking players, and cheat on the last two moves.",
    "Friedman (Grudger)": "Cooperate until betrayed once, then never again.",
    "Davis": "Cooperate for 10 moves no matter what, then hold a permanent grudge after any betrayal.",
    "Graaskamp": "Copy the other, but test it with a defection at move 51 and keep testing anyone who isn't a simple copier.",
    "Downing": "Learn how the other responds and play whatever pays best - but it starts out suspicious.",
    "Feld": "Copy defections; cooperate less and less often over the game.",
    "Joss": "Copy the other, but sneak in a defection 10% of the time.",
    "Tullock": "Cooperate a bit less than the other has lately.",
    "Name Withheld": "Mostly random (cooperates 30-70% of the time).",
    "Random": "A coin toss each move.",
    "Champion": "Cooperative start, then copying, then mostly cooperative unless the other is clearly uncooperative.",
    "Borufsen": "Copy the other but break up feuds, and defect against random or hostile players.",
    "Graaskamp and Katzen": "Copy the other, but give up and defect for good if its score falls behind schedule.",
    "Eatherley": "Forgive a defection unless the other defects often - punish in proportion to its record.",
    "Tranquilizer": "Lull the other into cooperating, then cheat now and then.",
    "Tester": "Defect first to test; if punished, apologise and copy; if not, exploit every other move.",
    "Tit For Two Tats": "Only punish two defections in a row.",
    "Revised Downing": "Learn how the other responds and play whatever pays best, assuming good faith at first.",
    "Generous Tit For Tat": "Copy the other, but forgive a third of defections.",
    "Contrite Tit For Tat": "Copy the other, but accept punishment for your own mistakes instead of punishing back.",
    "Pavlov (Win-Stay Lose-Shift)": "Keep your move if it paid well, change it if it paid badly.",
    "Gradual": "Punish the n-th defection with n defections, then make peace with two cooperations.",
    "Extort-2": "A probabilistic rule that guarantees beating the other on points, at the cost of total score.",
    "ZD Generous TFT-2": "A probabilistic rule that is generous: lets the other do slightly better, keeps cooperation going.",
    "Southampton Master": "Collusion: recognise teammates by a secret opening code and let servants feed it points.",
    "Southampton Servant": "Collusion: feed the master, defect against everyone else.",
    "Always Cooperate": "Always cooperate.",
    "Always Defect": "Always defect.",
    "Alternator": "Cooperate, defect, cooperate, defect...",
    "Suspicious Tit For Tat": "Copy the other, but start with a defection.",
    "Envoy": "Learn how the other responds and plan ahead for the best long-run payoff; never breaks a run of mutual cooperation.",
    "Peacekeeper": "Copy cooperation, forgive defection in proportion to how rare it is, accept punishment for its own slips, and defect against random or hostile players.",
    "Evolved Reciprocator": "A bred lookup table: never defects first and overlooks one or two lapses, but three in a row turn it into a lasting exploiter.",
}
for _cls in REGISTRY:
    _cls.gist = GISTS.get(_cls.name, "")


def strategy_info(cls) -> str:
    """Plain-text explanation of a strategy."""
    lines = [cls.name]
    if cls.author:
        lines.append(f"By: {cls.author}")
    lines.append(f"From: {cls.origin}" + (f" - placed {cls.place}" if cls.place else ""))
    lines.append("Random element: yes" if cls.stochastic else "Random element: no (deterministic)")
    lines.append("")
    if getattr(cls, "gist", ""):
        lines += ["In short: " + cls.gist, ""]
    lines.append("The rules: " + (cls.blurb or "(no description)"))
    return "\n".join(lines)

