with open('/repo/scripts/deployer.py') as f: c=f.read()
if 'SECURITY_HEADERS' not in c:
 i=c.find('FRONTEND_DIR = ');e=c.index('\n',i)
 block='''

# Security headers for all responses
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
STATIC_CACHE_MAX_AGE = 86400
BACKEND_HOST = "backend"
BACKEND_PORT = 8000
'''
 c=c[:e+1]+block+c[e+1:]
 open('/repo/scripts/deployer.py','w').write(c)
 print('OK')
else: print('SKIP')
