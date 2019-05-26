#!/usr/bin/python

import jinja2
import os
import pymysql
import subprocess
import sys
import time

DEFAULT_KEYSTONE_PUBLIC_URL = 'http://localhost:5000'
DEFAULT_KEYSTONE_INTERNAL_URL = 'http://localhost:5000'
DEFAULT_KEYSTONE_ADMIN_PASSWORD = 'keystone'


def wait_for_database(db_host, db_user, db_pass, db_name):
    while True:
        print('Waiting for database...')
        try:
            connection = pymysql.connect(
                host=db_host,
                user=db_user,
                password=db_pass,
                db=db_name)

            break
        except pymysql.err.OperationalError as err:
            print('Database connection failed: {}'.format(err))
            time.sleep(1)

    print('Database is available.')
    return connection


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

print('templating files')

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


print('initializing keystone db schema')
subprocess.check_call(
    'keystone-manage db_sync'.split())

print('setting up fernet tokens')
subprocess.check_call(
    'keystone-manage fernet_setup '
    '--keystone-user keystone '
    '--keystone-group keystone'.split())

print('bootstrapping keystone')
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

print('running: {}'.format(sys.argv))
os.execvp(sys.argv[1], sys.argv[1:])
