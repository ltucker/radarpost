from radarpost.main import COMMANDLINE_PLUGIN, BasicCommand, get_basic_option_parser
from radarpost.main import find_command, print_basic_usage, print_unknown_command
from radarpost import plugins

class HelpCommand(BasicCommand):

    command_name = 'help'
    description = 'print help for commands'

    def setup_options(self, parser):
        parser.set_usage(r"%prog help <command> [options]")

    def __call__(self, config, options, args):
        if len(args) > 2:
            self.print_usage()
        if len(args) == 1:
            get_basic_option_parser().print_usage()
            for command in plugins.get(COMMANDLINE_PLUGIN):
                print "%s - %s" % (command.command_name, command.description)
        if len(args) == 2:
            command_name = args[1]
            command = find_command(command_name)
            if command is None: 
                print_unknown_command(command_name)
                return
            else:
                command.print_usage()
plugins.register(HelpCommand(), COMMANDLINE_PLUGIN)

class ShowConfig(BasicCommand):

    command_name = 'showconfig'
    description = 'print configuration'

    def setup_options(self, parser):
        parser.set_usage(r"%prog showconfig [config pattern] [options]")

    def __call__(self, config, options, args):
        if len(args) > 2:
            self.print_usage()
        if len(args) == 1:
            for key in sorted(config.keys()):
                print "%s = %s" % (key, config[key]) 
        else: 
            key_pat = re.compile('^%s$' % args[1])
            for key in sorted(config.keys()):
                if key_pat.match(key):
                    print "%s = %s" % (key, config[key]) 
plugins.register(ShowConfig(), COMMANDLINE_PLUGIN)
