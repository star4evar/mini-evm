from typing import Iterator
from contextlib import contextmanager
import redis

from eth.db.diff import DELETED
from ..atomic import AtomicDB, AtomicDBWriteBatch


class AtomicRedis(AtomicDB):

    def __init__(self, db: redis.StrictRedis) -> None:
        if db is None:
            raise ValueError("db None")
        else:
            self.redis_inst = db

    def __getitem__(self, key: bytes) -> bytes:
        value = self.redis_inst.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: bytes, value: bytes) -> None:
        self.redis_inst.set(key, value)

    def __delitem__(self, key: bytes) -> None:
        self.redis_inst.delete(key)

    def _exists(self, key: bytes) -> bool:
        return self.redis_inst.exists(key)

    @contextmanager
    def atomic_batch(self) -> Iterator[AtomicDBWriteBatch]:
        """
        Commit all writes inside the context, unless an exception was raised.

        Although this is technically an external API, it (and this whole class) is only intended
        to be used by AtomicDB.
        """
        readable_write_batch: AtomicDBWriteBatch = AtomicRedisWriteBatch(self)
        try:
            yield readable_write_batch
            readable_write_batch._commit()
        finally:
            # force a shutdown of this batch, to prevent out-of-context usage
            readable_write_batch.batch_over()



class AtomicRedisWriteBatch(AtomicDBWriteBatch):

    def __init__(self, atomic_redis: AtomicRedis) -> None:
        super().__init__(atomic_redis)
        self.atomic_redis = atomic_redis


    def _commit(self) -> None:
        redis_inst: StrictRedis = self.atomic_redis.redis_inst

        p = redis_inst.pipeline()
        p.multi()

        for key, value in self._diff()._changes.items():
            if value is DELETED:
                try:
                    p.delete(key)
                except:
                    raise
            else:
                p.set(key, value)

        p.execute()


    def batch_over(self):
        self._track_diff = None
        self._write_target_db = None

