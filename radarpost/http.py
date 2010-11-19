from httplib2 import Http as UnrestrictedHttp
from tinfoilhat import Http as RestrictedHttp
from radarpost.config import CONFIG_INI_PARSER_PLUGIN, parse_bool, config_section
from radarpost import plugins

def create_client(cfg):
    """
    create an http client according to 
    the configuration given.
    """

    cfg = config_section('http', cfg)
    
    kw = {}
    if 'timeout' in cfg: 
        kw['timeout'] = cfg['timeout']    
    if 'cache' in cfg:
        kw['cache'] = cfg['cache']
    
    if cfg.get('allow_local') == True: 
        client = UnrestrictedHttp(**kw)
    else:
        client = RestrictedHttp(**kw)

    client.force_exception_to_status_code = True
    
    return client
    
def close_all(client):
    """
    Force-close all connections on an 
    Http object.  Set the Connection: close 
    header to force most to close automatically 
    for well behaved servers.  This cleans up
    after servers that do not behave.  
    
    See:
    http://groups.google.com/group/httplib2-dev/browse_thread/thread/55cafd03850d895?pli=1
    http://code.google.com/p/httplib2/issues/detail?id=41    
    """
    for conn in client.connections.values():
        conn.close()
    client.connections = {}

@plugins.plugin(CONFIG_INI_PARSER_PLUGIN)
def parse_http_config(cfg):
    if 'http.allow_local' in cfg: 
        cfg['http.allow_local'] = parse_bool(cfg['http.allow_local'])
    if 'http.timeout' in cfg:
        try:
            cfg['http.timeout'] = int(cfg['http.timeout'])
        except: 
            pass