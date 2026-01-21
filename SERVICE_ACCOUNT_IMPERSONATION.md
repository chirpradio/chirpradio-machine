# Service Account Impersonation Guide

This guide explains how to use **service account impersonation** instead of service account keys for Google Cloud Datastore operations. This is the **recommended and more secure** approach.

## Why Use Service Account Impersonation?

### ✅ Benefits

1. **More Secure** - No service account key files to manage or accidentally leak
2. **Better Auditing** - Actions are logged under your user account, not a shared service account
3. **MFA Support** - Can use multi-factor authentication with your user credentials
4. **Easier Key Rotation** - No need to rotate service account keys
5. **Principle of Least Privilege** - Users only get permissions when they need them

### ❌ Drawbacks of Service Account Keys

- Keys are long-lived credentials that can be stolen
- Keys are often committed to git repositories by accident
- Hard to track who is using which key
- No way to enforce MFA when using keys

---

## Setup Instructions

### Step 1: Authenticate with gcloud

First, log in with your Google Cloud credentials:

```bash
gcloud auth application-default login
```

This will open a browser and prompt you to log in with your Google account.

### Step 2: Create or Identify the Service Account

You need a service account that has the necessary Datastore permissions. Either create a new one or use an existing one:

**Create new service account:**
```bash
PROJECT_ID="your-project-id"
SA_NAME="chirpradio-datastore"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Create service account
gcloud iam service-accounts create ${SA_NAME} \
    --display-name="Chirpradio Datastore Access" \
    --project=${PROJECT_ID}

# Grant Datastore permissions to the service account
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/datastore.user"
```

**Or use existing service account:**
```bash
# List existing service accounts
gcloud iam service-accounts list --project=your-project-id
```

### Step 3: Grant Impersonation Permissions to Your User

Grant yourself (or other users) permission to impersonate the service account:

```bash
PROJECT_ID="your-project-id"
SA_EMAIL="chirpradio-datastore@${PROJECT_ID}.iam.gserviceaccount.com"
USER_EMAIL="your-email@example.com"

gcloud iam service-accounts add-iam-policy-binding ${SA_EMAIL} \
    --member="user:${USER_EMAIL}" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --project=${PROJECT_ID}
```

**For a Google Group:**
```bash
gcloud iam service-accounts add-iam-policy-binding ${SA_EMAIL} \
    --member="group:your-team@example.com" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --project=${PROJECT_ID}
```

### Step 4: Configure chirpradio-machine

Update your `settings_local.py` (or `settings.py`):

```python
# Service Account Impersonation (Recommended)
IMPERSONATE_SERVICE_ACCOUNT = 'chirpradio-datastore@your-project-id.iam.gserviceaccount.com'
```

---

## Usage

### Option 1: Configure in settings_local.py (Recommended)

Edit your `settings_local.py`:

```python
import os.path as op

# ... other settings ...

# Enable service account impersonation
IMPERSONATE_SERVICE_ACCOUNT = 'chirpradio-datastore@your-project-id.iam.gserviceaccount.com'
```

Then run scripts normally:

```bash
source .venv/bin/activate
python -m chirp.library.chirpradio_scripts.do_index_census
python -m chirp.library.do_push_artists_to_chirpradio
python -m chirp.library.do_push_to_chirpradio
```

### Option 2: Pass Service Account to connect()

You can also pass the service account email directly in code:

```python
from chirp.library.datastore import connection

# Connect with impersonation
client = connection.connect(
    impersonate_service_account='chirpradio-datastore@project.iam.gserviceaccount.com'
)
```

### Option 3: Use Environment Variable

Set an environment variable before running:

```bash
export IMPERSONATE_SERVICE_ACCOUNT='chirpradio-datastore@project.iam.gserviceaccount.com'
python -m chirp.library.do_push_to_chirpradio
```

Then update `settings_local.py`:

```python
import os
IMPERSONATE_SERVICE_ACCOUNT = os.getenv('IMPERSONATE_SERVICE_ACCOUNT')
```

---

## Required IAM Permissions

### Permissions on the Service Account

The service account needs permissions to access Datastore:

```bash
# Grant Datastore User role (read/write)
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:SA_EMAIL" \
    --role="roles/datastore.user"
```

### Permissions for Your User Account

Your user account needs permission to impersonate the service account:

**Required Role:**
- `roles/iam.serviceAccountTokenCreator` on the service account

**Grant it:**
```bash
gcloud iam service-accounts add-iam-policy-binding SA_EMAIL \
    --member="user:YOUR_EMAIL" \
    --role="roles/iam.serviceAccountTokenCreator"
```

---

## Verification

### Check Your Default Credentials

```bash
gcloud auth application-default login
gcloud auth application-default print-access-token
```

### Test Impersonation

```bash
# Test that you can generate tokens for the service account
gcloud auth print-access-token --impersonate-service-account=SA_EMAIL
```

### Test Datastore Access

```python
# Test script
from chirp.library.datastore import connection

client = connection.connect(
    impersonate_service_account='your-sa@project.iam.gserviceaccount.com'
)
print("Connection successful!")
print(f"Project: {client.project}")
```

---

## Troubleshooting

### Error: `DefaultCredentialsError`

```
google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials.
```

**Solution:**
```bash
gcloud auth application-default login
```

### Error: `Permission Denied` when impersonating

```
google.auth.exceptions.RefreshError: ('Unable to acquire impersonated credentials', ...)
```

**Solution:** Grant yourself the `serviceAccountTokenCreator` role:
```bash
gcloud iam service-accounts add-iam-policy-binding SA_EMAIL \
    --member="user:YOUR_EMAIL" \
    --role="roles/iam.serviceAccountTokenCreator"
```

### Error: `Permission Denied` when accessing Datastore

```
google.api_core.exceptions.PermissionDenied: 403 Missing or insufficient permissions.
```

**Solution:** Grant the service account Datastore permissions:
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:SA_EMAIL" \
    --role="roles/datastore.user"
```

### Check Your Permissions

**See if you can impersonate:**
```bash
gcloud iam service-accounts describe SA_EMAIL --format=json
gcloud iam service-accounts get-iam-policy SA_EMAIL
```

**See service account's Datastore permissions:**
```bash
gcloud projects get-iam-policy PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:SA_EMAIL"
```

---

## Switching Back to Service Account Keys

If you need to switch back to using service account keys (not recommended):

**In settings_local.py:**
```python
# Disable impersonation
IMPERSONATE_SERVICE_ACCOUNT = None

# Make sure this points to your key file
GOOGLE_APPLICATION_CREDENTIALS = op.expanduser('~/chirpradio-data/chirpradio_service_account_key.json')
```

---

## Security Best Practices

1. **Use Impersonation in Production** - Never use service account keys if you can avoid it
2. **Limit Impersonation Permissions** - Only grant `serviceAccountTokenCreator` to users who need it
3. **Use Groups** - Grant permissions to Google Groups, not individual users
4. **Audit Regularly** - Review who has impersonation permissions
5. **Short-Lived Tokens** - The code uses 1-hour token lifetime (configurable in `connection.py`)
6. **Monitor Usage** - Check Cloud Audit Logs for impersonation activity

---

## How It Works

1. **Your user logs in** via `gcloud auth application-default login`
2. **Code gets your credentials** via `google.auth.default()`
3. **Code requests impersonated token** using your credentials + service account email
4. **Google verifies** you have `iam.serviceAccountTokenCreator` permission
5. **Google issues short-lived token** (1 hour) for the service account
6. **Code uses token** to access Datastore with service account's permissions
7. **Token expires** after 1 hour (automatically refreshed by google-auth)

This means:
- ✅ All Datastore operations appear as the service account (consistent logging)
- ✅ All impersonation requests are logged under your user account (audit trail)
- ✅ You only need your user credentials (no key files)
- ✅ Tokens are short-lived and auto-refreshed

---

## Example: Full Setup

```bash
# 1. Set variables
PROJECT_ID="chirpradio-dev"
SA_NAME="chirpradio-datastore"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
YOUR_EMAIL="yourname@gmail.com"

# 2. Create service account
gcloud iam service-accounts create ${SA_NAME} \
    --display-name="Chirpradio Datastore Access" \
    --project=${PROJECT_ID}

# 3. Grant Datastore permissions to service account
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/datastore.user"

# 4. Grant yourself impersonation permissions
gcloud iam service-accounts add-iam-policy-binding ${SA_EMAIL} \
    --member="user:${YOUR_EMAIL}" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --project=${PROJECT_ID}

# 5. Authenticate with your user account
gcloud auth application-default login

# 6. Test impersonation
gcloud auth print-access-token --impersonate-service-account=${SA_EMAIL}

# 7. Update settings_local.py
echo "IMPERSONATE_SERVICE_ACCOUNT = '${SA_EMAIL}'" >> settings_local.py

# 8. Test the connection
python -c "from chirp.library.datastore import connection; print(connection.connect())"
```

---

## Summary

**Recommended Setup:**
1. Authenticate: `gcloud auth application-default login`
2. Set `IMPERSONATE_SERVICE_ACCOUNT` in `settings_local.py`
3. Grant yourself `roles/iam.serviceAccountTokenCreator` on the service account
4. Grant service account `roles/datastore.user` on the project
5. Run scripts normally - impersonation happens automatically!

This is more secure and easier to manage than service account keys.
