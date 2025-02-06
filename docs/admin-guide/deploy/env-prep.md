# Environment Preparation

## SSL Certificates

This was covered in [setting up the TLS configuration](tls-configuration.md), but it bears repeating here.

You will need to export the `LOCAL_SSL_CERT_DIR` variable to wherever you installed the SSL certificates from the previous step.

```
export LOCAL_SSL_CERT_DIR=/etc/ssl/certs
```

## Other Environment Variables


The file `prod/.env.docker-compose` lists several configurable environment variables that need to be properly set in order for the deployed site to work. The relevant variables are given below.

```
# The list of allowed hosts. Add your domain here.
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,url.com

# The list of CORS-whitelisted origins. Add your domain here in https://YOURDOMAIN format.
DJANGO_CORS_ORIGIN_WHITELIST=http://url.com,https://url.com

# The list of CSRF-trusted origins. Add your domain here in https://YOURDOMAIN format.
DJANGO_CSRF_TRUSTED_ORIGINS=https://url.com
```

---

If you are deploying for the first time, you can proceed to [Running the Docker Services](docker-services.md).
