# Updating the Application

To update the application, `git pull` the latest main branch and run:

```bash
# tear down the old services
docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# build new container images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# start the services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# apply any new schema migrations
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm django ./manage.py migrate
```
