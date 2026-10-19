from approval_continuity_lab.scenarios import experiment, dispatch
from tests.support.base import Case, snapshot, B


class OutsideBoundary(Case):
    def test_file_changes_outside_reference_transaction(self):
        observations=experiment('D14',self.path.parent)
        self.assertEqual((self.path.parent/'outside-effect.json').read_bytes(),b'{"artifact_digest":"sha256:'+b'c'*64+b'"}\n')
        state=snapshot(self.path.parent/'outside.sqlite')
        self.assertEqual(state['services'][0]['artifact_digest'],B);self.assertEqual(state['services'][0]['revision'],2)
        self.assertEqual(state['proposals'][0]['status'],'consumed');self.assertEqual(len(state['executions']),1)
        self.assertNotIn('outside-effect',state['executions'][0]['result_json'])
        self.assertEqual(observations[1]['step'],'outside-file');self.assertIsNone(observations[1]['effect_count']);self.assertIsNone(observations[1]['service_revision'])
        summary=dispatch('scenario-run','D14')['data']['scenarios'][0]
        self.assertEqual(summary['classification'],'OUTSIDE_GUARANTEE')
