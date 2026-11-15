"""Checks that strategies follow their published rules.  python3 -m unittest test_strategies"""
import random
import unittest

from ipd import strategies as S
from ipd.engine import Settings, ecological, gene_index, play_match, run_tournament


def match(a, b, turns=200, **kw):
    st = Settings(turns=turns, **kw)
    return play_match(a(), b(), turns, st, random.Random(7))


class Rules(unittest.TestCase):
    def test_every_strategy_plays_and_is_explained(self):
        for cls in S.REGISTRY:
            self.assertTrue(cls.blurb and cls.gist, cls.name)
            for opp in (S.AllC, S.AllD, S.RandomPlayer, S.TitForTat):
                r = match(cls, opp, 60)
                self.assertEqual(len(r.a), 60)
                self.assertTrue(set(r.a) <= {"C", "D"})

    def test_names_unique(self):
        names = [c.name for c in S.REGISTRY]
        self.assertEqual(len(names), len(set(names)))

    def test_tft(self):
        r = match(S.TitForTat, S.Alternator, 10)
        self.assertEqual("".join(r.a), "CCDCDCDCDC")

    def test_grudger_and_davis(self):
        r = match(S.Friedman, S.Tester, 10)
        self.assertEqual(r.a[:2], ["C", "D"])
        self.assertTrue(all(m == "D" for m in r.a[1:]))
        r = match(S.Davis, S.AllD, 15)
        self.assertEqual("".join(r.a), "C" * 10 + "D" * 5)

    def test_stein_rapoport_endgame(self):
        r = match(S.SteinRapoport, S.AllC, 200)
        self.assertEqual(r.a[-2:], ["D", "D"])
        self.assertEqual(r.a.count("D"), 2)
        r = match(S.SteinRapoport, S.AllC, 200, tell_length=False)
        self.assertEqual(r.a.count("D"), 0)

    def test_shubik_escalates(self):
        class TwoLapses(S.Strategy):
            def move(self, me, opp):
                return "D" if len(me) in (3, 10) else "C"
        r = match(S.Shubik, TwoLapses, 20)
        self.assertEqual("".join(r.a[:16]), "CCCCDCCCCCCDDCCC")

    def test_tester(self):
        r = match(S.Tester, S.AllC, 8)
        self.assertEqual("".join(r.a), "DCCDCDCD")
        r = match(S.Tester, S.TitForTat, 6)
        self.assertEqual("".join(r.a), "DCCCCC")

    def test_tf2t(self):
        r = match(S.TitForTwoTats, S.Alternator, 10)
        self.assertNotIn("D", r.a)

    def test_graaskamp_katzen_gives_up(self):
        r = match(S.GraaskampKatzen, S.AllD, 15)
        self.assertTrue(all(m == "D" for m in r.a[10:]))

    def test_nydegger_table(self):
        r = match(S.Nydegger, S.AllC, 50)
        self.assertNotIn("D", r.a)

    def test_downing_starts_suspicious_revised_does_not(self):
        self.assertEqual(match(S.Downing, S.TitForTat, 3).a[:2], ["D", "D"])
        self.assertEqual(match(S.RevisedDowning, S.TitForTat, 3).a[0], "C")

    def test_pavlov(self):
        r = match(S.Pavlov, S.AllD, 6)
        self.assertEqual("".join(r.a), "CDCDCD")

    def test_gradual(self):
        class OneLapse(S.Strategy):
            def move(self, me, opp):
                return "D" if len(me) == 2 else "C"
        r = match(S.Gradual, OneLapse, 8)
        self.assertEqual("".join(r.a[:6]), "CCCDCC")

    def test_contrite_accepts_punishment(self):
        # Contrite TFT defects by mistake (noise stand-in): TFT punishes; CTFT must not echo.
        class Slip(S.ContriteTFT):
            def move(self, me, opp):
                return "D" if len(me) == 3 else super().move(me, opp)
        r = match(Slip, S.TitForTat, 10)
        self.assertEqual("".join(r.a), "CCCDCCCCCC")
        self.assertEqual("".join(r.b), "CCCCDCCCCC")

    def test_southampton_collusion(self):
        r = match(S.SouthamptonMaster, S.SouthamptonServant, 30)
        self.assertTrue(all(m == "D" for m in r.a[11:]))
        self.assertTrue(all(m == "C" for m in r.b[11:]))
        r = match(S.SouthamptonServant, S.TitForTat, 30)
        self.assertTrue(all(m == "D" for m in r.a[11:]))

    def test_new_strategies_are_nice(self):
        for cls in (S.Envoy, S.Peacekeeper, S.EvolvedReciprocator):
            for opp in (S.TitForTat, S.AllC, S.Friedman, S.Davis):
                r = match(cls, opp, 200, tell_length=False)
                self.assertNotIn("D", r.a, (cls.name, opp.name))

    def test_new_strategies_punish_defectors(self):
        for cls in (S.Envoy, S.Peacekeeper):
            self.assertGreater(match(cls, S.AllD, 200).score_a, 180, cls.name)

    def test_gene_index(self):
        self.assertEqual(gene_index([], [], "CCCCCC"), 0)
        self.assertEqual(gene_index([], [], "DDDDDD"), 63)
        self.assertEqual(gene_index(["C"], ["D"], "CCCCCC"), 1)


class Tournament(unittest.TestCase):
    def test_first_tournament_shape(self):
        field = [(c, 1) for c in S.REGISTRY if c.origin == S.FIRST]
        r = run_tournament(field, Settings(repetitions=3))
        top = {s.name for s in r.standings if s.rank <= 5}
        self.assertIn("Tit For Tat", top)
        bottom = {s.name for s in r.standings if s.rank > 10}
        self.assertIn("Random", bottom)

    def test_copies_and_ecology(self):
        r = run_tournament([(S.TitForTat, 1), (S.AllD, 2)], Settings(turns=50, repetitions=1))
        self.assertEqual(r.names, ["Tit For Tat", "Always Defect #1", "Always Defect #2"])
        hist = ecological(r.matrix, 50)
        self.assertAlmostEqual(sum(hist[-1]), 1.0)


if __name__ == "__main__":
    unittest.main()
