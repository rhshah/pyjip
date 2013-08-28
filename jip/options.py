#!/usr/bin/env pythons
"""The options module contains the classes and functions
to wrap script/tool options. The Options class is a container
for a set of options and provides class functions to
load options from either a docstring (from_docopt) or from a
populated argpars parser instance.
"""
import sys

TYPE_OPTION = "option"
TYPE_INPUT = "input"
TYPE_OUTPUT = "output"


class Option(object):
    """A script option covers the most basic information about a
    script option. This covers the following attributes::

        name         a unique name that is used to identify the option
        short        the short representation, i.e -a
        long         the long representation, i.e --name
        type         optional type
        nargs        number of arguments, supports 0, 1, + and *
        default      optional default value
        value        list of current values for this option
        description  optional description
        required     the option needs to be specified
        hidden       the option is hidden on the command line
        join         optional join character for list options
        option_type  the option type, one of TYPE_OPTION, TYPE_INPUT,
                     TYPE_OUTPUT

    Please note that values are always represented as a list.
    """
    def __init__(self, name, short=None, long=None, type=None, nargs=None,
                 default=None, value=None, description=None, required=False,
                 hidden=False, join=" ", option_type=TYPE_OPTION):
        self.name = name
        self.short = short
        self.long = long
        self.type = type
        self.option_type = option_type
        self.nargs = nargs
        self.default = default
        self.description = description
        self.required = required
        self.hidden = hidden
        self.join = join
        self.nargs = nargs
        if self.nargs is None:
            if isinstance(default, bool):
                self.nargs = 0
            else:
                if not isinstance(default, (list, tuple)):
                    self.nargs = 1
                else:
                    self.nargs = "*"

        self.value = value if value is not None else default

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = []
        if value is not None:
            self._value = [value] if not isinstance(value, (list, tuple)) \
                else value
        ## check default values
        self._value = map(lambda v: self.__resolve_default(v),
                          self._value)

    def __resolve_default(self, v):
        """helper function to resolve stdin, stdout and stderr default
        values
        """
        if v == 'stdin':
            self.option_type = TYPE_INPUT
            return sys.stdin
        if v == 'stdout':
            self.option_type = TYPE_OUTPUT
            return sys.stdout
        if v == 'stderr':
            self.option_type = TYPE_OUTPUT
            return sys.sterr
        return v

    def _get_opt(self):
        """Return the short or long representation of this option"""
        return self.short if self.short else self.long

    def get(self):
        """Get the string representation for the current value
        """
        if self.nargs == 0:
            return ""
        if self.nargs == 1:
            ## current value is a list
            if len(self.value) > 1:
                raise ValueError("Option '%s' contains more "
                                 "than one value!" % self.name)
                return self.__resolve(self.value[0])

            ## single value
            v = None if len(self.value) == 0 else self.value[0]
            if v is None and self.required:
                raise ValueError("Option '%s' is required but not set!")
            return self.__resolve(v) if v else ""
        else:
            return self.join.join([self.__resolve(v) for v in self.value])

    def raw(self):
        """Get raw value(s) not the string representations
        """
        if self.nargs == 0:
            return False if len(self._value) == 0 else bool(self._value[0])
        if self.nargs == 1 and len(self.value) == 1:
            return self.value[0]
        return None if len(self._value) == 0 else self._value

    def __resolve(self, v):
        """Helper to resolve a single value to its string representation
        """
        if isinstance(v, bool) or isinstance(v, file):
            return ""
        return str(v)

    def validate(self):
        """Validate the option and raise a ValueError if the option
        is required but no value is set.
        """
        if self.required:
            if self.nargs != 0 and len(self.value) == 0:
                raise ValueError("Option '%s' is reqired but not set!")

    def _is_list(self):
        """Return true if the current value is a list"""
        return self.nargs != 0 and self.nargs != 1

    def __str__(self):
        """Return the command line representation for this option. An
        excption is raised if the option setting is not valid. Hidden options
        are represented as empty string. Boolean options where the value is
        False or None are represnted as empty string.
        """
        if self.hidden:
            return ""
        if self.nargs == 0:
            if len(self.value) == 0:
                return ""
            return "" if not self.value[0] else self._get_opt()
        value = self.get()
        if not value:
            return ""
        return "%s %s" % (self._get_opt(), value)

    def __eq__(self, other):
        return isinstance(other, Option) and self.name == other.name

    def __hash__(self):
        return self.name.__hash__()


class Options(object):
    """Container instance for a set of options"""

    def __init__(self):
        self.options = []
        self._usage = ""
        self._help = ""

    def usage(self):
        return self._usage

    def help(self):
        return self._help

    def __index(self, name):
        try:
            return self.options.index(Option(name))
        except:
            return -1

    def __getitem__(self, name):
        i = self.__index(name)
        if i >= 0:
            return self.options[i]
        return None

    def __setitem__(self, name, option):
        i = self.__index(name)
        if i >= 0:
            self.options[i] = option
        else:
            self.options.append(option)

    def __len__(self):
        return len(self.options)

    def add(self, option):
        i = self.__index(option.name)
        if i >= 0:
            raise ValueError("Option with the name '%s' already exists",
                             option.name)
        self.options.append(option)

    def validate(self):
        """Validate all options"""
        map(Option.validate, self.options)

    def parse(self, args):
        """Parse the given arguments"""
        from argparse import ArgumentParser

        def to_opts(o):
            opts = []
            if o.short:
                opts.append(o.short)
            if o.long:
                opts.append(o.long)
            if len(opts) == 0:
                opts.append(o.name)
            return opts
        parser = ArgumentParser()
        for o in self.options:
            opts = to_opts(o)
            parser.add_argument(
                *opts,
                dest=o.name,
                nargs=0 if o.nargs == 0 else "*",
                action="store_true" if o.nargs == 0 else None,
                default=o.raw()
            )

        # Override the argparse error function to
        # raise an exception rather than calling a system.exit
        def _custom_error(self, message=None):
            if message is None:
                message = str(self)
            raise Exception(message)
        def _custom_exit(self, status=0, message=None):
            raise Exception(message)

        parser.error = _custom_exit
        namespace = parser.parse_args(args)
        parsed = vars(namespace)
        if "help" in parsed:
            del parsed['help']
        ## apply the values
        for k, v in parsed.iteritems():
            self[k].value = v
        return parsed

    @classmethod
    def from_argparse(cls, parser, inputs=None, outputs=None):
        """Create Options from a given argparse parser
        The inputs and outputs can be set to options names to
        set a specific type
        """
        from StringIO import StringIO

        opts = cls()
        buf = StringIO()
        parser.print_usage(buf)
        opts._usage = buf.getvalue().strip()
        buf.close()

        buf = StringIO()
        parser.print_help(buf)
        opts._help = buf.getvalue().strip()
        buf.close()

        inputs = inputs if inputs else []
        outputs = outputs if outputs else []
        for action in parser._optionals._actions:
            long = None
            short = None
            option_type = TYPE_OPTION
            if action.dest in inputs:
                option_type = TYPE_INPUT
            elif action.dest in outputs:
                option_type = TYPE_OUTPUT

            for s in action.option_strings:
                if s.startswith("--") and long is None:
                    long = s
                elif s.startswith("-") and short is None:
                    short = s
            opts.add(Option(
                action.dest,
                long=long,
                type=action.type,
                option_type=option_type,
                short=short,
                nargs=action.nargs,
                required=action.required,
                description=action.help,
                value=action.default if action.dest != "help" else False,
            ))
        return opts

    @classmethod
    def from_docopt(cls, doc, inputs=None, outputs=None):
        """Create Options from a help string using docopt
        The inputs and outputs can be set to options names to
        set a specific type
        """
        from jip.vendor import docopt
        from jip.vendor.docopt import Required, Optional, Argument, \
            OneOrMore

        inputs = inputs if inputs else []
        outputs = outputs if outputs else []
        opts = cls()

        usage_sections = docopt.parse_section('usage:', doc)
        if len(usage_sections) == 0:
            raise ValueError('"usage:" (case-insensitive) not found.')
        if len(usage_sections) > 1:
            raise ValueError('More than one "usage:" '
                             '(case-insensitive).')
        opts._usage = usage_sections[0]
        opts._help = doc

        def to_name(pattern):
            name = pattern.name
            if name.startswith("<"):
                name = name[1:-1]
            elif name.startswith("--"):
                name = name[2:]
            elif name.startswith("-"):
                name = name[1:]
            return name

        options = docopt.parse_defaults(doc)
        type_inputs = docopt.parse_defaults(doc, "inputs:")
        options += type_inputs
        inputs += map(to_name, type_inputs)
        type_outputs = docopt.parse_defaults(doc, "outputs:")
        options += type_outputs
        outputs += map(to_name, type_outputs)
        pattern = docopt.parse_pattern(docopt.formal_usage(usage_sections[0]),
                                       options)

        inputs = set(inputs)
        outputs = set(outputs)

        ####################################################################
        # recursice pattern parser. We iterate the pattern and collect
        # Options and Arguments recursively
        ####################################################################
        docopt_options = {}
        index = [0]

        def parse_pattern(pattern, required=False, parent=None,
                          one_or_more=False):
            if not hasattr(pattern, "children"):
                pattern.required = required
                if type(pattern) == Argument and parent:
                    docopt_options[parent].argcount = 1 if not one_or_more \
                        else "*"
                else:
                    # create option
                    if one_or_more:
                        pattern.argcount = "*"
                    else:
                        pattern.argcount = 1 if type(pattern) == Argument \
                            else pattern.argcount
                    docopt_options[pattern] = pattern
                    pattern.index = index[0]
                    index[0] = index[0] + 1
            else:
                if required:
                    if type(pattern) == Optional:
                        required = False
                else:
                    required = type(pattern) == Required
                if type(pattern) == OneOrMore:
                    one_or_more = True
                last = parent
                for child in pattern.children:
                    parse_pattern(child, required, last, one_or_more)
                    last = child if not hasattr(child, 'children') else last
        parse_pattern(pattern)

        ####################################################################
        # Convert to Options
        ####################################################################
        for pattern in sorted(docopt_options.keys(), key=lambda x: x.index):
            name = to_name(pattern)
            option_type = TYPE_OPTION
            if name in inputs:
                option_type = TYPE_INPUT
            elif name in outputs:
                option_type = TYPE_OUTPUT

            if type(pattern) == Argument:
                opts.add(Option(
                    name,
                    nargs=pattern.argcount,
                    required=pattern.required,
                    default=pattern.value,
                    option_type=option_type
                ))
            else:
                opts.add(Option(
                    name,
                    short=pattern.short,
                    long=pattern.long,
                    nargs=pattern.argcount,
                    required=pattern.required,
                    default=pattern.value,
                    option_type=option_type
                ))

        return opts