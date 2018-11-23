# coding=utf-8

TEMPLATE = u'''{
    "public_endpoint": "http://www.${pkg_name}.cn/",
    "locale_app": "${pkg_name}",
    "locale_path": "./etc/locale",
    "language": "en",
    "server": {
        "bind": "0.0.0.0",
        "port": 9000
    },
    "log": {
    	"gunicorn_access": "./access.log",
    	"gunicorn_error": "./error.log",
        "path": "./server.log",
        "level": "INFO",
        "format_string": "%(asctime)s.%(msecs)03d %(process)d %(levelname)s %(name)s:%(lineno)d [-] %(message)s",
        "date_format_string": "%Y-%m-%d %H:%M:%S"
    },
    "db": {
        "connection": "${db_connection}",
        "pool_size": 3,
        "pool_recycle": 3600,
        "pool_timeout": 5,
        "max_overflow": 5
    },
    "application": {
        "names": []
    },
    "rate_limit": {
        "enabled": true,
        "storage_url": "memory://",
        "strategy": "fixed-window",
        "global_limits": null
    }
}
'''