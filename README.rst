###################
pfstate  v1.1.1.4
###################

.. image:: https://badge.fury.io/py/pfstate.svg
    :target: https://badge.fury.io/py/pfstate

.. image:: https://travis-ci.org/FNNDSC/pfstate.svg?branch=master
    :target: https://travis-ci.org/FNNDSC/pfstate

.. image:: https://img.shields.io/badge/python-3.5%2B-blue.svg
    :target: https://badge.fury.io/py/pfcon

.. contents:: Table of Contents

********
Overview
********

This repository provides ``pfstate`` -- a library / module that maintains state in the object/class definition (and not in a class instance). The module uses the tree ``C_snode`` data abstraction internally (see elsewhere for ``C_snode``) as well as some internal methods to set/get this internal data in various ways.

pfstate
=======

Most simply, ``pfstate`` is a module that keeps state in a class definition (as opposed to a class instance). It was primarily created in the context of custom ``ThreadedHTTPServer`` classes. Creating a ``ThreadedHTTPServer`` in python involves instantiating the ``ThreadedHTTPServer``, and in the constructor providing a derived ``BaseHTTPRequestHandler`` object. The design pattern has some structural shortcomings -- most notably that the difficulty in setting internal ``BaseHTTPRequestHandler`` data from the level of the ``ThreadedHTTPServer``. One mechanism to overcome this is to share a common single ``pfstate`` object across the scope of both the server and the handler.

Moreover, each call to the ``ThreadedHTTPServer`` re-initializes the handler object derived from ``BaseHTTPRequestHandler``, so any state information in that object instance is lost across calls.

By using the ``pfstate`` module, however, in the handler object, state information can be preserved across calls to the ``ThreadedHTTPServer`` by keeping state in the object and not an instance of the object. 

In some ways, this can be thought of a cleaner way to avoid using a global variable.

Consult the source code for full detail. However, as a simple overview, the recommended method of using this module is to define a subclass containing the state-specific information in a dictionary, and then to initialize the class.

Note, it is vitally important that this derived class check the initialization of the base object data so as to not re-initialize an already stateful object and hence lose any additional state information.

.. code-block:: python

    from    pfmisc.C_snode      import C_snode
    from    pfmisc._colors      import Colors
    from    pfstate             import S
    from    argparse            import RawTextHelpFormatter
    from    argparse            import ArgumentParser

    str_desc        = "some program description"
    str_version     = "1.0.0.0"

    parser          = ArgumentParser(
                        description = str_desc, 
                        formatter_class = RawTextHelpFormatter
                    )

    parser.add_argument(
        '--msg',
        action  = 'store',
        dest    = 'msg',
        default = '',
        help    = 'Message payload for internalctl control.'
    )

    class D(S):
        """
        A derived class with problem-specific state
        """

        def __init__(self, *args, **kwargs):
            """
            Constructor
            """
            S.__init__(self, *args, **kwargs)
            if not S.b_init:
                d_specific  = \
                    {
                        'specificState': {
                            'desc':         'Additional state information',
                            'theAnswer':    42,
                            'theQuestion':  'What do you get if you multiple six by nine',
                            'foundBy':      'Arthur Dent'
                        },
                        'earthState': {
                            'current':      'Destroyed',
                            'reason':       'Hyper space bypass',
                            'survivors': {
                                'humans':   ['Arthur Dent', 'Ford Prefect', 'Trillian'],
                                'dolphins': 'Most of them'
                            }
                        }
                    }
                S.d_state.update(d_specific)
                S.T.initFromDict(S.d_state)
                S.b_init    = True
                if len(S.T.cat('/this/debugToDir')):
                    if not os.path.exists(S.T.cat('/this/debugToDir')):
                        os.makedirs(S.T.cat('/this/debugToDir'))

            self.dp.qprint(
                Colors.YELLOW + "\n\t\tInternal data tree:", 
                level   = 1,
                syslog  = False)
            self.dp.qprint(
                C_snode.str_blockIndent(str(S.T), 3, 8), 
                level   = 1,
                syslog  = False)

    state   = D( 
        version     = str_version,
        desc        = str_desc,
        args        = vars(args)
    )

    if len(args.msg):
        d_control = state.internalctl_process(request = json.loads(args.msg))
        print(
            json.dumps(
                d_control,
                indent = 4
            )
        )

************
Installation
************

Installation is relatively straightforward, and we recommend using python ```pip`` to simplu install the module, preferably in a python virtual environment.

Python Virtual Environment
==========================

On Ubuntu, install the Python virtual environment creator

.. code-block:: bash

  sudo apt install virtualenv

Then, create a directory for your virtual environments e.g.:

.. code-block:: bash

  mkdir ~/python-envs

You might want to add to your .bashrc file these two lines:

.. code-block:: bash

    export WORKON_HOME=~/python-envs
    source /usr/local/bin/virtualenvwrapper.sh

Note that depending on distro, the virtualenvwrapper.sh path might be

.. code-block:: bash

    /usr/share/virtualenvwrapper/virtualenvwrapper.sh

Subsequently, you can source your ``.bashrc`` and create a new Python3 virtual environment:

.. code-block:: bash

    source .bashrc
    mkvirtualenv --python=python3 python_env

To activate or "enter" the virtual env:

.. code-block:: bash

    workon python_env

To deactivate virtual env:

.. code-block:: bash

    deactivate

Install the module

.. code-block:: bash
 
    pip install pfstate


Using the ``fnndsc/pfstorage`` docker container
================================================

For completeness sake with other pf* packages, a dockerized build is provided, although its utility is debatable and running / building the docker image will serve little purpose.

*****
Usage
*****

For usage of  ``pstate``, consult the relevant wiki pages  <https://github.com/FNNDSC/pfstate/wiki/pfstate-overview>`.


Command line arguments
======================

.. code-block:: html

        [--msg '<JSON_formatted>']
        An optional JSON formatted string exemplifying how to get and
        set internal variables.
        
        --msg '
        {  
            "action": "internalctl",
            "meta": {
                        "var":     "/",
                        "get":      "value"
                    }
        }'

        --msg '
        {   "action": "internalctl",
            "meta": {
                        "var":     "/service/megalodon",
                        "set":     {
                            "compute": {
                                "addr": "10.20.1.71:5010",
                                "baseURLpath": "api/v1/cmd/",
                                "status": "undefined"
                            },
                            "data": {
                                "addr": "10.20.1.71:5055",
                                "baseURLpath": "api/v1/cmd/",
                                "status": "undefined"
                            }
                        }
                    }
        }'

        [--configFileLoad <file>]
        Load configuration information from the JSON formatted <file>.

        [--configFileSave <file>]
        Save configuration information to the JSON formatted <file>.

        [-x|--desc]                                     
        Provide an overview help page.

        [-y|--synopsis]
        Provide a synopsis help summary.

        [--version]
        Print internal version number and exit.

        [--debugToDir <dir>]
        A directory to contain various debugging output -- these are typically
        JSON object strings capturing internal state. If empty string (default)
        then no debugging outputs are captured/generated. If specified, then
        ``pfcon`` will check for dir existence and attempt to create if
        needed.

        [-v|--verbosity <level>]
        Set the verbosity level. "0" typically means no/minimal output. Allows for
        more fine tuned output control as opposed to '--quiet' that effectively
        silences everything.

EXAMPLES

.. code-block:: bash

    pfstate                                                \\
        --msg ' 
            {  "action": "internalctl",
                "meta": {
                            "var":     "/",
                            "get":      "value"
                        }
            }'

