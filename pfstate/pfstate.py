#!/usr/bin/env python3.5

import  abc

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
import  pprint

import  threading
import  platform
import  socket
import  psutil
import  os
import  multiprocessing
import  pfurl
import  configparser
import  swiftclient

import  pfmisc

# debugging utilities
import  pudb

# pfstorage local dependencies
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
    A somewhat cryptically named class that keeps system state.

    Calls to the HTTPServer re-initialize the StoreHandler class -- this
    effectively means any per-instance state information is lost across
    calls.

    Barring the use of a module-wide global variable, this class keeps
    state information as a class (not instance)-variable -- which
    effectively is analogous to a namespaced global variable.

    State-related class variables can thus be accessed by calling the
    class directly, 'S'. For example, to change values in the state
    tree structure, simply call 'S.T.<method>'.

    NOTE: derived classes MUST handle the checks on prior initializaion
    so as to not re-initialize this class once it has been created.

    """
    d_state =  {}
    T       = C_stree()
    b_init  = False

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
                    'verbosity':            int(d_args['verbosity']),
                    'debugToDir':           d_args['str_debugToDir'],
                    'configFileLoad':       d_args['str_configFileLoad'],
                    'configFileSave':       d_args['str_configFileSave'],
                    'args':                 d_args
                }
            }

    def __init__(self, *args, **kwargs):
        """
        The logic of this constructor reflects a bit from legacy design
        patterns of `pfcon` -- specifically the passing of flags in a
        single structure, and the <self.state> dictionary to try and
        organize the space of <self> variables a bit logically.
        """

        d_args                  = {}
        str_desc                = ''
        str_version             = ''

        # pudb.set_trace()

        for k,v in kwargs.items():
            if k == 'args':     d_args          = v
            if k == 'desc':     str_desc        = v
            if k == 'name':     str_name        = v
            if k == 'version':  str_version     = v

        if not S.b_init:
            self.state_init(d_args, str_name, str_desc, str_version)

        self.dp                 = pfmisc.debug(
                                            verbosity   = S.T.cat('/this/verbosity'),
                                            within      = S.T.cat('/this/name')
                                            )
        self.pp                 = pprint.PrettyPrinter(indent=4)

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


