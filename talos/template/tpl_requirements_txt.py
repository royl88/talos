# coding=utf-8

TEMPLATE = u'''# The order of packages is significant, because pip processes them in the order
# of appearance. Changing the order has an impact on the overall integration
# process, which may cause wedges in the gate later.
talos-api
# celery
# dogpile.cache
# redis
# gunicorn
# psycopg2-binary/pymysql
'''
