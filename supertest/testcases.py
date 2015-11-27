import six

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import Client
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select

# Preference is to use Xvfb for off-screen rendering. The reason is that
# PhantomJS can be a bit behind in terms of JS support, so using FF is
# better.
try:
    from easyprocess import EasyProcessCheckInstalledError
    from pyvirtualdisplay import Display
except ImportError:
    pass


class CommonMixin(object):
    """Common components between the Selenium `Element` and the
    `TestCase`.
    """

    def sleep(self, sec):
        if sec:
            time.sleep(sec)

    def find(self, selector):
        return Element(self.wd.find_element_by_css_selector(selector))

    def click(self, selector=None, sleep=None):
        self.sleep(sleep)
        if selector:
            elem = self.find(selector)
            if not elem:
                raise Exception('Element not found.')
        else:
            elem = self
        elem.wd.click()
        return elem

    def send_keys(self, selector, value, sleep=None):
        self.sleep(sleep)
        elem = self.click(selector)
        elem.wd.send_keys(value)
        return elem

    def select(self, selector, text):
        elem = self.find(selector)
        sel = Select(elem.wd)
        sel.select_by_visible_text(text)
        return elem

    def attr(self, name):
        return self.wd.get_attribute(name)


class Element(CommonMixin):

    def __init__(self, web_elem):
        self.web_elem = web_elem
        self.wd = web_elem


class UnitTestCaseMixin(object):
    pass


class FunctionalTestCaseMixin(object):
    pass


class IntegrationTestCaseMixin(object):
    pass


class SeleniumTestCaseMixin(CommonMixin, IntegrationTestCaseMixin):

    def __init__(self, *args, **kwargs):
        super(SeleniumTestCaseMixin, self).__init__(*args, **kwargs)
        settings.DEBUG = getattr(self, 'use_debug', True)
        self.webdriver_type = kwargs.get('driver', getattr(self, 'driver', getattr(settings, 'SELENIUM_DRIVER', 'firefox')))
        self.hidden = kwargs.get('hidden', getattr(self, 'hidden', getattr(settings, 'SELENIUM_HIDDEN', True)))

    def setUp(self):

        # Use a hidden display to avoid browser windows popping up.
        # But only if it's available.
        self.display = None
        if self.hidden and self.webdriver_type != 'phantomjs':
            try:
                self.display = Display(visible=0, size=(1920, 1200))
                self.display.start()
            except NameError:
                six.print_('Warning: pyvirtualdisplay required for off-screen rendering.')
            except EasyProcessCheckInstalledError:
                six.print_('Warning: Xvfb not installed, browser will not be hidden.')

        if self.webdriver_type == 'chrom':
            self.wd = webdriver.Chrome()
        elif self.webdriver_type == 'phantomjs':
            self.wd = webdriver.PhantomJS()
            self.wd.set_window_size(1920, 1200)
        else:
            self.wd = webdriver.Firefox()
        self.wd.implicitly_wait(2)
        self.client = Client()

    def tearDown(self):
        self.wd.quit()
        if self.display is not None:
            self.display.stop()

    def create_user(self, username, password, superuser=False, login=False):
        user_model = get_user_model()
        try:
            self.user = user_model.objects.get(username=username)
        except user_model.DoesNotExist:
            if superuser:
                self.user = user_model.objects.create_superuser(
                    username=username,
                    # first_name=self.first_name,
                    # last_name=self.last_name,
                    password=password,
                    # email=self.email,
                )
            else:
                self.user = user_model.objects.create_user(
                    username=username,
                    # first_name=self.first_name,
                    # last_name=self.last_name,
                    password=password,
                    # email=self.email,
                )
        if login:
            self.login_user(username, password)

    def login_user(self, username, password):
        self.client.login(username=username, password=password)
        cookie = self.client.cookies['sessionid']
        self.wd.get(self.live_server_url + '/admin/')
        self.wd.add_cookie({'name': 'sessionid', 'value': cookie.value, 'secure': False, 'path': '/'})

    def open(self, url, create_superuser=False):
        # if create_superuser:
        #     self.create_user()
        self.wd.get('%s%s'%(self.live_server_url, url))
        # time.sleep(1)

    def screenshot(self, filename):
        self.wd.save_screenshot(filename)

    def js(self, code):
        return self.wd.execute_script(code)

    def is_jquery_ready(self):
        return self.js('return jQuery.isReady') == 'True'

    def wait_for_load(self, sleep=2):
        self.sleep(sleep)
        for ii in range(10):
            if self.js('return document.readyState') == 'complete':
                return
            self.sleep(1)
        raise AssertionError('Page did not load.')

    def assertElementExists(self, selector, sleep=None):
        self.sleep(sleep)
        try:
            elem = self.find(selector)
        except NoSuchElementException:
            raise AssertionError('No such element exists.')

    def assertCurrentPath(self, path):
        url = self.wd.current_url
        cur_path = '/' + '/'.join(url.split('/')[3:])
        if path != cur_path:
            raise AssertionError('Paths do not match.')


class SeleniumTestCase(SeleniumTestCaseMixin, StaticLiveServerTestCase):
    pass
