import unittest, sys, re
import inspect, traceback

from functools import partialmethod


class OmocTestCase(unittest.TestCase):



    @classmethod
    def suite(cls):
        return None
        # return (
        #     'test_method1',
        #     'test_method2',
        #     cls.test_method3
        #     cls.test_method4
        # )


    # 使用TextRunner运行本测试
    @classmethod
    def runInText(cls):
        ############################################################################
        # discover tests to run, subclass can override suite() to define it.
        #     _test_def can be string , function , or seq of them(can be mixed)
        #     test_suite is suite of TestCase , complying with pyunit standard
        ############################################################################
        test_suite, _test_def = None, cls.suite()
        if _test_def is None:
            test_suite = unittest.defaultTestLoader.loadTestsFromTestCase(cls)
        else:
            if isinstance(_test_def, str) or callable(_test_def):
                _test_def = (_test_def,)

            test_suite = unittest.TestSuite()
            if hasattr(_test_def, '__iter__'):
                for _t in _test_def:
                    testname = _t if isinstance(_t, str) else _t.__name__ if callable(_t) else None
                    if testname is not None:
                        test_suite.addTest(cls(testname))

        runner = unittest.TextTestRunner(stream=sys.stdout,verbosity=2)
        runner.run(test_suite)




    #################################################################################################
    # usage:
    # with self.should_raise(ValueError, IOError,
    #                        satisfy=lambda e: str(e) == "something wrong"):
    #     raise ValueError("something wrong")
    #################################################################################################
    def should_raise(self, *types, satisfy=None, message=None):
        return ExceptionHuntingContext(self, *types, satisfy = satisfy, message = message)




#################################################################################################
# usage:
# with ExceptionHuntingContext(ValueError, AssertionError, IOError,
#                              satisfy = lambda e: "detailed error information" in str(e),
#                              message = "should raise error"
#                              ):
#    do_some_test( which should raise expected Error )...
#################################################################################################
class ExceptionHuntingContext:

    def __init__(self, testcase, *types, satisfy = None, message = None ):
        self.testcase = testcase
        self.error_types = types or (BaseException)
        self.error_satisfy = satisfy
        self.message = message

    def __enter__(self):
        pass

    def __exit__(self, etype, evalue, etrace):

        type_matched = etype is not None and issubclass(etype, self.error_types)
        satisfied = self.error_satisfy is None or self.error_satisfy(evalue)

        if type_matched and satisfied:
            return True

        message = self.message
        if message == None:
            if not type_matched:
                message = "should raise Exception among ({}), but got <{}>: \n\t {}".format(
                    ", ".join((t.__name__ for t in self.error_types)),
                    etype,
                    traceback.format_exception_only(etype, evalue)
                )
            elif not satisfied:
                message = "raised Exception:\n\t {} \n\t did not satisfy critetia: \n\t{}".format(
                    repr(evalue),
                    inspect.getsource(self.error_satisfy)
                )

        raise AssertionError(message)



