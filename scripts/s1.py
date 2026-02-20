import shutil
shutil.copy2('/repo/scripts/deployer.py', '/repo/scripts/deployer.py.bak')
with open('/repo/scripts/deployer.py') as f: c=f.read()
adds="import socket\nimport select\nimport gzip\nimport hashlib\nfrom datetime import datetime, timezone"
if 'import socket' not in c:
 i=c.rfind('\nimport ');e=c.index('\n',i+1)
 c=c[:e+1]+adds+'\n'+c[e+1:]
 open('/repo/scripts/deployer.py','w').write(c)
 print('OK')
else: print('SKIP')
