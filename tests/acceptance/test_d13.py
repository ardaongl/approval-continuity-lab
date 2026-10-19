from approval_continuity_lab.scenarios import experiment, dispatch
from tests.support.base import Case, snapshot, B, C


class EducationalBaseline(Case):
    def test_unsafe_negative_control_really_changes_separate_store(self):
        observations=experiment('D13',self.path.parent)
        reference=snapshot(self.path.parent/'reference.sqlite');naive=snapshot(self.path.parent/'naive.sqlite')
        self.assertEqual(reference['services'][0]['artifact_digest'],C);self.assertEqual(reference['services'][0]['revision'],2)
        self.assertEqual(reference['proposals'][0]['status'],'superseded');self.assertEqual(reference['executions'],[])
        self.assertEqual(naive['services'][0]['artifact_digest'],B);self.assertEqual(naive['services'][0]['revision'],3)
        self.assertEqual(naive['proposals'][0]['status'],'approved');self.assertEqual(naive['executions'],[])
        self.assertEqual([x['effect_count'] for x in observations],[0,1])
        self.assertIn('UNSAFE_EDUCATIONAL',observations[1]['step'])
        self.assertEqual(dispatch('scenario-run','D13')['data']['scenarios'][0]['classification'],'COMPARISON')
