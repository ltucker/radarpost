from ConfigParser import Error as ConfigError, NoSectionError, NoOptionError
from optparse import OptionParser
from radarpost import plugins
from radarpost.config import load_config
import logging
import os
import re
import sys

#
# Command Plugin
#
# This plugin id is used to expose commands available at the 
# command line as 'radarpost <command>' 
#
COMMANDLINE_PLUGIN = 'radarpost.main.command'

class BasicCommand(object):
    
    def print_usage(self):
        parser = get_basic_option_parser()
        parser.set_usage(r"%prog " + " %s [options]" % self.command_name)
        self.setup_options(parser)
        print "%s: %s" % (self.command_name, self.description)
        parser.print_help()

    def setup_options(self, parser):
        pass

def get_basic_option_parser():
    parser = OptionParser(add_help_option=False)
    parser.set_usage(r"%prog " + "<command> [options]")
    parser.add_option('-C', action="append",
                      type="string", dest="config_filenames",
                      help="specify configuration files.  May be specified multipe times for overrides.",
                      default=[])
    return parser

def find_command(command_name):
    for command in plugins.get(COMMANDLINE_PLUGIN):
        if command_name == command.command_name:
            return command
    return None

def print_basic_usage(argv):
    print "Usage: %s <command> -C[config.ini] [-Csite.ini] [command_options]" % argv[0]

def print_unknown_command(command_name):
    print 'Unknown command "%s", use "help" for a list of commands.' % command_name 


def main(argv=None):
    if argv is None: 
        argv = sys.argv
    logging.basicConfig(level=logging.INFO)

    if len(argv) == 1:
        print_basic_usage(argv)
        sys.exit(1)

    command_name = argv[1]
    argv = argv[0:1] + argv[2:]

    command = find_command(command_name)
    if command is None: 
        print_basic_usage(argv)
        print_unknown_command(command_name)
        sys.exit(1)

    parser = get_basic_option_parser()
    command.setup_options(parser)
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
        
    command(config, options, args)

if __name__ == '__main__':
    main()