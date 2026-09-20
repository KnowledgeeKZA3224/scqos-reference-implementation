import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from sc_core import compile_batch, HARD_OUTLOOK_CEILING

class TestSCMailCore(unittest.TestCase):
    def clean(self, email):
        return {"email":email,"source":"existing_business_file","relationship":"existing_customer","purpose":"business outreach"}

    def test_clean_batch_permits(self):
        c=[self.clean("a@example.com"),self.clean("b@example.com")]
        r=compile_batch(c,{"id":"c1","subject":"Tax reminder","authorized":True},2)
        self.assertEqual(r["decision"],"PERMIT")
        self.assertEqual(len(r["selected"]),2)

    def test_duplicate_does_not_count_twice(self):
        c=[self.clean("a@example.com"),self.clean("a@example.com"),self.clean("b@example.com")]
        r=compile_batch(c,{"id":"c1","subject":"Tax reminder","authorized":True},2)
        self.assertEqual(r["decision"],"PERMIT")
        self.assertEqual(len(r["selected"]),2)

    def test_suppressed_contact_is_held(self):
        x=self.clean("a@example.com"); x["unsubscribed"]=True
        r=compile_batch([x],{"id":"c1","subject":"Tax reminder","authorized":True},1)
        self.assertEqual(r["decision"],"HOLD")

    def test_unknown_source_is_held(self):
        x=self.clean("a@example.com"); x["source"]="unknown"
        r=compile_batch([x],{"id":"c1","subject":"Tax reminder","authorized":True},1)
        self.assertEqual(r["decision"],"HOLD")

    def test_hard_ceiling_is_absolute(self):
        self.assertEqual(HARD_OUTLOOK_CEILING,9950)

if __name__ == "__main__":
    unittest.main()
