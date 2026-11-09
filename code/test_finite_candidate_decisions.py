"""Arithmetic software fixtures only; not BIM, energy, cost or carbon observations."""
import random
import unittest
from finite_candidate_decisions import Evaluation as E,NoFeasibleDesign,select,enumerate_assignments,held_out_evaluate


class FiniteDecisionTests(unittest.TestCase):
    def test_three_objectives_diverge(self):
        # Artificial arithmetic chosen to distinguish objectives, not engineering data.
        rows={'A':{'s1':E(True,0),'s2':E(True,100)},'B':{'s1':E(True,40),'s2':E(True,60)},'C':{'s1':E(True,50),'s2':E(True,50)}}
        self.assertEqual(select(rows,['s1','s2'],'deterministic','s1')['selected'],'A')
        self.assertEqual(select(rows,['s1','s2'],'minimax')['selected'],'C')
        self.assertEqual(select(rows,['s1','s2'],'minimax_regret')['selected'],'B')
        self.assertFalse(select(rows,['s1','s2'],'minimax')['global_route_optimality_certified'])

    def test_infeasible_candidates_not_zero_or_dropped_scenarios(self):
        rows={'A':{'s1':E(True,-2),'s2':E(False,None)},'B':{'s1':E(True,2),'s2':E(True,3)}}
        self.assertEqual(select(rows,['s1','s2'],'deterministic','s1')['selected'],'A')
        self.assertEqual(select(rows,['s1','s2'],'minimax')['excluded'],['A'])
        with self.assertRaises(NoFeasibleDesign):
            select({'A':rows['A']},['s1','s2'],'minimax_regret')
        with self.assertRaises(ValueError):
            select({'A':{'s1':E(False,0)}},['s1'],'minimax')

    def test_missing_nonfinite_and_unknown_objective_rejected(self):
        for rows in ({'A':{'s1':E(True,float('nan'))}},{'A':{'s1':E(True,True)}},{'A':{}},{'A':{'s1':E(True,1),'extra':E(True,1)}}):
            with self.assertRaises(ValueError):
                select(rows,['s1'],'minimax')
        with self.assertRaises(ValueError):
            select({'A':{'s1':E(True,1)}},['s1'],'unknown')

    def test_ties_are_input_order_independent(self):
        rows={'Z':{'s':E(True,2)},'A':{'s':E(True,2)}}
        result=select(rows,['s'],'minimax')
        self.assertEqual(result['tied_designs'],['A','Z'])
        self.assertEqual(result['selected'],'A')

    def test_cartesian_budget_and_duplicates(self):
        rows=enumerate_assignments({'route':['r1','r2'],'size':[1,2,3]},6)
        self.assertEqual(len(rows),6)
        self.assertEqual(len({tuple(sorted(row.items())) for row in rows}),6)
        with self.assertRaises(ValueError):
            enumerate_assignments({'route':['r1','r2'],'size':[1,2,3]},5)
        with self.assertRaises(ValueError):
            enumerate_assignments({'size':[1,1]},10)

    def test_holdout_cannot_hide_failure_or_reselect(self):
        rows={'A':{'h1':E(True,2),'h2':E(False,None)},'B':{'h1':E(True,1),'h2':E(True,3)}}
        result=held_out_evaluate(rows,['h1','h2'],['s1'],'A')
        self.assertEqual(result['selected'],'A')
        self.assertEqual(result['failure_count'],1)
        self.assertEqual(result['feasibility_fraction'],.5)
        self.assertIsNone(result['maximum_regret_all_scenarios'])
        self.assertEqual(result['scenarios'][0]['regret'],1)
        with self.assertRaises(ValueError):
            held_out_evaluate(rows,['h1','h2'],['h1'],'A')

    def test_independent_nested_loop_recomputation(self):
        rng=random.Random(391)
        for _ in range(40):
            matrix=[[rng.randrange(-20,100) for s in range(4)] for d in range(5)]
            rows={str(d):{str(s):E(True,matrix[d][s]) for s in range(4)} for d in range(5)}
            best=[]
            for s in range(4):
                value=matrix[0][s]
                for d in range(1,5):
                    if matrix[d][s]<value:
                        value=matrix[d][s]
                best.append(value)
            for mode in ('minimax','minimax_regret'):
                scored=[]
                for d in range(5):
                    worst=float('-inf')
                    for s in range(4):
                        value=matrix[d][s]-(best[s] if mode=='minimax_regret' else 0)
                        if value>worst:
                            worst=value
                    scored.append((worst,str(d)))
                expected=sorted(scored)[0]
                actual=select(rows,[str(s) for s in range(4)],mode)
                self.assertEqual((actual['objective'],actual['selected']),expected)


if __name__=='__main__':
    unittest.main()
