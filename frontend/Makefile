.PHONY: deploy

deploy:
	quasar build -m spa --dotenv .env.production
	scp -r dist/spa caph:git/cashu-auditor/frontend/dist/spa


