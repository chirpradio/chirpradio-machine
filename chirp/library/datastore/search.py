"""Modern Datastore search and indexing functionality.

This module replaces the legacy djdb.search using google-cloud-datastore.
"""

from typing import List, Optional
from google.cloud import datastore
from google.api_core import retry
from .models import get_client


class Indexer:
    """Batch indexer for adding entities to Datastore.

    Accumulates entities and writes them in batches using put_multi().
    """

    def __init__(self):
        """Initialize the indexer with a new transaction key."""
        self._client = get_client()
        # Create a parent entity for this batch (transaction group)
        # Allocate an ID to make the key complete (required for parent keys)
        incomplete_key = self._client.key("IndexerTransaction")
        self._transaction_key = self._client.allocate_ids(incomplete_key, 1)[0]
        self._entities = []

    @property
    def transaction(self):
        """Get the transaction key for this batch.

        This is used as the parent for all entities in this batch.
        """
        return self._transaction_key

    @property
    def _transaction(self):
        """Alternate property name for compatibility."""
        return self._transaction_key

    @_transaction.setter
    def _transaction(self, value):
        """Set the transaction key."""
        self._transaction_key = value

    def add_album(self, album):
        """Add an album entity to the batch.

        Args:
            album: Album model instance or entity
        """
        if hasattr(album, '_entity'):
            # Model instance
            self._entities.append(album._entity)
        else:
            # Raw entity
            self._entities.append(album)

    def add_track(self, track):
        """Add a track entity to the batch.

        Args:
            track: Track model instance or entity
        """
        if hasattr(track, '_entity'):
            # Model instance
            self._entities.append(track._entity)
        else:
            # Raw entity
            self._entities.append(track)

    def add_artist(self, artist):
        """Add an artist entity to the batch.

        Args:
            artist: Artist model instance or entity
        """
        if hasattr(artist, '_entity'):
            # Model instance
            self._entities.append(artist._entity)
        else:
            # Raw entity
            self._entities.append(artist)

    @retry.Retry(predicate=retry.if_exception_type(
        Exception  # Retry on any exception
    ))
    def save(self, rpc=None, timeout: int = 120):
        """Save all accumulated entities to Datastore.

        Args:
            rpc: Legacy parameter for compatibility (ignored)
            timeout: Timeout in seconds for the operation

        Raises:
            google.api_core.exceptions.GoogleAPIError: On save failure
        """
        if not self._entities:
            return

        # Use put_multi for batch write
        # The timeout parameter sets the deadline for the operation
        self._client.put_multi(self._entities, timeout=timeout)

        # Clear the batch after successful save
        self._entities = []


def optimize_index(term: str) -> int:
    """Optimize the search index for a given term.

    This is a placeholder implementation. The actual search index optimization
    would depend on the search infrastructure being used.

    Args:
        term: Search term to optimize

    Returns:
        Number of index entries deleted/optimized
    """
    client = get_client()

    # Query for SearchMatches with this term
    query = client.query(kind="SearchMatches")
    query.add_filter("term", "=", term)

    # Fetch all matches
    entities = list(query.fetch())

    # In a real implementation, you would:
    # 1. Deduplicate matches
    # 2. Remove stale entries
    # 3. Consolidate fragmented index entries
    # For now, we just return the count
    return len(entities)
