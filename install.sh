#! /bin/bash

sudo apt update
sudo apt install -y python3-pip python3-matplotlib
pip3 install --user networkx
pip3 install --user pandas
sudo apt install -y python3-pygraphviz
pip3 install --user sklearn
pip3 install --user hyperopt
sudo apt install -y mongodb
pip3 install --user pymongo

mkdir db
mongod --dbpath db/ --bind_ip 127.0.0.1 --port 45555 --fork --syslog

