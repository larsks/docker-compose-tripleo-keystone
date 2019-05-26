## Configuration

Put your passwords in `.env`, like this:

```
MYSQL_ROOT_PASSWORD=db-root-secret
KEYSTONE_ADMIN_PASSWORD=keystone-admin-secret
KEYSTONE_DB_PASSWORD=keystone-db-secret
```

## Running it

To start up mysql and keystone:

```
docker-compose up -d
```
