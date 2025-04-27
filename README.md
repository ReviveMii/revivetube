# ReviveTube

Watch YouTube on your Wii!

ReviveTube: http://yt.old.errexe.xyz/

ReviveMii Homepage: https://revivemii.errexe.xyz/

# Self Hosting

## Docker (Recommended):
ReviveTube now supports Docker. Docker Installation:

Install docker with `sudo apt install docker.io && sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose`


Then run
```bash
wget https://cloud.theerrorexe.dev/revivetube-docker.tar
docker load -i revivetube-docker.tar
```
Create docker-compose.yml:
```diff
version: "3.9"

services:
  revivetube:
    image: theerrorexe/revivetube:latest
    ports:
      - "5000:5000"
    environment:
      - GOOGLE_API_TOKEN=YOUR_GOOGLE_TOKEN
    volumes:
      - .:/app
    restart: unless-stopped
```
Replace YOUR_GOOGLE_TOKEN with your google api token 
Now run `sudo docker-compose up -d` or `sudo docker compose up -d`

ReviveTube should now run on Port 5000

## Using Python directly

WARNING: before starting the server, remove the --proxy command and the --cookie command in revivetube.py

Go to https://console.cloud.google.com/ and create a new application with the YouTube Data v3 API.

Click on Credentials and click on new, and create a new API Key. Paste the API Key in token.txt

Install the Requirements:
```bash
pip install -r requirements.txt
```
Search for "--proxy" in revivetube.py and remove the command

Search for "--cookies" in revivetube.py and remove the command

Start the Server:
```bash
python3 revivetube.py
```
