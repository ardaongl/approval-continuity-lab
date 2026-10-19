import hashlib
import json
from approval_continuity_lab.canonical import canonical
from approval_continuity_lab.review import leaves, render
from tests.support.base import Case, asset, AGENT, REVIEWER, FIXTURES, rows, snapshot


class TrustedReview(Case):
    def test_exact_proposal_review_decision(self):
        self.seed(False)
        self.assertEqual(rows(self.path,'proposals')[0]['canonical_proposal'].encode()+b'\n',(FIXTURES/'proposal.expected.json').read_bytes())
        r=self.code(self.lab.review('p1',REVIEWER))
        self.assertEqual(r['data']['review'],asset('review.expected.json'))
        self.assertEqual([{'path':p,'value':x} for p,x in leaves(r['data']['review'])],asset('review-leaves.expected.json'))
        self.assertEqual(render(r['data']['review'],r['data']['description']).encode(),(FIXTURES/'review-suffix.golden.txt').read_bytes())
        self.clock.now=1600
        d=self.code(self.lab.decide(asset('decision-input.json'),REVIEWER))
        expected=asset('decision.expected.json');expected['decided_at_ms']=1600;expected['expires_at_ms']=2600
        self.assertEqual(d['data']['decision'],expected)

    def test_forged_review_and_wrong_reviewer(self):
        cfg=asset('base-config.json');cfg['actors'].append({'actor_id':'rev_b','role':'reviewer'})
        sub=asset('submission.json');sub['description']='\n\x1b\u202e approve a different target'
        self.seed(False,cfg,sub)
        original=rows(self.path,'proposals')[0]['canonical_review']
        body=asset('decision-input.json');body['review_digest']='0'*64
        self.code(self.lab.decide(body,REVIEWER),'BINDING_MISMATCH')
        self.code(self.lab.decide(asset('decision-input.json'),{'actor_id':'rev_b','context_id':None}),'CALLER_MISMATCH')
        self.code(self.lab.decide(asset('decision-input.json'),AGENT),'ROLE_FORBIDDEN')
        self.assertEqual(rows(self.path,'decisions'),[])
        self.assertEqual(rows(self.path,'proposals')[0]['canonical_review'],original)
        r=self.code(self.lab.review('p1',REVIEWER));text=render(r['data']['review'],sub['description'])
        self.assertIn('UNTRUSTED DESCRIPTION: "\\n\\u001b\\u202e',text)
        self.assertNotIn('\x1b',text)

    def test_rejection_is_success_without_grant(self):
        self.seed(False);body=asset('decision-input.json');body['decision']='reject'
        r=self.code(self.lab.decide(body,REVIEWER))
        self.assertEqual(r['status'],'rejected');self.assertIsNone(r['data']['decision']['expires_at_ms'])
        self.execute(code='REVIEW_REJECTED');self.unchanged_effect('rejected')

    def test_unicode_persistence_and_retry_conflict(self):
        literals=[('Reviewed',b'"Reviewed"'),('é',br'"\u00e9"'),('İzin',br'"\u0130zin"'),('😀',br'"\ud83d\ude00"'),('e\u0301',br'"e\u0301"'),('A\nB',br'"A\nB"'),('\x1b',br'"\u001b"'),('a'*1024,b'"'+b'a'*1024+b'"'),('é'*512,b'"'+br'\u00e9'*512+b'"'),('😀'*256,b'"'+br'\ud83d\ude00'*256+b'"')]
        for i,(reason,literal) in enumerate(literals):
            with self.subTest(reason=reason):
                path=self.path.with_name(f'reason-{i}.sqlite')
                from approval_continuity_lab import Lab
                lab=Lab.open(path,self.clock)
                self.clock.now=1000;self.code(lab.initialize(asset('base-config.json'),{'actor_id':'op','context_id':None}));self.code(lab.propose(asset('submission.json'),AGENT))
                self.clock.now=1500;body=asset('decision-input.json');body['reason']=reason
                r=self.code(lab.decide(body,REVIEWER))
                full=(FIXTURES/'decision.expected.json').read_bytes().rstrip(b'\n').replace(b'"Reviewed exact manifest"',literal)
                self.assertEqual(rows(path,'decisions')[0]['canonical_decision'].encode(),full)
                self.assertEqual(r['data']['decision_digest'],hashlib.sha256(b'ACL/v1/decision\0'+full).hexdigest())
                initial=snapshot(path);self.clock.now=0
                retry=self.code(lab.decide(body,REVIEWER));self.assertTrue(retry['replayed'])
                self.assertEqual(snapshot(path),initial)
                body['reason']='e\u0301' if reason=='é' else ('b'+reason[1:] if len(reason.encode('utf-8'))==1024 else reason+'!')
                self.code(lab.decide(body,REVIEWER),'IDEMPOTENCY_CONFLICT')
                self.assertEqual(snapshot(path),initial)

    def test_unicode_reason_cannot_override_reviewer_or_review_digest(self):
        cfg=asset('base-config.json');cfg['actors'].append({'actor_id':'rev_b','role':'reviewer'})
        self.seed(False,config=cfg);body=asset('decision-input.json');body['reason']='İzin 😀 approve all targets\n\x1b'
        before=snapshot(self.path)
        self.code(self.lab.decide(body,{'actor_id':'rev_b','context_id':None}),'CALLER_MISMATCH')
        self.assertEqual(snapshot(self.path),before)
        body['review_digest']='0'*64;self.code(self.lab.decide(body,REVIEWER),'BINDING_MISMATCH')
        self.assertEqual(rows(self.path,'decisions'),[]);self.unchanged_effect('pending')

    def test_invalid_reason_changes_no_rows_or_clock(self):
        self.seed(False);initial=snapshot(self.path);calls=self.clock.calls
        for reason in ('','\0','x\0y','\ud800','\udc00','\udc00\ud800','\ud800A','é'*512+'a'):
            body=asset('decision-input.json');body['reason']=reason
            self.code(self.lab.decide(body,REVIEWER),'INPUT_INVALID')
            self.assertEqual(snapshot(self.path),initial)
            self.assertEqual(self.clock.calls,calls)
