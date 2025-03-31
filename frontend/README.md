# Cashu Round Robin Auditor frontend

This is the frontend for the Cashu Round Robin Auditor written with Quasar and Vue-js.

## Setup and deployment

Before you can start the frontend, copy the `.env.example` file to `.env` and enter your backend's URL there so the frontend knows what to talk to. You can also create a separate file for your production environment with a `.env.production` file, which we use later for building the app for production.

The `.env` file contains:

```
# URL to your backend API server
VUE_BASE_URL=https://api.domain.com
```

### Install the dependencies
```bash
yarn
# or
npm install
```

#### Build the app for production
Make sure you have an `.env.production` file with the necessary values like the backend's URL set.
```bash
quasar build -m spa --dotenv .env.production
```

#### Push changes
You can push the files `dist/spa` to your webserver now.

## Development

#### Start the app in development mode (hot-code reloading, error reporting, etc.)
```bash
quasar dev
```

Note that if you have an `.env` file, it will be used instead of `.env.production` here.

#### Lint the files
```bash
yarn lint
# or
npm run lint
```


#### Format the files
```bash
yarn format
# or
npm run format
```