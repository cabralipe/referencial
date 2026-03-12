import urllib.request, urllib.error
import re
try:
    urllib.request.urlopen("http://localhost:8000/api/v1/public/cadastro-data")
except urllib.error.HTTPError as e:
    html = e.read().decode('utf-8')
    match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    if match:
        print("Title:", match.group(1))
    
    match2 = re.search(r'Exception Value:.*?<pre[^>]*>(.*?)</pre>', html, re.IGNORECASE | re.DOTALL)
    if match2:
        print("Error:", match2.group(1))
    else:
        print("Could not parse Error line from Django template")
