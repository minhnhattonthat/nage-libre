import os, tempfile, unittest
import trace_diff

def write(rows):
    fd, p = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("pc,n,lo,hi\n" + "".join(rows))
    return p

class Diff(unittest.TestCase):
    def test_new_and_grown_pcs(self):
        base = trace_diff.load(write(["808000,100,000000,000010\n", "81A000,10,010000,010004\n"]))
        act = trace_diff.load(write(["808000,110,000000,000010\n", "81A000,50,010000,010040\n",
                                     "82B000,7,0A0000,0A0006\n"]))
        self.assertEqual(trace_diff.diff(base, act),
                         [(0x81A000, 50, 10, 0x010000, 0x010040), (0x82B000, 7, 0, 0x0A0000, 0x0A0006)])
