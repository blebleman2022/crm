#!/bin/bash
cd /Users/blebleman/sync/SynologyDrive/crm
source venv/bin/activate
export FLASK_APP=app.py
export FLASK_ENV=development
python app.py
