import hashlib
import json
from approval_continuity_lab.canonical import canonical, digest
from approval_continuity_lab.validation import decode, validate
from approval_continuity_lab.models import Failure, MAX_INT
from tests.support.base import Case, asset, AGENT, FIXTURES, snapshot


class Canonicalization(Case):
    def test_frozen_vectors_and_domains(self):
        for vector in asset("canonical-vectors.json"):
            self.assertEqual(canonical(decode(vector["input"].encode())), vector["canonical_ascii"])
        for domain, name in [("plan", "submission.json"), ("proposal", "proposal.expected.json"), ("review", "review.expected.json"), ("decision", "decision.expected.json")]:
            value = asset(name)
            if domain == "plan":
                value = value["plan"]
            expected = asset("digests.expected.json")[domain]
            self.assertEqual(digest(domain, value), expected)
            raw = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
            self.assertEqual(hashlib.sha256(b"ACL/v1/" + domain.encode() + b"\0" + raw).hexdigest(), expected)
        self.assertNotEqual(canonical("é"), canonical("e\u0301"))

    def test_strict_decoder_families(self):
        cases = [(b'{"a":1,"a":1}', "INPUT_INVALID"), (b'{"x":{"a":1,"a":2}}', "INPUT_INVALID"), (b'{} x', "INPUT_INVALID"), (b'\xef\xbb\xbf{}', "INPUT_INVALID"), (b'\xff', "INPUT_INVALID"), (b'"\xed\xa0\x80"', "INPUT_INVALID"), (b'"\\ud800"', "INPUT_INVALID"), (b'"\\udc00"', "INPUT_INVALID"), (b'"\\udc00\\ud800"', "INPUT_INVALID"), (b'1.0', "INPUT_INVALID"), (b'1e0', "INPUT_INVALID"), (b'NaN', "INPUT_INVALID"), (b'Infinity', "INPUT_INVALID"), (str(MAX_INT + 1).encode(), "INPUT_INVALID"), (b'['*17+b'0'+b']'*17, "INPUT_LIMIT"), (b' '*65537, "INPUT_LIMIT")]
        for raw, code in cases:
            with self.subTest(raw=raw[:40]), self.assertRaises(Failure) as e:
                decode(raw)
            self.assertEqual(e.exception.code, code)
        self.assertEqual(decode(b'-0'), 0)
        self.assertEqual(decode(b'['*16+b'0'+b']'*16), [[[[[[[[[[[[[[[[0]]]]]]]]]]]]]]]])
        self.assertEqual(decode(b'0'+b' '*65535), 0)
        self.assertEqual(decode(str(MAX_INT).encode()), MAX_INT)
        self.assertEqual(decode(b'"\\ud83d\\ude00"'), '😀')

    def test_schema_negatives_do_not_access_db(self):
        self.seed(False)
        initial = snapshot(self.path)
        for key, value in [('proposal_id', None), ('schema_version', True), ('schema_version', 2), ('grant_ttl_ms', 0), ('plan', {'revision': True, 'steps': []}), ('proposal_id', 'é')]:
            body = asset('submission.json');body[key] = value
            expected = 'UNSUPPORTED_VERSION' if key == 'schema_version' and value == 2 else 'INPUT_INVALID'
            self.code(self.lab.propose(body, AGENT), expected)
            self.assertEqual(snapshot(self.path), initial)
        for mode in ('extra', 'missing'):
            body=asset('submission.json')
            if mode == 'extra':body['extra']=1
            else:del body['request_id']
            self.code(self.lab.propose(body, AGENT), 'INPUT_INVALID')
            self.assertEqual(snapshot(self.path), initial)

    def test_reordered_submission_retry(self):
        self.seed(False)
        old = snapshot(self.path)
        self.clock.now = 0
        value = decode(json.dumps(asset('submission.json'), indent=3).encode())
        result = self.code(self.lab.propose(value, AGENT))
        self.assertTrue(result['replayed']);self.assertIsNone(result['observed_at_ms'])
        self.assertEqual(snapshot(self.path), old)

    def test_b1_reason_byte_boundaries(self):
        for reason, valid in [('',False),('a',True),('a'*1023,True),('a'*1024,True),('a'*1025,False),('é'*511+'a',True),('é'*512,True),('é'*512+'a',False),('😀'*256,True),('😀'*256+'a',False),('\0',False),('\ud800',False),('\udc00',False),('A\nB',True),('\x1b',True)]:
            with self.subTest(bytes=len(reason.encode('utf-8','surrogatepass'))):
                body=asset('decision-input.json');body['reason']=reason
                if valid:validate('decide',body)
                else:
                    with self.assertRaises(Failure):validate('decide',body)
