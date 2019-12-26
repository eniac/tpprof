#! /bin/bash

rm -f logfile.txt
rm -rf tmp/
mongo --quiet localhost:45555/db --eval 'db.dropDatabase()'

