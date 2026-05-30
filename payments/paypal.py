"""
tiny paypal sandbox gateway, owned by the payments slice.

the react app runs the real paypal JS buttons in the browser. the backend's job
is just to (1) open our own Payment ledger row + hand back an order id for the
button, and (2) record the capture once paypal confirms.

real sandbox calls use these env vars (put them in .env, never commit them):
    PAYPAL_MODE=sandbox
    PAYPAL_CLIENT_ID=...
    PAYPAL_SECRET=...
for offline dev we mint order/capture ids locally so the flow stays testable.
"""

import os
import uuid

PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'sandbox')
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', '')
PAYPAL_SECRET = os.getenv('PAYPAL_SECRET', '')


def new_order_id():
    return 'ORDER-' + uuid.uuid4().hex[:16].upper()


def new_capture_id():
    return 'CAPTURE-' + uuid.uuid4().hex[:16].upper()
