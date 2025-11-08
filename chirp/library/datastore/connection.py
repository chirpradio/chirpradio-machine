"""Modern connection module for Google Cloud Datastore.

This module replaces the legacy chirp.common.chirpradio connection
that used AppEngine Remote API.
"""

import os
import json
from typing import Optional
from google.cloud import datastore
from google.auth import impersonated_credentials
import google.auth
from chirp.common import conf


def connect(impersonate_service_account: Optional[str] = None) -> datastore.Client:
    """Connect to Google Cloud Datastore using modern client library.

    Args:
        impersonate_service_account: Optional service account email to impersonate.
            If provided, uses your default gcloud credentials to impersonate this
            service account. If None, checks conf.IMPERSONATE_SERVICE_ACCOUNT.
            If that's also None, falls back to direct service account key auth.

    Returns:
        Initialized Datastore client

    Raises:
        FileNotFoundError: If credentials file not found (when not using impersonation)
        ValueError: If credentials file is invalid
        google.auth.exceptions.DefaultCredentialsError: If default credentials not found

    Examples:
        # Use service account impersonation (recommended)
        client = connect(impersonate_service_account="sa@project.iam.gserviceaccount.com")

        # Use direct service account key
        client = connect()
    """
    # Check if we should use service account impersonation
    service_account_to_impersonate = impersonate_service_account
    if service_account_to_impersonate is None:
        service_account_to_impersonate = getattr(conf, 'IMPERSONATE_SERVICE_ACCOUNT', None)

    if service_account_to_impersonate:
        # Use service account impersonation
        return _connect_with_impersonation(service_account_to_impersonate)
    else:
        # Use direct service account key (legacy method)
        return _connect_with_service_account_key()


def _connect_with_impersonation(service_account_email: str) -> datastore.Client:
    """Connect using service account impersonation.

    This uses your default gcloud credentials to impersonate a service account.
    More secure than using service account keys directly.

    Args:
        service_account_email: Email of service account to impersonate

    Returns:
        Initialized Datastore client with impersonated credentials
    """
    # Get default credentials (from gcloud auth login)
    source_credentials, project_id = google.auth.default()

    # If project is not set, try multiple strategies
    if not project_id:
        # Strategy 1: Extract from service account email (e.g., sa@PROJECT.iam.gserviceaccount.com)
        if '@' in service_account_email and '.iam.gserviceaccount.com' in service_account_email:
            project_id = service_account_email.split('@')[1].split('.')[0]

        # Strategy 2: Try to read from service account key file as fallback
        if not project_id and hasattr(conf, 'GOOGLE_APPLICATION_CREDENTIALS'):
            if os.path.exists(conf.GOOGLE_APPLICATION_CREDENTIALS):
                try:
                    with open(conf.GOOGLE_APPLICATION_CREDENTIALS) as fp:
                        credentials_data = json.load(fp)
                        project_id = credentials_data.get('project_id')
                except (FileNotFoundError, json.JSONDecodeError):
                    pass

    if not project_id:
        raise ValueError(
            f"Could not determine project ID. Please either:\n"
            f"1. Set a default project: gcloud config set project PROJECT_ID\n"
            f"2. Ensure service account email is in format: sa@PROJECT.iam.gserviceaccount.com\n"
            f"3. Provide a valid GOOGLE_APPLICATION_CREDENTIALS file"
        )

    # Define the scopes needed for Datastore operations
    target_scopes = ['https://www.googleapis.com/auth/datastore']

    # Create impersonated credentials
    target_credentials = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=service_account_email,
        target_scopes=target_scopes,
        lifetime=3600  # 1 hour
    )

    # Create and return Datastore client with impersonated credentials
    client = datastore.Client(project=project_id, credentials=target_credentials)

    return client


def _connect_with_service_account_key() -> datastore.Client:
    """Connect using service account key file (legacy method).

    Returns:
        Initialized Datastore client

    Raises:
        FileNotFoundError: If credentials file not found
        ValueError: If credentials file is invalid
    """
    # Set credentials environment variable
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = conf.GOOGLE_APPLICATION_CREDENTIALS

    # Read project ID from credentials file
    with open(conf.GOOGLE_APPLICATION_CREDENTIALS) as fp:
        credentials_data = json.load(fp)
        project_id = credentials_data['project_id']

    # Create and return Datastore client
    # The client automatically uses GOOGLE_APPLICATION_CREDENTIALS
    client = datastore.Client(project=project_id)

    return client
