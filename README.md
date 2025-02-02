# ReviveTube

Watch YouTube on your Wii!

ReviveTube: http://yt.old.errexe.xyz/

ReviveMii Homepage: https://revivemii.errexe.xyz/

# Self Hosting

WARNING: before starting the server, remove the --proxy command in revivetube.py

Go to https://console.cloud.google.com/ and create a new application with the YouTube Data v3 API.

Click on Credentials and click on new, and create a new API Key. Paste the API Key in token.txt

Install the Requirements:
```bash
pip install -r requirements.txt
```
Search for "--proxy" in revivetube.py and remove the command

Start the Server:
```bash
python3 revivetube.py
```