# Generating Vector Tiles

Normally, the tiles will be auto-generated in the background when you start the application. However, that might not be desired, e.g. you want to generate the tiles on a more powerful machine rather than your server.

To manually generate the vector tiles, run the following command.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm gen-vector-basemap
```

This is a very long task with soft-minimum system requirements:

- At least 40GB disk space
- At least 8GB available RAM

The UI will pick up the presence of the vector tiles once the tiles have been generated.

If the deployment is restarted at any time, the tile-generation job will make a best-effort case to resume generation from where it left off.

If vector tiles are not manually generated beforehand, then the production docker-compose deployment will kickstart a job to generate the vector tiles for the entire USA.
