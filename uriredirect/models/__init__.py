from __future__ import absolute_import
from builtins import *

from .RewriteRule import *
from .Profile import *
from .UriRegister import *
from .AcceptMapping import *
from .MediaType import *
try:
    from .RewriteRule import *
    from .Profile import *
    from .UriRegister import *
    from .AcceptMapping import *
    from .MediaType import *
except:
   from models import *

__version__ = (1, 1)

