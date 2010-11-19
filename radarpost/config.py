from ConfigParser import SafeConfigParser
from radarpost import plugins


#
# Config INI parser
#
# This plugin id is used to register configuration validators / manipulators
# that can check and parse the types of configuration values read from 
# the configuration ini file.
# 
# the parser should accept a dict and raise an exception
# if any illegal configuration is found.  The parser is 
# free to manipulate the configuration as needed.
#
# @plugins.plugin(CONFIG_INI_READER_PLUGIN)
# def http_port_conf(config):
#    if 'http.port' in config: 
#       config['http.port'] = int(config['http.port'])
#
CONFIG_INI_PARSER_PLUGIN = 'radarpost.config.configiniparser'

#
# provide defaults that are used to fill in templated values in 
# configuration like %(whatever) etc. 
#
# should be a function that accepts no arguments and returns a 
# dictionary of default values.
#
CONFIG_INI_DEFAULTS_PLUGIN = 'radapost.config.configdefaults'

def load_config(*filenames):
    defaults = {}
    for get_defaults in plugins.get(CONFIG_INI_DEFAULTS_PLUGIN):
        defaults.update(get_defaults())
    
    parser = SafeConfigParser(defaults=defaults)
    
    for filename in filenames:
        conf_file = open(filename, 'r')
        parser.readfp(conf_file)

    config = {}
    for section in parser.sections():
        for key, val in parser.items(section):
            if section == 'main': 
                config[key] = val
            else: 
                config['%s.%s' % (section, key)] = val

    for parser in plugins.get(CONFIG_INI_PARSER_PLUGIN):
        parser(config)

    return config

def parse_bool(b):
    if isinstance(b, bool): 
        return b
    if isinstance(b, int): 
        return b != 0
    elif isinstance(b, basestring): 
        if b.lower() == 'true': 
            return True
        elif b.lower() == 'false': 
            return False        
    raise ValueError('Cannot parse "%s" as a boolean (True or False)' % b)

def config_section(section, config, reprefix=''):
    if not section.endswith('.'):
        section = section + '.'
    section_options = {}
    for k in config.keys():
        if k.startswith(section): 
            section_options[reprefix + k[len(section):]] = config[k]
    return section_options
