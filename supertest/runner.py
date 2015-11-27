import six
import unittest
from unittest.mock import patch
from unittest import TestCase

from django.test import TransactionTestCase

from .testcases import UnitTestCaseMixin, FunctionalTestCaseMixin, IntegrationTestCaseMixin

# Need a Django 1.6 fallback.
try:
    from django.test.runner import DiscoverRunner as BaseRunner
except ImportError:
    from django.test.simple import DjangoTestSuiteRunner as BaseRunner


class NoDatabaseMixin(object):
    """
    Test runner mixin which skips the DB setup/teardown
    when there are no subclasses of TransactionTestCase to improve the speed
    of running the tests.
    """

    def build_suite(self, *args, **kwargs):
        """
        Check if any of the tests to run subclasses TransactionTestCase.
        """
        suite = super(NoDatabaseMixin, self).build_suite(*args, **kwargs)
        self._needs_db = any([isinstance(test, TransactionTestCase) for test in suite])
        return suite

    def setup_databases(self, *args, **kwargs):
        """
        Skip test creation if not needed. Ensure that touching the DB raises and
        error.
        """
        if self._needs_db:
            return super(NoDatabaseMixin, self).setup_databases(*args, **kwargs)
        if self.verbosity >= 1:
            six.print_('No DB tests detected. Skipping Test DB creation...')
        self._db_patch = patch('django.db.backends.utils.CursorWrapper')
        self._db_mock = self._db_patch.start()
        self._db_mock.side_effect = RuntimeError('No testing the database!')
        return None

    def teardown_databases(self, *args, **kwargs):
        """
        Remove cursor patch.
        """
        if self._needs_db:
            return super(NoDatabaseMixin, self).teardown_databases(*args, **kwargs)
        self._db_patch.stop()
        return None


class SuperTestLoader(unittest.TestLoader):
    """Load tests based on selected test type."""

    TEST_TYPE_MAP = {
        None: None,
        'all': TestCase,
        'unit': UnitTestCaseMixin,
        'functional': FunctionalTestCaseMixin,
        'integration': IntegrationTestCaseMixin,
    }

    def __init__(self, *args, **kwargs):
        self.tests_type = kwargs.pop('tests_type', None)
        self.tests_type = self.TEST_TYPE_MAP[self.tests_type]
        super(SuperTestLoader, self).__init__(*args, **kwargs)

    def loadTestsFromModule(self, module, *args, pattern=None, **kws):
        """Return a suite of all tests cases contained in the given module"""

        # This method used to take an undocumented and unofficial
        # use_load_tests argument.  For backward compatibility, we still
        # accept the argument (which can also be the first position) but we
        # ignore it and issue a deprecation warning if it's present.
        if len(args) > 0 or 'use_load_tests' in kws:
            warnings.warn('use_load_tests is deprecated and ignored',
                          DeprecationWarning)
            kws.pop('use_load_tests', None)
        if len(args) > 1:
            # Complain about the number of arguments, but don't forget the
            # required `module` argument.
            complaint = len(args) + 1
            raise TypeError('loadTestsFromModule() takes 1 positional argument but {} were given'.format(complaint))
        if len(kws) != 0:
            # Since the keyword arguments are unsorted (see PEP 468), just
            # pick the alphabetically sorted first argument to complain about,
            # if multiple were given.  At least the error message will be
            # predictable.
            complaint = sorted(kws)[0]
            raise TypeError("loadTestsFromModule() got an unexpected keyword argument '{}'".format(complaint))
        tests = []
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, TestCase):
                if self.tests_type is not None and not issubclass(obj, self.tests_type):
                    continue
                if self.tests_type is None and issubclass(obj, IntegrationTestCaseMixin):
                    continue
                tests.append(self.loadTestsFromTestCase(obj))

        load_tests = getattr(module, 'load_tests', None)
        tests = self.suiteClass(tests)
        if load_tests is not None:
            try:
                return load_tests(self, tests, pattern)
            except Exception as e:
                error_case, error_message = _make_failed_load_tests(
                    module.__name__, e, self.suiteClass)
                self.errors.append(error_message)
                return error_case
        return tests

    # def _match_path(self, path, full_path, pattern):
    #     if self.tests_type:
    #         sub = os.path.sep + self.tests_type + os.path.sep
    #         if sub not in full_path:
    #             return False
    #     return super(SuperTestLoader, self)._match_path(path, full_path, pattern)


class SuperTestRunnerMixin(object):

    def __init__(self, *args, **kwargs):
        tests_type = kwargs.pop('test', None)
        self.test_loader = SuperTestLoader(tests_type=tests_type)
        super(SuperTestRunnerMixin, self).__init__(*args, **kwargs)

    @classmethod
    def add_arguments(cls, parser):
        BaseRunner.add_arguments(parser)
        parser.add_argument('--test',
            action='store', dest='test', default=None,
            choices=['all', 'unit', 'functional', 'integration'],
            help='Select the kind of tests to run.')


class SuperTestRunner(SuperTestRunnerMixin, NoDatabaseMixin, BaseRunner):
    """Actual test runner sub-class to make use of the mixin."""
    pass
