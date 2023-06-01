#!/bin/bash

# Check the code for linting errors
isort acmi_bot.py
flake8 acmi_bot.py
pylint acmi_bot.py
