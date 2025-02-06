# Running the docker services

!!! warning
    Be sure to [set up your environment](env-prep.md) before running the services! Otherwise, authentication may not work properly.

The production deployment runs via docker-compose. To start the service,
run the following commands:

```
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# apply any schema upgrades
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm django ./manage.py migrate
```

Once everything has started, the site will be available at <https://url.com/>.

---

If you are deploying for the first time, you can proceed to [Create the Administrator User](create-admin-user.md).
