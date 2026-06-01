"""
PayPal sandbox gateway (server-side REST), owned by the payments slice.

Mirrors the flow proven in the find_job Laravel project:
  1. OAuth2 client-credentials token (Basic auth with client id + secret)
  2. POST /v2/checkout/orders  -> order id + the buyer `approval_url`
  3. POST /v2/checkout/orders/{id}/capture -> move the money

Mistakes from that project we deliberately avoid here:
  * PayPal's capture endpoint 400s ("Request is not well-formed") unless the
    request carries `Content-Type: application/json` AND a body. We always send
    `{}` so the header + body are present even though capture takes no payload.
  * Credentials missing -> we don't explode mid-checkout; `offline()` kicks in
    and we run a local DEMO flow so CI/tests and credential-less dev still work.
  * A PAYPAL_FAKE_CAPTURE escape hatch for when the sandbox account itself keeps
    returning COMPLIANCE_VIOLATION and there's nothing code can do.

Env (put real values in .env, NEVER commit them):
    PAYPAL_MODE=sandbox|live
    PAYPAL_CLIENT_ID=...
    PAYPAL_CLIENT_SECRET=...
    PAYPAL_CURRENCY=USD
    PAYPAL_FAKE_CAPTURE=0
"""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid

PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'sandbox')
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', '')
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET', '')
PAYPAL_CURRENCY = os.getenv('PAYPAL_CURRENCY', 'USD')
PAYPAL_FAKE_CAPTURE = os.getenv('PAYPAL_FAKE_CAPTURE', '').lower() in ('1', 'true', 'yes')

_BASE = 'https://api-m.paypal.com' if PAYPAL_MODE == 'live' else 'https://api-m.sandbox.paypal.com'


class PayPalError(RuntimeError):
    """Carries PayPal's parsed error body so the view can surface the real issue."""

    def __init__(self, message, body=None):
        super().__init__(message)
        self.body = body or {}


def configured():
    return bool(PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)


def offline():
    """No creds, or the fake-capture hatch -> run the local DEMO flow."""
    return (not configured()) or PAYPAL_FAKE_CAPTURE


def _http(method, path, *, token=None, json_body=None, form_body=None, headers=None):
    url = f'{_BASE}{path}'
    hdrs = dict(headers or {})
    if method == 'GET':
        data = None
    elif form_body is not None:
        data = urllib.parse.urlencode(form_body).encode()
        hdrs['Content-Type'] = 'application/x-www-form-urlencoded'
    else:
        # capture takes no payload but PayPal still needs a JSON body + header
        data = json.dumps(json_body if json_body is not None else {}).encode()
        hdrs['Content-Type'] = 'application/json'
    if token:
        hdrs['Authorization'] = f'Bearer {token}'

    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode() or '{}'
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors='replace')
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = {'raw': raw}
        raise PayPalError(f'PayPal {method} {path} -> HTTP {exc.code}', body=parsed) from exc
    except urllib.error.URLError as exc:
        raise PayPalError(f'PayPal {method} {path} unreachable: {exc.reason}') from exc


def _access_token():
    creds = base64.b64encode(f'{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}'.encode()).decode()
    data = _http(
        'POST',
        '/v1/oauth2/token',
        form_body={'grant_type': 'client_credentials'},
        headers={'Authorization': f'Basic {creds}'},
    )
    return data['access_token']


def create_order(amount, *, currency=None, reference=None, return_url=None, cancel_url=None):
    """Step 1 — returns {id, status, approval_url, demo, raw}."""
    currency = (currency or PAYPAL_CURRENCY).upper()
    if offline():
        return {
            'id': 'DEMO-' + uuid.uuid4().hex[:16].upper(),
            'status': 'CREATED',
            'approval_url': None,
            'demo': True,
            'raw': {},
        }

    token = _access_token()
    unit = {'amount': {'currency_code': currency, 'value': f'{float(amount):.2f}'}}
    if reference:
        unit['reference_id'] = str(reference)
    payload = {'intent': 'CAPTURE', 'purchase_units': [unit]}
    if return_url and cancel_url:
        payload['application_context'] = {
            'return_url': return_url,
            'cancel_url': cancel_url,
            'user_action': 'PAY_NOW',
            'shipping_preference': 'NO_SHIPPING',
        }

    data = _http(
        'POST',
        '/v2/checkout/orders',
        token=token,
        json_body=payload,
        headers={'Prefer': 'return=representation'},
    )
    approve = next(
        (link['href'] for link in data.get('links', []) if link.get('rel') == 'approve'),
        None,
    )
    return {
        'id': data['id'],
        'status': data.get('status'),
        'approval_url': approve,
        'demo': False,
        'raw': data,
    }


def capture_order(order_id):
    """Step 2 — returns {status, capture_id, demo, raw}. Raises PayPalError on HTTP failure."""
    if offline():
        return {
            'status': 'COMPLETED',
            'capture_id': 'DEMOCAP-' + uuid.uuid4().hex[:16].upper(),
            'demo': True,
            'raw': {},
        }

    token = _access_token()
    data = _http(
        'POST',
        f'/v2/checkout/orders/{order_id}/capture',
        token=token,
        json_body={},  # MUST send a body so Content-Type sticks
        headers={'Prefer': 'return=representation', 'PayPal-Request-Id': f'capture-{order_id}'},
    )
    capture_id = None
    try:
        capture_id = data['purchase_units'][0]['payments']['captures'][0]['id']
    except (KeyError, IndexError):
        pass
    return {
        'status': data.get('status'),
        'capture_id': capture_id,
        'demo': False,
        'raw': data,
    }


def get_order(order_id):
    """Inspect an order — used by verify() to re-sync after an interrupted capture."""
    if offline():
        return {'id': order_id, 'status': 'COMPLETED', 'demo': True}
    token = _access_token()
    return _http('GET', f'/v2/checkout/orders/{order_id}', token=token, json_body=None)
