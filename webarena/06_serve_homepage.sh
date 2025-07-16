#!/bin/bash

source 00_vars.sh

# activate venv with flask
source .venv/bin/activate

cd webarena-homepage
cp templates/index.backup templates/index.html
sed -i "s|SHOPPING_URL|${SHOPPING_URL}|g" templates/index.html
sed -i "s|SHOPPING_ADMIN_URL|${SHOPPING_ADMIN_URL}|g" templates/index.html
sed -i "s|GITLAB_URL|${GITLAB_URL}|g" templates/index.html
sed -i "s|REDDIT_URL|${REDDIT_URL}|g" templates/index.html
sed -i "s|MAP_URL|${MAP_URL}|g" templates/index.html
sed -i "s|WIKIPEDIA_URL|${WIKIPEDIA_URL}|g" templates/index.html

flask run --host=0.0.0.0 --port=$HOMEPAGE_PORT
