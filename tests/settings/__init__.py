from tests.settings.base import *

try:
    from tests.settings.local import *
except ImportError:
    pass
