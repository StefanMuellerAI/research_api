#!/bin/bash

# Aktiviere die virtuelle Umgebung, falls vorhanden
if [ -d "../openai-agents-python/env" ]; then
    source ../openai-agents-python/env/bin/activate
fi

# Starte die API
python api.py 