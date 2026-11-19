#!/usr/bin/env bash
set -euo pipefail
# Run on EC2 instance; no public endpoints or AWS API calls.
python3 - <<'PYCODE'
import urllib.request, urllib.error
base='http://127.0.0.1:18080'
with urllib.request.urlopen(base+'/health/live', timeout=5) as response:
    assert response.status == 200
for uri in ('/health/ready','/v1/business/questions'):
    try:
        urllib.request.urlopen(base+uri,timeout=5)
        raise AssertionError(uri+' unexpectedly available')
    except urllib.error.HTTPError as ex:
        assert ex.code == 503, (uri,ex.code)
print('PASS: loopback liveness; readiness and business requests blocked')
PYCODE
