#!/usr/bin/env python3
import base64, sys
data = open('/repo/scripts/deployer.py.b64').read().strip()
with open('/repo/scripts/deployer.py', 'w') as f:
    f.write(base64.b64decode(data).decode())
print('Deployer updated')
