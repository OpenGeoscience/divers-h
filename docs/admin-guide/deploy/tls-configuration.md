# Setting up TLS configuration

If you haven't done so already, here are the instructions to set up the TLS configuration prior to starting the application.

Two files are needed for TLS configuration: a certificate file and a private key
file.  How these are obtained depends on how the certificate files are delivered
by the certificate authority (the CA).

For example, a typical .zip file from the CA should contain 3 files:

- YourCertificate.crt
- CertAuthorityBundle.crt
- YourPrivate.key

These files should ideally be installed to `/etc/ssl/certs`, but this location can be overridden by setting the `LOCAL_SSL_CERT_DIR` environment variable. To install these files, run the following commands:

```
export LOCAL_SSL_CERT_DIR=/etc/ssl/certs

# combine the certificate files, with your certificate first
cat YourCertificate.crt CertAuthorityBundle.crt | sudo tee $LOCAL_SSL_CERT_DIR/yourcert.crt

sudo mv YourPrivate.key $LOCAL_SSL_CERT_DIR/yourcert.key
```

---

If you are deploying for the first time, you can proceed to [Environment Preparation](env-prep.md).

