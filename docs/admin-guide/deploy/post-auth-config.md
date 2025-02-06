# Finalizing Authentication Config

!!! info
    You must have [created the admin user](create-admin-user.md) before you can finalize the authentication configuration.

This is the last step you will need to take to finalize the authentication configuration. This enables the OAuth link between the web application and the server.

You will need several pieces of information to run the command below.

- `$ADMIN_USER_EMAIL`: the superuser/admin's email you created in [the previous step](create-admin-user.md).
- `$WEBSITE_URL`: the website URL of the deployment in `https://YOURDOMAIN/` format.
  **IMPORTANT**: the format must match *exactly*. This includes the suffix slash. That is, if `YOURDOMAIN` is `url.com`, then `WEBSITE_URL` should be `https://url.com/`.

Run the following command to create the OAuth client for the web application, substituting `$ADMIN_USER_EMAIL` and `$WEBSITE_URL` appropriately.

```
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm django ./manage.py makeclient --user $ADMIN_USER_EMAIL --uri $WEBSITE_URL
```

---

If you are deploying for the first time, you can proceed to [Name Your Site](site-name.md).
