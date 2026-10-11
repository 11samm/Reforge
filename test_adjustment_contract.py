"""No-model regression for dimensions rejected during the first rehearsal."""
import copy
import unittest
from unittest.mock import Mock
from features.learning import AdjustmentHarness, PLAN


class PlannerDomain(unittest.TestCase):
    def test_schema_and_host_use_the_same_existing_generator_bounds(self):
        harness=object.__new__(AdjustmentHarness)
        harness.domain={'min':-100,'max':100,'step':1,'default':0}
        harness.budget=Mock()
        plan={'question':'Synthetic domain check','hypotheses':['A','B'],
              'input':{'kind':'patches','width':17,'height':3},'value':0,
              'predictions':['A','B'],'usefulness':'No model or reference call'}
        for field in ('width','height'):
            schema=PLAN['properties']['input']['properties'][field]
            self.assertEqual(schema,{'type':'integer','minimum':3,'maximum':257})
            for bad in (1,2,258,3.5,True):
                value=copy.deepcopy(plan);value['input'][field]=bad
                with self.assertRaisesRegex(ValueError,'Expected integer in 3..257'):
                    harness.experiment(value)
            harness.budget.spend.assert_not_called()
            # Stop at the budget boundary, before generation/browser execution.
            for accepted in (3,257):
                value=copy.deepcopy(plan);value['input'][field]=accepted
                harness.budget.spend.side_effect=StopIteration('Synthetic stop before execution')
                with self.assertRaises(StopIteration):harness.experiment(value)
                harness.budget.spend.assert_called_once_with('experiment')
                harness.budget.spend.reset_mock()


if __name__=='__main__':unittest.main()
