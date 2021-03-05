#!/usr/bin/env python3.5

import  abc
import  logging
logging.disable(logging.CRITICAL)

import  sys
from    io              import  BytesIO as IO
from    http.server     import  BaseHTTPRequestHandler, HTTPServer
from    socketserver    import  ThreadingMixIn
from    webob           import  Response
from    pathlib         import  Path
import  cgi
import  json
import  urllib
import  ast
import  shutil
import  datetime
import  time
import  inspect

import  threading
import  platform
import  socket
import  psutil
import  os

# debugging utilities
import  pudb

# pfstorage local dependencies
import  pfmisc
from    pfmisc._colors      import  Colors
from    pfmisc.debug        import  debug
from    pfmisc.C_snode      import *

def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate

class S:
    """
    A somewhat cryptically named class that keeps system state between
    separate modules/classes. This class was designed to keep object
    state even if instances of this object class are re-constructed --
    this typically occurs with certain modules such as the HTTPserver.
    Each call to the module re-initializes the StoreHandler class, which
    effectively means any per-instance state information is lost across
    calls.

    State-related class variables can thus be accessed by calling the
    class directly, 'S'. For example, to change values in the state
    tree structure, simply call 'S.T.<method>'.

    NOTE: derived classes MUST handle the checks on prior initializaion
    so as to not re-initialize this class once it has been created.

    """
    d_state = {}
    T       = C_stree()
    b_init  = False

    @classmethod
    def __get_validators__(cls):
        # one or more validators may be yielded which will be called in the
        # order to validate the input, each validator will receive as an input
        # the value returned from the previous validator
        yield cls.validate

    @classmethod
    def validate(cls, v):
        return cls

    def __repr__(self):
        """
        Return a representation of the internal state, esentially
        the dictionary called on the tree root node.
        """
        d_tree  = {}
        try:
            d_tree.update(next(self.T.__iter__()))
        except:
            pass
        return json.dumps({
            "tree"  : d_tree
        })

    def __call__(self, *args):
        """
        set/get components of the state object
        """
        if len(args) == 1:
            return S.T.cat(args[0])
        else:
            S.T.touch(args[0], args[1])

    def state_create(self, d_state, *args, **kwargs):
        """
        Create the internal object with specific state
        dictionary information.
        """

        for k,v in kwargs.items():
            if k == 'reinitialize': S.b_init    = v
        S.__init__(self, *args, **kwargs)
        if not S.b_init:
            S.d_state.update(d_state)
            S.T.initFromDict(S.d_state)
            S.b_init    = True
            if len(self('/this/debugToDir')):
                if not os.path.exists(self('/this/debugToDir')):
                    os.makedirs(self('/this/debugToDir'))
            self.dp     = pfmisc.debug(
                            verbosity   = self('/this/verbosity'),
                            within      = self('/this/name'),
                            colorize    = self('/this/colorize')
            )

        self.dp.qprint(
            Colors.YELLOW + "\n\t\tInternal data tree:",
            level   = 1,
            syslog  = False)
        self.dp.qprint(
            C_snode.str_blockIndent(str(S.T), 3, 8),
            level   = 1,
            syslog  = False)

    def state_init( self, d_args,
                    str_name    = "",
                    str_desc    = "",
                    str_version = ""
                    ):
        """
        Populate the internal <self.state> dictionary based on the
        passed 'args'
        """

        # Initializing from file state will always flush and
        # recreate, destroying any previous state.
        if 'str_configFileLoad' not in d_args.keys():
            d_args['str_configFileLoad']    = ''
        if 'str_configFileSave' not in d_args.keys():
            d_args['str_configFileSave']    = ''
        if 'str_debugToDir'     not in d_args.keys():
            d_args['str_debugToDir']        = '/tmp'
        if 'verbosity'          not in d_args.keys():
            d_args['verbosity']             = '0'
        if len(d_args['str_configFileLoad']):
            if Path(d_args['str_configFileLoad']).is_file():
                # Read configuration detail from JSON formatted file
                with open(d_args['str_configFileLoad']) as json_file:
                    S.d_state   = json.load(json_file)
                    S.b_init    = False
        else:
            S.d_state = \
            {
                'this': {
                    'name':                 str_name,
                    'version':              str_version,
                    'desc':                 str_desc,
                    'colorize':             False,
                    'verbosity':            int(d_args['verbosity']),
                    'debugToDir':           d_args['str_debugToDir'],
                    'configFileLoad':       d_args['str_configFileLoad'],
                    'configFileSave':       d_args['str_configFileSave'],
                    'args':                 d_args
                }
            }
            S.T.initFromDict(S.d_state)

    def __init__(self, *args, **kwargs):
        """
        Constructor. If the object has already been initialized by a subclass
        with a call to state_create(), then repeated calls of this constructor
        will not change object state values.
        """

        d_args          : dict  = {}
        str_desc        : str   = ''
        str_version     : str   = ''
        str_name        : str   = ''
        verbosity       : int   = 0
        str_within      : str   = ''
        b_colorize      : bool  = False

        # pudb.set_trace()

        for k,v in kwargs.items():
            if k == 'args':     d_args          = v
            if k == 'desc':     str_desc        = v
            if k == 'name':     str_name        = v
            if k == 'version':  str_version     = v

        if not S.b_init:
            self.state_init(d_args, str_name, str_desc, str_version)

        if not self('/this/verbosity'):  verbosity   = 0
        else: verbosity     = self('/this/verbosity')
        if not self('/this/name'):       str_within  = 'pfstate'
        else: str_within    = self('/this/name')
        if not self('/this/colorize'):   b_colorize  = False
        else: b_colorize    = self('/this/colorize')
        self.dp             = pfmisc.debug(
                                verbosity   = verbosity,
                                within      = str_within,
                                colorize    = b_colorize
        )

    def leaf_process(self, **kwargs):
        """
        Process the storage state tree and perform possible env substitutions.
        """
        str_path    = ''
        str_target  = ''
        str_newVal  = ''

        for k,v in kwargs.items():
            if k == 'where':    str_path    = v
            if k == 'replace':  str_target  = v
            if k == 'newVal':   str_newVal  = v

        str_parent, str_file    = os.path.split(str_path)
        str_pwd                 = S.T.cwd()
        if S.T.cd(str_parent)['status']:
            str_origVal     = S.T.cat(str_file)
            str_replacement = str_origVal.replace(str_target, str_newVal)
            S.T.touch(str_path, str_replacement)
            S.T.cd(str_pwd)

    def internalvar_getProcess(self, d_meta):
        """
        process the 'get' directive
        """
        str_var     = d_meta['var']
        d_ret       = {}
        b_status    = False
        T           = C_stree()

        if S.T.isdir(str_var):
            S.T.copy(startPath = str_var, destination = T)
            d_ret                   = dict(T.snode_root)
        else:
            d_ret[str_var]          = S.T.cat(str_var)
        b_status                = True
        return b_status, d_ret

    def internalvar_setProcess(self, d_meta):
        """
        process the 'set' directive
        """
        str_var     = d_meta['var']
        d_ret       = {}
        b_status    = False
        b_tree      = False

        try:
            d_set       = json.loads(d_meta['set'])
        except:
            str_set     = json.dumps(d_meta['set'])
            d_set       = json.loads(str_set)
            if isinstance(d_set, dict):
                b_tree  = True
        if b_tree:
            D       = C_stree()
            D.initFromDict(d_set)
            if not S.T.exists(str_var):
                S.T.mkdir(str_var)
            for topDir in D.lstr_lsnode():
                D.copy(
                        startPath       = '/'+topDir,
                        destination     = S.T,
                        pathDiskRoot    = str_var
                    )
            d_ret           = d_set
        else:
            S.T.touch(str_var, d_meta['set'])
            d_ret[str_var]  = S.T.cat(str_var)
        b_status    = True
        return b_status, d_ret

    def internalvar_valueReplaceProcess(self, d_meta):
        """
        process the 'valueReplace' directive

        Find all the values in the internalctl tree
        and replace the value corresponding to 'var' with
        the field of 'valueReplace'
        """

        hits            = 0
        l_fileChanged   = []

        def fileContentsReplaceAtPath(str_path, **kwargs):
            nonlocal    hits
            nonlocal    l_fileChanged
            b_status        = True
            str_target      = ''
            str_value       = ''
            self.dp.qprint('In dir = %s, hits = %d' % (str_path, hits))
            for k, v in kwargs.items():
                if k == 'target':   str_target  = v
                if k == 'value':    str_value   = v
            for str_hit in S.T.lsf(str_path):
                str_content = S.T.cat(str_hit)
                self.dp.qprint('%20s: %20s' % (str_hit, str_content))
                if str_content  == str_target:
                    self.dp.qprint('%20s: %20s' % (str_hit, str_value))
                    S.T.touch(str_hit, str_value)
                    b_status    = True
                    hits        = hits + 1
                    l_fileChanged.append(str_path + '/' + str_hit)

            return {
                    'status':           b_status,
                    'l_fileChanged':    l_fileChanged
                    }

        d_ret       = {}
        b_status    = False
        str_target      = d_meta['var']
        str_value       = d_meta['valueReplace']
        if str_value    == 'ENV':
            if str_target.strip('%') in os.environ:
                str_value   = os.environ[str_target.strip('%')]
        d_ret = S.T.treeExplore(
                f       = fileContentsReplaceAtPath,
                target  = str_target,
                value   = str_value
                )
        b_status        = d_ret['status']
        d_ret['hits']   = hits
        return b_status, d_ret

    def internalctl_varprocess(self, *args, **kwargs):
        """

        get/set a specific variable as parsed from the meta JSON.

        :param args:
        :param kwargs:
        :return:
        """

        d_meta          = {}
        d_ret           = {}
        b_status        = False

        for k,v in kwargs.items():
            if k == 'd_meta':   d_meta  = v

        if d_meta:
            if 'get' in d_meta.keys():
                b_status, d_ret = self.internalvar_getProcess(d_meta)

            if 'set' in d_meta.keys():
                # pudb.set_trace()
                b_status, d_ret = self.internalvar_setProcess(d_meta)

            if 'valueReplace' in d_meta.keys():
                b_status, d_ret = self.internalvar_valueReplaceProcess(d_meta)

        return {'d_ret':    d_ret,
                'status':   b_status}

    def internalctl_process(self, *args, **kwargs):
        """

        Process the 'internalctl' action.

                {  "action": "internalctl",
                        "meta": {
                            "var":      "/tree/path",
                            "set":     "<someValue>"
                        }
                }

                {  "action": "internalctl",
                        "meta": {
                            "var":      "/tree/path",
                            "get":      "currentPath"
                        }
                }

        :param args:
        :param kwargs:
        :return:
        """

        d_request           = {}
        b_status            = False
        d_ret               = {
            'status':   b_status
        }

        for k,v in kwargs.items():
            if k == 'request':   d_request   = v
        if d_request:
            d_meta  = d_request['meta']
            d_ret   = self.internalctl_varprocess(d_meta = d_meta)
        return d_ret


