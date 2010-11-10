from ConfigParser import Error as ConfigError, NoSectionError, NoOptionError
from optparse import OptionParser
from radarpost import plugins
from radarpost.config import load_config
import logging
import os
import re
import sys
import traceback

#
# Command Plugin
#
# This plugin id is used to expose commands available at the 
# command line as 'radarpost <command>' 
#
COMMANDLINE_PLUGIN = 'radarpost.main.command'

class InvalidArguments(Exception):
    pass

class BasicCommand(object):
    """
    Helper base class for Commands.
    
    subclasses should override as needed and
    must implement
    
    command_name = <name used at command line>  
    description = <brief description of command>
    __call__(...): # perform the command
    """
    def __init__(self, config):
        self.config = config
    
    def print_usage(self):
        parser = get_basic_option_parser()
        parser.set_usage(r"%prog " + "%s [options]" % self.command_name)
        self.setup_options(parser)
        print "\n%s: %s" % (self.command_name, self.description)
        parser.print_help()

    @classmethod
    def setup_options(cls, parser):
        """
        may be overridden by subclasses to provide additional 
        command line arguments like --foo etc.
        """
        pass
        
    def clean_options(self, options):
        kw = dict(options.__dict__)
        del kw['config_filenames']
        del kw['log_file']
        return kw
        
    def run(self, args, options):
        kw = self.clean_options(options)
        try:
            self(*args, **kw)
        except TypeError:
            self.print_usage()

def get_basic_option_parser():
    parser = OptionParser(add_help_option=False)
    parser.set_usage(r"%prog " + "<command> [options]")
    parser.add_option('-C', action="append",
                      type="string", dest="config_filenames",
                      help="specify configuration files.  May be specified multipe times for overrides.",
                      default=[])
    parser.add_option('--log', type="string", dest="log_file", default=None, 
                      help="log output to the file specified.")
    return parser

def find_command_type(command_name):
    for Command in plugins.get(COMMANDLINE_PLUGIN):
        if command_name == Command.command_name:
            return Command
    return None

def print_basic_usage(argv):
    print "Usage: %s <command> -C[config.ini] [-Csite.ini] [command_options]" % argv[0]

def print_unknown_command(command_name):
    print 'Unknown command "%s", use "help" for a list of commands.' % command_name 


def main(argv=None):
    import warnings
    warnings.simplefilter("ignore")

    if argv is None: 
        argv = sys.argv

    if len(argv) == 1:
        print_basic_usage(argv)
        sys.exit(1)

    command_name = argv[1]
    argv = argv[0:1] + argv[2:]

    Command = find_command_type(command_name)
    if Command is None: 
        print_basic_usage(argv)
        print_unknown_command(command_name)
        sys.exit(1)

    parser = get_basic_option_parser()
    Command.setup_options(parser)
    options, args = parser.parse_args(argv)

    if len(options.config_filenames) > 0: 
        config_files = options.config_filenames
    elif 'RADAR_CONFIG' in os.environ:
        config_files = os.environ['RADAR_CONFIG'].split(',') 
    else:
        print_basic_usage(argv)
        print "No configuration specified, use -C to specify or set RADAR_CONFIG"
        sys.exit(1)

    try:
        config = load_config(*config_files)
    except IOError as err: 
        print "Unable to read configuration"
        print err
        sys.exit(1)
    except NoOptionError as err: 
        print "Your configuration is missing a required value"
        print err.message
        sys.exit(1)        
    except NoOptionError as err: 
        print "Your configuration is missing a required section"
        print err.message
        sys.exit(1)        
    except ConfigError as err:
        print "An error occurred reading the configuration."
        print err.message
        sys.exit(1)
    
    # setup basic logging
    logger = logging.getLogger()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    if options.log_file is not None: 
        handler = logging.FileHandler(options.log_file, mode="w")
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    command = Command(config)
    try:
        command.run(args[1:], options)
    except InvalidArguments as e: 
        if len(e.args):
            print e.args[0]
        command.print_usage()
        return 1

if __name__ == '__main__':
    main()
