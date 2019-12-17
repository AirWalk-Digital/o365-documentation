# Documentation and Audit for Azure and Office 365 using the Microsoft Graph API

## Running Locally
in order to run the application remotely, you need to have setup an application within Azure AD.
You will need:
- AZURE_TENANT_ID
- CLIENT_ID (Application ID)
- CLIENT_SECRET (Application Secret)
- REDIRECT_URI (use 'http://localhost:5002/login/authorized' for running locally)

The application is published on Docker Hub under `airwalkconsulting/o365-docs`

Using docker, run the following:

```bash

export CONFIG_PATH= [the location where you want to store your config files (before /msGraph)]

docker run -d \
  -e "AZURE_TENANT_ID=YOUR_TENNANT_ID" \
  -e "CLIENT_SECRET=YOUR_CLIENT_SECRET" \
  -e "CLIENT_ID=YOUR_CLIENT_ID" \
  -e "REDIRECT_URI=http://localhost:5002/login/authorized" \
  -v "$CONFIG_PATH:/app/config" \
  -p 5002:5002 \
airwalkconsulting/o365-docs 

```

## Manual Debugging

```bash
docker run -it --name python -v ~/github/o365-documentation/:/app -p 5002:5002 python bash
cd /app
pip install -r requirements_all.txt
python run_flask.py

```

# Python authentication samples for Microsoft Graph

