# Cashu Round Robin Auditor

_An auditor that receives Ecash donations from any Cashu mint so it can be audited perpetually. This app sends random Lightning payments between mints. Forever. The sats go in a circle until all is lost to fees or rugs. If a mint fails to pay an invoice, it is marked with a scary red label._

This project consists of two parts: the auditor backend and its frontend. The frontend files can be found in the `frontend` folder.

## Frontend setup

Read the [README.md](frontend/README.md) in the `frontend` folder of this project to set it up.

## Backend setup

The auditor backend has a [Nutshell](https://github.com/cashubtc/nutshell) Cashu wallet and an API server that publishes audit data.

#### Getting started
Clone this repository and then init all submodules:
```
git submodule update --init --recursive
```

Make sure you have poetry installed. There are many instructions online but you can also check the [Nutshell](https://github.com/cashubtc/nutshell) repository for a quick overview. 

Now install the project:
```
poetry install
```

Run the backend service using:
```
poetry run uvicorn src.main:app
```

#### Nutshell wallet
Copy the `.env.example` file to `.env` or create an `.env` file in the project's root directory for your nutshell wallet configuration. 

##### Using Tor
You're going to want to use Tor for the nutshell wallet so that the auditor can frequently change its IP address. To tell nutshell to use tor, simply put the following into your `.env` file to start the builtin Tor daemon.
```bash
# use builtin tor, this overrides SOCKS_PROXY, HTTP_PROXY
TOR=TRUE
```

If you would like to use your own Tor daemon or another proxy, you can also choose that:

```
# use custom proxy, this will only work with TOR=false
#HTTP_PROXY=http://localhost:8088
#SOCKS_PROXY=socks5://localhost:9050
```

##### Wallet database
The wallet will create a database file called `wallet.sqlite3` that contains its ecash as well as the seed phrase it generated. Make a backup of this file. At least write down the seed phrase contained in the database.

