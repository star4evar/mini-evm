

from unittest import TestCase

class Test(TestCase):

    def test_1(self):
        import sys

        for p in sys.path:
            print(p)
