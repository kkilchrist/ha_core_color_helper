#!/bin/bash

# Sync current directory (excluding sync.sh itself) to remote
rsync -avz --exclude='sync.sh' --exclude='home-assistant.log' ./ root@192.168.2.1:/mnt/userdata/homeassistant-config/custom_components/input_color/

ssh root@192.168.2.1 << 'ENDSSH'
    cp -r /mnt/userdata/homeassistant-config/custom_components/input_color/www/* /mnt/userdata/homeassistant-config/www/
    cd /mnt/userdata/homeassistant-docker/
    docker-compose restart
    sleep 5
ENDSSH

rsync -avz root@192.168.2.1:/mnt/userdata/homeassistant-config/home-assistant.log ./