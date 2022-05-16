import redis

from eth.test_util.ut import OmocTestCase

from eth.db.backends.redisdb import AtomicRedis


##############################################################################################
##    if you run this unit test alone in intellij idea, and got following Error:
##  ...
##   File "....\src\eth\db\trie.py", line 5, in <module>
##   from trie import (
##     ImportError: cannot import name 'HexaryTrie'
##  ...
##  that's because Idea will add the parent folder eth/db to sys.path,
##      and there is already a 'trie' module in that folder,
#       which will hide the global 'trie' package
##  to fix it , open menu Run->Edit configuration,
##  select this unittest, in the right side of the window, change "Working Directory" to empty,
##      then save configuration and run this test again, it will work!!
##############################################################################################
class Test(OmocTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        redis_conn = redis.StrictRedis(host='localhost', port=6379, db=0)
        cls.aredis = AtomicRedis(redis_conn)


    def test_set_on_existing_value(self):
        aredis = self.aredis
        aredis.set(b'1', b'2')
        aredis.set(b'1', b'3')
        self.assertEqual(aredis.get(b'1'), b'3')


    def test_atomic(self):
        aredis = self.aredis
        aredis.set(b'1', b'2')
        self.assertEqual(aredis.get(b'1'), b'2')

        aredis.set(b'2', b'3')
        self.assertEqual(aredis.get(b'2'), b'3')

        ################################################################################
        ##  successfully execute a batch
        ################################################################################
        with aredis.atomic_batch() as batch:
            batch.set(b'1', b'A')
            batch.set(b'2', b'B')
            batch.set(b'3', b'C')

        self.assertEqual(aredis.get(b'1'), b'A')
        self.assertEqual(aredis.get(b'2'), b'B')
        self.assertEqual(aredis.get(b'3'), b'C')

        aredis.delete(b'2')

        ################################################################################
        ##  error in batch
        ################################################################################
        try:
            with aredis.atomic_batch() as batch:
                batch.set(b'1', b'X')
                batch.set(b'2', b'Y')
                batch.set(b'3', b'Z')
                raise ValueError("all batch operation should fail")
        except:
            pass


        self.assertEqual(aredis.get(b'1'), b'A')
        # key b'2' was delete before batch, should take effect.
        self.assertEqual(aredis.get(b'2'), None)
        self.assertEqual(aredis.get(b'3'), b'C')

