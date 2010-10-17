from operator import attrgetter
import sys

from radarpost.main import COMMANDLINE_PLUGIN, BasicCommand, get_basic_option_parser
from radarpost.main import find_command_type, print_basic_usage, print_unknown_command
from radarpost import plugins

class HelpCommand(BasicCommand):

    command_name = 'help'
    description = 'print help for commands'

    @classmethod
    def setup_options(cls, parser):
        parser.set_usage(r"%prog " + "%s <command> [options]" % cls.command_name)

    def __call__(self, command_name=None):
        if command_name is None: 
            get_basic_option_parser().print_usage()
            print "Commands:"
            for Command in sorted(plugins.get(COMMANDLINE_PLUGIN), key=attrgetter('command_name')):
                print "  %s %s" % (Command.command_name.ljust(20), Command.description)
        else: 
            Command = find_command_type(command_name)
            if Command is None:
                print_unknown_command(command_name)
                return
            else:
                command = Command(self.config)
                command.print_usage()
plugins.register(HelpCommand, COMMANDLINE_PLUGIN)


class ShowConfig(BasicCommand):

    command_name = 'show_config'
    description = 'print configuration'

    @classmethod
    def setup_options(cls, parser):
        parser.set_usage(r"%prog " + "%s [config pattern] [options]" % cls.command_name)

    def __call__(self, key_pattern=None):
        """
        Print the current configuration
        """
        if key_pattern is None:
            for key in sorted(self.config.keys()):
                print "%s = %s" % (key, self.config[key]) 
        else:
            key_pattern = re.compile('^%s$' % key_pattern)
            for key in sorted(self.config.keys()):
                if key_pat.match(key):
                    print "%s = %s" % (key, self.config[key]) 
plugins.register(ShowConfig, COMMANDLINE_PLUGIN)

class Shell(BasicCommand): 
    
    command_name = 'shell'
    description = 'start an interactive shell with the current configuration'
    
    def __call__(self):
        class ShellCommands:
            pass

        cmds = ShellCommands()
        ShellCommands.__doc__ = "Commands:"
        for Command in sorted(plugins.get(COMMANDLINE_PLUGIN), key=attrgetter('command_name')):
            # help is skipped because it relates to the command line option
            # info for the commands.  The built-in python help should be 
            # used in the shell.
            if (not hasattr(Command, '__call__') or 
                Command == HelpCommand or 
                isinstance(self, Command)):
                continue
            
            shell_cmd = Command(self.config).__call__
            shell_cmd.__func__.__name__ = Command.command_name
            setattr(cmds, Command.command_name, shell_cmd)
            ShellCommands.__doc__ += "\n  "
            ShellCommands.__doc__ += Command.command_name.ljust(20)
            ShellCommands.__doc__ += Command.description
        ShellCommands.__doc__ += "\n\nType: help(cmds.<function>) for more info"
        
        locs = {'config': self.config, 'cmds': cmds }
        banner_header = 'RadarPost Interactive Shell\n'
        banner_footer = '\n\nYou may access the current config as "config"'
        banner_footer += '\nCLI commands are available as "cmds.<command>"'
        banner_footer += '\nType: help(cmds) for more info'
        try:
            # try to use IPython if possible
            from IPython.Shell import IPShellEmbed
            shell = IPShellEmbed(argv=sys.argv)
            banner = banner_header + shell.IP.BANNER + banner_footer
            shell.set_banner(banner)
            shell(local_ns=locs, global_ns={})
        except ImportError:
            import code
            pyver = 'Python %s' % sys.version
            banner = banner_header +  pyver + banner_footer

            shell = code.InteractiveConsole(locals=locs)
            try:
                import readline
            except ImportError:
                pass
            try:
                shell.interact(banner)
            finally:
                pass
plugins.register(Shell, COMMANDLINE_PLUGIN)
