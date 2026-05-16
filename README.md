# Infoscreen

Simple server to show slides and images in a browser. Controlled via a webinterface. Even by multiple persons at the same time! 

I wrote this software to enable multiple people to deliver presentations together. It allows each of us to control the slides using our own smartphones. Furthermore, it is an excellent tool for displaying relevant images at conferences whenever a specific topic comes up for discussion. When there is no immediate need for manual control, a slideshow can be displayed in automatic mode.

This is more or less my personal, public backup and documentation of this tool.

Feel free to use it. But...

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. THERE IS NO SUPPORT.

You have been warned.


## Install

Clone this repository to your local machine, notebook or server.

Install dependencies

```console
sudo apt install unclutter python3-full python3-aiohttp python3-websockets git
```

## Config

Create config.ini from the example file. Usually there is no need to change 
anything besides username and password for the control interface.


## Run the thing

Just run:

```console
python3 server.py
```

Open http://localhost:8000/ in your browser.

To control the server, open http://localhost:8000/ctrl/ in your browser. 
Login using the username and password from the config.ini



## Content

Put your content into web/content. Create subfolder for each set of slides.
Folders and images will be sorted and displayed in alphabetical ordner. So
you might want to use some kind of numbering scheme to get them in order.

This repository ships with some examples.

NOTE: Don't put space in the directory or files names.


### Slideshow

There's an option to put a config.txt into each folder. This is especially 
useful for slideshows. There are three options you can put into config.txt:

```console
autorun=true or false
loop=true or false
delay=5
```

They do what their name suggests. You have to select the desired slideshow in
the control interface and start it.


### Creating content from PDFs

Use the following command to convert a PDF file into single images.

```console
pdftoppm -jpeg -r 300 mypdf.pdf outdir/imgprexif
```


## There's more!

### autostart.sh

On standalone machines, there is a helper script that starts the server and
even gitsync (see below). It connects to the local server with firefox in
kiosk mode. You might want to disable all screensaver and powersaving/standby
features on your machine. At least in Ubuntu this is done by the autostart.sh

Edit the autostart.sh.example to your needs and safe it to autostart.sh

```console
chmod 700 autostart.sh
./autostart.sh
```

## Auto-sync content with git

I wrote a little helper script that pulls a host specific config file from a
remote repository and then pulls content from a repository configures in said 
file.

Content can be switched by branches in the repository. This way I'm able to
configure my remote screens via git and they pull the content, switch to the 
correct branch and send a reload to all clients.

Mid-event it is possible to push new content to the screen as well without the 
need to get to the machine.

The gitsync.py will restart itself over and over again.

TODO: 
 * more documentation
 * make it more robust to network outage etc.

Just edit tools/gitsync.ini (create from example-file) to your needs and run:

```console
python3 tools/gitsync.py
```


## Frontend Server on the Internetz

You need to sync the web directory of the server with your infoscreen host.
You can use gitsync for this as well. Or rsync.


### Apache Proxy

On frontend server

```console
apt install apache2
systemctl enable apache2 --now

apt install python3-certbot-apache -y
certbot --apache --agree-tos --redirect --hsts --staple-ocsp --email someone@example.com -d screen.mydomain.com
```

/etc/apache2/sites-available/screen.mydomain.com-https.conf


```apache

<VirtualHost *:443>
  ServerName screen.mydomain.com

  DocumentRoot /var/www/screen.mydomain.com/web/

  # Deny any access to git files      
  RedirectMatch 404 /\.git

  # Forward /ctrl/ for basic auth from backend server
  ProxyPass "/ctrl/" "http://127.0.0.1:8000/ctrl/"  

  # Forward websockets to backend server
  ProxyPass "/ws" "ws://127.0.0.1:8000/ws"
  ProxyPass "/ctrl/ws" "ws://127.0.0.1:8000/ctrl/ws"

  SSLEngine on
  SSLCertificateFile /etc/letsencrypt/live/screen.mydomain.com/fullchain.pem
  SSLCertificateKeyFile /etc/letsencrypt/live/screen.mydomain.com/privkey.pem
</VirtualHost>
```


Then

```console
a2enmod proxy proxy_http proxy_wstunnel
a2ensite screen.mydomain.com-https
systemctl restart apache2
```


### Reverse SSH tunnel

On frontend server

* edit /etc/ssh/sshd_config

```console
PubkeyAuthentication yes
PasswordAuthentication no
ClientAliveInterval 60
ClientAliveCountMax 3
```


On your infoscreen machine

* create ssh host key and upload to the server

```console
ssh-keygen -o
ssh-copy-id user@frontendserver.com
```

The infoscreen uses autossh to create and keep the tunnel.
It is included in autorun.sh as well.

```console
autossh -M 0 -o "ServerAliveInterval=30" -o "ServerAliveCountMax=3" -o "ExitOnForwardFailure=yes" -N -f -R 8000:localhost:8000 -p 22 user@frontendserver.com
```

## TODO

Some ideas I have so far:

* lazy loading images for ctrl
* maybe some kind of caching
* swipe gestures for the ctrl client
