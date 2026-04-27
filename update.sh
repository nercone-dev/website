sudo /usr/bin/systemctl disable nercone-website
sudo /usr/bin/systemctl kill nercone-website
/usr/bin/git pull
/root/.local/bin/uv tool uninstall nercone-website || true
/root/.local/bin/uv tool install . --upgrade
sudo /usr/bin/systemctl enable nercone-website
sudo /usr/bin/systemctl start nercone-website
