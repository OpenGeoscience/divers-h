# Create the Admin User

This is covered in [the User Management guide](../users.md), but repeated here for consistency. To create the admin user, run the following command:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm django ./manage.py createsuperuser
```


!!! warning
    Do not use upper-case characters when entering your email! If you do, you will not be able to log in.

---

If you are deploying for the first time, you can proceed to [Finalizing Authentication Configuration](post-auth-config.md).
