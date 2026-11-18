# KohwAI Multi-Provider SMS Framework

## What this patch changes

- Adds a provider router with the default order `smspop,infobip,econet_a2p`.
- Adds a documented SMSPoP REST adapter.
- Adds an Infobip SMS API adapter.
- Adds the Econet A2P provider slot, deliberately disabled until Econet supplies the authenticated production API specification.
- Keeps Africa's Talking as an optional legacy adapter, but does not include it in the default route order.
- Preserves the existing `send_sms()` and `send_sms_detailed()` import interface for alert/community modules.
- Updates OTP handling so a definite provider rejection returns HTTP 502, no configured provider returns HTTP 503, and an ambiguous provider outcome does not trigger a potentially duplicate send. The response adds `delivery_status` (`accepted`, `unknown`, or `development`).

`accepted` means the provider accepted/queued the message. It is not a delivery receipt. SMSPoP and Infobip delivery receipts need a separate webhook integration to confirm handset delivery.

## Install

1. Extract this ZIP into the KohwAI repository root. It creates the folder `kohwai_multi_provider_sms`.
2. Open PowerShell in the repository root.
3. Run:

```powershell
.\kohwai_multi_provider_sms\Apply-KohwaiMultiProviderSms.ps1
```

The installer checks the expected source anchors before writing. It creates timestamped backups beside `backend\app\utils\sms.py` and `backend\app\modules\identity\service.py`. It refuses to overwrite an existing `sms_providers` folder.

It does not modify `.env`, Docker Compose, database schema, data, or volumes.

## Configure providers

Add the following names to the repository-root `.env` file. Leave credentials empty until each provider account has been created. Do not commit real credentials to Git.

```dotenv
# Order is left-to-right. The next provider is used only after a definitive rejection.
SMS_PROVIDER_ORDER=smspop,infobip,econet_a2p

# Layer 1 - SMSPoP: requires API token and an approved sender ID.
SMSPOP_API_TOKEN=
SMSPOP_SENDER_ID=
SMSPOP_CALLBACK_URL=
SMSPOP_CAMPAIGN_NAME=KohwAI transactional message

# Layer 2 - Infobip: Base URL is unique to your Infobip account.
INFOBIP_BASE_URL=
INFOBIP_API_KEY=
INFOBIP_SENDER=

# Layer 3 - Econet Wireless A2P. Keep disabled until Econet gives the API contract.
ECONET_A2P_ENABLED=false
```

The framework reads these values from process environment variables. Confirm that the Docker Compose API service receives them; adding values to the Compose `.env` interpolation file alone does not automatically pass them into a container unless the service uses `env_file` or declares the variables under `environment`.

### SMSPoP requirements

- Create an SMSPoP account.
- Apply for an approved KohwAI sender ID.
- Generate an API token in the SMSPoP dashboard.
- Add the token and sender ID to `.env`.
- SMSPoP's published API supports Econet (077/078/079) and NetOne (071/072); it documents Telecel as unsupported. Its `sent` response means accepted by the network; final delivery is reported later by delivery report/webhook.

### Infobip requirements

- Create an Infobip account and obtain its API key and account-specific Base URL.
- Configure an approved sender for live traffic. During its self-signup free trial, Infobip limits delivery to verified recipients.
- Enter the exact sender value and Base URL supplied by your account dashboard.

### Econet A2P requirements

Econet publicly advertises A2P for OTP and transactional SMS, but the public page and marketplace registration page do not disclose the send endpoint, authentication scheme, body schema, response schema, or delivery webhook contract. The adapter is therefore a registered but disabled slot. Do not invent `ECONET_A2P_API_URL` or credentials, and do not set the adapter live until Econet supplies the API specification and production access.

Request the following from Econet:

- Production and sandbox base URLs and send endpoint.
- Authentication method, token lifecycle and required headers.
- Request schema, destination format, sender ID/shortcode requirements.
- Success, rejection, duplicate and retry semantics.
- Message ID and delivery receipt/webhook contract.
- Throughput/rate limits, pricing, IP allowlisting and support/SLA.
- Whether A2P sends only to Econet subscribers or has any off-net reach.

### Africa's Talking

The legacy adapter is optional and is not in the default order. Add `africastalking` to `SMS_PROVIDER_ORDER` only after its Live application, username and API key are confirmed to be valid. The previously shared API key should be revoked and replaced.

## Routing safety

- A provider acceptance stops routing for that recipient.
- A clear rejection may fail over to the next configured provider.
- A timeout, HTTP 5xx, or unreadable 2xx response is treated as uncertain and stops failover for that recipient, preventing duplicate OTPs.
- Direct Econet routing is restricted to Zimbabwe Econet-assigned number prefixes (077/078/079) as a preliminary route hint. Confirm final network eligibility and number portability behaviour with Econet before activating the direct adapter.
- The OTP itself is generated and hashed by KohwAI once. Providers only transport the message.

## Verification

The package includes provider-router unit tests that mock external HTTP calls; they do not send real SMS or touch a database.

From the repository root, after installing the patch:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'backend')
python -m unittest discover -s .\kohwai_multi_provider_sms\verification -v
```

The tests cover phone normalization, a definitive SMSPoP rejection followed by Infobip acceptance, suppression of failover after a timeout, and the disabled Econet adapter slot.

After adding provider variables to `.env`, inspect whether Compose passes them to the API container. Recreate only the API service after verifying its configuration; do not run `docker compose down -v`.
