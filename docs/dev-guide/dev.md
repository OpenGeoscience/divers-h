# Development Setup

To begin development, check out the repo via `git clone git@github.com:NZ-ARMADA/nz_armada_webgis.git`.

## Initial Dev Setup
1. To prepare the web client, install its requirements with `cd client && npm install`.
2. Run the docker containers with `docker compose up`. Be sure to check that all containers were able to start and stay running successfully before continuing.
3. While the containers are up, run the following commands in a separate terminal to prepare the database:
    1. Run `docker compose run --rm django ./manage.py migrate`.
    2. Run `docker compose run --rm django ./manage.py createsuperuser`
       and follow the prompts to create your own user.
    3. Run `docker compose run --rm django ./manage.py makeclient --username {your.username@email.com}` to create the client application id for user logins.
    4. Run `docker compose run --rm django ./manage.py ingest_data ./sample_data/test.json` to use sample data.
    5. Copy the `./client/env.example` environment file to `./client/.env`.  The default environment variables should be sufficient for local development.

## Run Application
1. Run `docker compose up`. You can access the admin page at port **8000**: <http://localhost:8000/admin/>
3. In the `client` directory run `npm run dev`. The user interface is on port **3000**: <http://localhost:3000/>
5. When finished, use `Ctrl+C` to stop the docker-compose and npm commands, respectively.

## Updating the Application
Occasionally, new package dependencies or schema changes will require rebuilding the docker images. To non-destructively update your development stack at any time:

1. Run `docker compose pull`
2. Run `docker compose build --pull --no-cache`
3. Run `docker compose run --rm django ./manage.py migrate`
