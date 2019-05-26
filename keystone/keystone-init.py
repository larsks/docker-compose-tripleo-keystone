#!/usr/bin/python

import jinja2
import logging
import os
import pymysql
import subprocess
import sys
import time

DEFAULT_KEYSTONE_PUBLIC_URL = 'http://localhost:5000'
DEFAULT_KEYSTONE_INTERNAL_URL = 'http://localhost:5000'
DEFAULT_KEYSTONE_ADMIN_PASSWORD = 'keystone'

LOG = logging.getLogger(__name__)


def wait_for_database(db_host, db_user, db_pass, db_name):
    while True:
        LOG.info('waiting for database...')
        try:
            connection = pymysql.connect(
                host=db_host,
                user=db_user,
                password=db_pass,
                db=db_name)

            break
        except pymysql.err.OperationalError as err:
            LOG.warning('database connection failed: %s', format(err))
            time.sleep(1)

    LOG.info('database is available.')
    return connection


######################################################################

logging.basicConfig(level=os.environ.get('KEYSTONE_INIT_LOGLEVEL', 'INFO'))

db_host = os.environ.get('KEYSTONE_DB_HOST', 'database')
db_user_keystone = os.environ.get('KEYSTONE_DB_USER', 'keystone')
db_pass_keystone = os.environ.get('KEYSTONE_DB_PASSWORD', 'keystone')
db_name_keystone = os.environ.get('KEYSTONE_DB_NAME', 'keystone')

db_user_root = os.environ.get('MYSQL_ROOT_USER', 'root')
db_pass_root = os.environ.get('MYSQL_ROOT_PASSWORD', 'password')
db_name_root = 'mysql'

connection = wait_for_database(db_host, db_user_root, db_pass_root,
                               db_name_root)

with connection.cursor() as cursor:
    cursor.execute('CREATE DATABASE IF NOT EXISTS {db_name}'.format(
        db_name=db_name_keystone))
    cursor.execute("GRANT ALL PRIVILEGES ON {db_name}.* "
                   "TO '{db_user}'@'localhost' "
                   "IDENTIFIED BY '{db_pass}'".format(
                       db_name=db_name_keystone,
                       db_user=db_user_keystone,
                       db_pass=db_pass_keystone))
    cursor.execute("GRANT ALL PRIVILEGES ON {db_name}.* "
                   "TO '{db_user}'@'%' "
                   "IDENTIFIED BY '{db_pass}'".format(
                       db_name=db_name_keystone,
                       db_user=db_user_keystone,
                       db_pass=db_pass_keystone))
connection.close()

LOG.info('generating keystone.conf')
with open('/etc/keystone/keystone.j2.conf') as fd:
    t = jinja2.Template(fd.read())

with open('/etc/keystone/keystone.conf', 'w') as fd:
    fd.write(t.render(
        environ=os.environ,
        keystone_db_host=db_host,
        keystone_db_user=db_user_keystone,
        keystone_db_pass=db_pass_keystone,
        keystone_db_name=db_name_keystone,
    ))


LOG.info('initializing keystone db schema')
subprocess.check_call(
    'keystone-manage db_sync'.split())

LOG.info('setting up fernet tokens')
subprocess.check_call(
    'keystone-manage fernet_setup '
    '--keystone-user keystone '
    '--keystone-group keystone'.split())

LOG.info('bootstrapping keystone')
subprocess.check_call(
    'keystone-manage bootstrap '
    '--bootstrap-password {KEYSTONE_ADMIN_PASSWORD} '
    '--bootstrap-username admin '
    '--bootstrap-project-name admin '
    '--bootstrap-role-name admin '
    '--bootstrap-service-name keystone '
    '--bootstrap-region-id RegionOne '
    '--bootstrap-public-url {KEYSTONE_PUBLIC_URL} '
    '--bootstrap-internal-url {KEYSTONE_INTERNAL_URL}'.format(
        KEYSTONE_ADMIN_PASSWORD=os.environ.get(
            'KEYSTONE_ADMIN_PASSWORD', DEFAULT_KEYSTONE_ADMIN_PASSWORD),
        KEYSTONE_PUBLIC_URL=os.environ.get(
            'KEYSTONE_PUBLIC_URL', DEFAULT_KEYSTONE_PUBLIC_URL),
        KEYSTONE_INTERNAL_URL=os.environ.get(
            'KEYSTONE_INTERNAL_URL', DEFAULT_KEYSTONE_INTERNAL_URL),
    ).split())

LOG.info('running: %s', sys.argv[1:])
os.execvp(sys.argv[1], sys.argv[1:])
