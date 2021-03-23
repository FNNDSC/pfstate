###################
pfstate  v2.2.12
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

    from    pfstate             import S
    from    argparse            import RawTextHelpFormatter
    from    argparse            import ArgumentParser

    str_desc        = "some program description"
    str_version     = "1.0.0"
    str_name        = "Example module"

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
        A derived 'pfstate' class that keeps system state.

        See https://github.com/FNNDSC/pfstate for more information.
        """

        def __init__(self, *args, **kwargs):
            """
            An object to hold some generic/global-ish system state, in C_snode
            trees.
            """
        self.state_create(
        {
            'additionalState': {
                'desc':         'Additional state information',
                'theAnswer':    42,
                'theQuestion':  'What do you get if you multiple six by nine',
                'foundBy':      'Arthur Dent',
                'note':     {
                    'additional':   'was this really Arthur Dent, though?',
                    'action':   {
                        'item1':    'further research might be needed'
                    }
                }
            },
            'earthState': {
                'current':      'Destroyed',
                'reason':       'Hyper space bypass',
                'survivors': {
                    'humans':   ['Arthur Dent', 'Ford Prefect', 'Trillian'],
                    'dolphins': 'Most of them',
                    'note': {
                        'exception':    'Ford Prefect is not a human'
                    }
                }
            }
        },
        *args, **kwargs)

    state      = D(
        version     = str_version,
        name        = str_name,
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

  python3 -m venv <virtualEnvPath>

Install the module

.. code-block:: bash

    pip install pfstate

*****
Usage
*****

For usage of  ``pstate``, consult the relevant wiki pages  <https://github.com/FNNDSC/pfstate/wiki/pfstate-overview>`.


Command line arguments
======================

.. code-block:: html

        [--test <directive>]
        If specified, return some test states. Usually this is some
        path into an internal test state tree. If the <directive> is
        the actual text 'tree', then return the test object representation
        of itself.

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
        Set the verbosity level. "0" typically means no/minimal output. Allows
        for more fine tuned output control as opposed to '--quiet' that effectively silences everything.

EXAMPLES

.. code-block:: bash

    $>pfstate --test '/earthState'      # return a dictionary representation of
                                        # this node in the internal test data

    $>pfstate --test 'tree'             # return the raw internal test data

    $>pfstate  \\
        --msg '
            {  "action": "internalctl",
                "meta": {
                            "var":     "/",
                            "get":      "value"
                        }
            }'

