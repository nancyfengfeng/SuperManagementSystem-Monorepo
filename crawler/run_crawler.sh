#!/bin/bash

PROJECT_ROOT="/www/wwwroot/SuperManagementSystem"

cd "$PROJECT_ROOT" || exit 1

export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/admin"

/www/wwwroot/SuperManagementSystem/admin/venv/bin/python -m crawler.run