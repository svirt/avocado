# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

import sys

from .base import CLICmd
from avocado.core import test
from avocado.core import loader
from avocado.core import output
from avocado.core import exit_codes
from avocado.utils import astring


class TestLister(object):

    """
    Lists available test modules
    """

    def __init__(self, args):
        use_paginator = args.paginator == 'on'
        self.view = output.View(app_args=args, use_paginator=use_paginator)
        self.term_support = output.TermSupport()
        try:
            loader.loader.load_plugins(args)
        except loader.LoaderError, details:
            sys.stderr.write(str(details))
            sys.stderr.write('\n')
            sys.exit(exit_codes.AVOCADO_FAIL)
        self.args = args

    def _extra_listing(self):
        loader.loader.get_extra_listing()

    def _get_test_suite(self, paths):
        which_tests = loader.ALL if self.args.verbose else loader.AVAILABLE
        try:
            return loader.loader.discover(paths,
                                          which_tests=which_tests)
        except loader.LoaderUnhandledUrlError, details:
            self.view.notify(event="error", msg=str(details))
            self.view.cleanup()
            sys.exit(exit_codes.AVOCADO_FAIL)

    def _get_test_matrix(self, test_suite):
        test_matrix = []

        type_label_mapping = loader.loader.get_type_label_mapping()
        decorator_mapping = loader.loader.get_decorator_mapping()

        stats = {}
        for value in type_label_mapping.values():
            stats[value.lower()] = 0

        for cls, params in test_suite:
            id_label = ''
            if isinstance(cls, str):
                type_label = cls
            else:
                type_label = cls.__name__

            if 'params' in params:
                id_label = params['params']['id']
            else:
                if 'name' in params:
                    id_label = params['name']
                elif 'path' in params:
                    id_label = params['path']

            try:
                type_label = type_label_mapping[cls]
                decorator = decorator_mapping[cls]
                stats[type_label.lower()] += 1
                type_label = decorator(type_label)
            except KeyError:
                if isinstance(cls, str):
                    cls = test.Test
                    type_label = type_label_mapping[cls]
                    decorator = decorator_mapping[cls]
                    stats[type_label.lower()] += 1
                    type_label = decorator(type_label)
                    id_label = params['name']
                elif issubclass(cls, test.Test):
                    cls = test.Test
                    type_label = type_label_mapping[cls]
                    decorator = decorator_mapping[cls]
                    stats[type_label.lower()] += 1
                    type_label = decorator(type_label)
                    id_label = params['name']

            test_matrix.append((type_label, id_label))

        return test_matrix, stats

    def _display(self, test_matrix, stats):
        header = None
        if self.args.verbose:
            header = (self.term_support.header_str('Type'), self.term_support.header_str('Test'))

        for line in astring.iter_tabular_output(test_matrix, header=header):
            self.view.notify(event='minor', msg="%s" % line)

        if self.args.verbose:
            self.view.notify(event='minor', msg='')
            for key in sorted(stats):
                self.view.notify(event='message', msg=("%s: %s" % (key.upper(), stats[key])))

    def _list(self):
        self._extra_listing()
        test_suite = self._get_test_suite(self.args.keywords)
        test_matrix, stats = self._get_test_matrix(test_suite)
        self._display(test_matrix, stats)

    def list(self):
        rc = 0
        try:
            self._list()
        except KeyboardInterrupt:
            rc = exit_codes.AVOCADO_FAIL
            msg = 'Command interrupted by user...'
            if self.view is not None:
                self.view.notify(event='error', msg=msg)
            else:
                sys.stderr.write(msg)
        finally:
            if self.view:
                self.view.cleanup()
        return rc


class List(CLICmd):

    """
    Implements the avocado 'list' subcommand
    """

    name = 'list'
    description = 'List available tests'

    def configure(self, parser):
        """
        Add the subparser for the list action.

        :param parser: Main test runner parser.
        """
        parser = super(List, self).configure(parser)
        parser.add_argument('keywords', type=str, default=[], nargs='*',
                            help="List of paths, aliases or other "
                            "keywords used to locate tests. "
                            "If empty, avocado will list tests on "
                            "the configured test source, "
                            "(see 'avocado config --datadir') Also, "
                            "if there are other test loader plugins "
                            "active, tests from those plugins might "
                            "also show up (behavior may vary among "
                            "plugins)")
        parser.add_argument('-V', '--verbose',
                            action='store_true', default=False,
                            help='Whether to show extra information '
                            '(headers and summary). Current: %(default)s')
        parser.add_argument('--paginator',
                            choices=('on', 'off'), default='on',
                            help='Turn the paginator on/off. '
                            'Current: %(default)s')
        loader.add_loader_options(parser)

    def run(self, args):
        test_lister = TestLister(args)
        return test_lister.list()
