# Client Code

## Client Development Initialization


 Follow the setup guide documentation to initialize the django back-end and create a clientId for the application.

Copy the example.env file to a .env file and set the environment variables for your system.

below are the default values for local development:
```
VUE_APP_API_ROOT=http://localhost:8000/api/v1
VUE_APP_OAUTH_API_ROOT=http://localhost:8000/oauth/
VUE_APP_OAUTH_CLIENT_ID=devClientId
```

After configuring the clientId from the setup and copying over the files run `npm run dev` to initialize the client application on `http://localhost:3000`

