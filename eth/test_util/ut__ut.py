from .ut import OmocTestCase



class SampleTest(OmocTestCase):

    def test_should_raise(self):
        ##############################################################################
        #   fail if not raise any of given Errors
        ##############################################################################
        try:
            with self.should_raise(ValueError):
                pass
            self.fail("shoud not go here")
        except AssertionError as e:
            pass

        ##############################################################################
        #   pass if raise any of given Errors
        ##############################################################################
        with self.should_raise(ValueError, IOError):
            raise IOError("somthing wrong")


        ##############################################################################
        #   fail if raised Error didn't match critetia
        ##############################################################################
        try:
            with self.should_raise(ValueError, satisfy=lambda e: str(e) == "something wrong"):
                raise ValueError("AAA")
            self.fail("should not go here")
        except AssertionError as e:
            pass

        ##############################################################################
        #   pass if raise correct Error type and match critetia
        ##############################################################################
        with self.should_raise(ValueError, IOError,
                               satisfy=lambda e: str(e) == "something wrong"):
            raise ValueError("something wrong")


        ##############################################################################
        #   create a exception hunter context and reuse it
        ##############################################################################
        exception_hunter = self.should_raise(ValueError, IOError, ArithmeticError,
                                             satisfy=lambda e: str(e) == "something wrong")

        try:
            with exception_hunter:
                raise ValueError("value wrong")
            self.fail("should not go here")
        except AssertionError as e:
            pass

        with exception_hunter:
            raise ArithmeticError("something wrong")






