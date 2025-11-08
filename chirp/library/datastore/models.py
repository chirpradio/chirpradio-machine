"""Modern Datastore models for chirpradio.

This module replaces the legacy djdb.models using google-cloud-datastore.
"""

import datetime
from typing import Optional, List, Any, Iterator
from google.cloud import datastore
from google.cloud.datastore.query import Query as DatastoreQuery


# Global datastore client instance
_client: Optional[datastore.Client] = None


def get_client() -> datastore.Client:
    """Get or create the global Datastore client."""
    global _client
    if _client is None:
        # Client automatically uses GOOGLE_APPLICATION_CREDENTIALS env var
        _client = datastore.Client()
    return _client


class Query:
    """Query wrapper that mimics legacy db.Query API."""

    def __init__(self, kind: str, model_class=None):
        self.kind = kind
        self.model_class = model_class
        self._query = get_client().query(kind=kind)
        self._filters = []
        self._orders = []

    def filter(self, filter_str: str, value: Any) -> 'Query':
        """Add a filter to the query.

        Args:
            filter_str: Filter string like "field =" or "__key__ >"
            value: Value to filter by

        Returns:
            Self for chaining
        """
        # Parse filter string (e.g., "album_id =" or "__key__ >")
        parts = filter_str.strip().split()
        if len(parts) == 2:
            field, op = parts
        else:
            # Default to equality
            field = parts[0]
            op = "="

        self._query.add_filter(field, op, value)
        return self

    def order(self, field: str) -> 'Query':
        """Add ordering to the query.

        Args:
            field: Field name to order by (e.g., "__key__")

        Returns:
            Self for chaining
        """
        self._query.order = [field]
        return self

    def _wrap_entity(self, entity: datastore.Entity):
        """Wrap a raw entity in a model instance."""
        if self.model_class:
            # Wrap in model class
            instance = self.model_class.__new__(self.model_class)
            instance._entity = entity
            instance.key = entity.key
            return instance
        else:
            # Return entity wrapper that allows attribute access
            return EntityWrapper(entity)

    def fetch(self, limit: Optional[int] = None) -> List:
        """Fetch query results.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of entities or model instances
        """
        if limit:
            entities = list(self._query.fetch(limit=limit))
        else:
            entities = list(self._query.fetch())

        return [self._wrap_entity(e) for e in entities]

    def __iter__(self) -> Iterator:
        """Iterate over query results."""
        for entity in self._query.fetch():
            yield self._wrap_entity(entity)


class EntityWrapper:
    """Wrapper for raw Datastore entities to allow attribute access."""

    def __init__(self, entity: datastore.Entity):
        self._entity = entity
        self.key = entity.key

    def __getattr__(self, name: str) -> Any:
        """Get property from entity."""
        if name.startswith('_') or name == 'key':
            return object.__getattribute__(self, name)
        return self._entity.get(name)

    def __setattr__(self, name: str, value: Any):
        """Set property on entity."""
        if name.startswith('_') or name == 'key':
            object.__setattr__(self, name, value)
        else:
            self._entity[name] = value


class Model:
    """Base model class that wraps datastore.Entity."""

    KIND: str = None  # Override in subclasses

    def __init__(self, **kwargs):
        """Initialize model with properties.

        Args:
            **kwargs: Entity properties
        """
        client = get_client()

        # Handle parent parameter
        parent = kwargs.pop('parent', None)

        # Create key
        if parent:
            self.key = client.key(self.KIND, parent=parent)
        else:
            self.key = client.key(self.KIND)

        # Create entity
        self._entity = datastore.Entity(key=self.key)

        # Set all properties
        for key, value in kwargs.items():
            self._entity[key] = value

    def __getattr__(self, name: str) -> Any:
        """Get property from underlying entity."""
        if name.startswith('_') or name in ('key', 'KIND'):
            return object.__getattribute__(self, name)
        return self._entity.get(name)

    def __setattr__(self, name: str, value: Any):
        """Set property on underlying entity."""
        if name.startswith('_') or name in ('key', 'KIND'):
            object.__setattr__(self, name, value)
        else:
            if hasattr(self, '_entity'):
                self._entity[name] = value

    def parent_key(self):
        """Get the parent key of this entity."""
        return self.key.parent

    @classmethod
    def all(cls) -> Query:
        """Create a query for all entities of this kind."""
        return Query(cls.KIND, model_class=cls)


class Artist(Model):
    """Artist entity model."""

    KIND = "Artist"

    @classmethod
    def fetch_by_name(cls, name: str) -> Optional['Artist']:
        """Fetch an artist by name.

        Args:
            name: Artist name

        Returns:
            Artist entity or None if not found
        """
        query = get_client().query(kind=cls.KIND)
        query.add_filter("name", "=", name)
        query.add_filter("revoked", "=", False)

        results = list(query.fetch(limit=1))
        if results:
            # Wrap entity in Artist model
            artist = cls.__new__(cls)
            artist._entity = results[0]
            artist.key = results[0].key
            return artist
        return None

    @classmethod
    def fetch_all(cls) -> List['Artist']:
        """Fetch all artists.

        Returns:
            List of all artist entities
        """
        query = get_client().query(kind=cls.KIND)
        results = []
        for entity in query.fetch():
            artist = cls.__new__(cls)
            artist._entity = entity
            artist.key = entity.key
            results.append(artist)
        return results

    @classmethod
    def create(cls, parent=None, name: str = None) -> 'Artist':
        """Create a new artist entity.

        Args:
            parent: Parent key for entity hierarchy
            name: Artist name

        Returns:
            New Artist instance
        """
        artist = cls(parent=parent, name=name, revoked=False)
        return artist


class Album(Model):
    """Album entity model."""

    KIND = "Album"

    def __init__(self, **kwargs):
        """Initialize album with properties."""
        # Set default values
        if 'revoked' not in kwargs:
            kwargs['revoked'] = False
        super().__init__(**kwargs)


class Track(Model):
    """Track entity model."""

    KIND = "Track"

    def __init__(self, **kwargs):
        """Initialize track with properties."""
        super().__init__(**kwargs)


class SearchMatches(Model):
    """Search index matches entity model."""

    KIND = "SearchMatches"

    def __init__(self, **kwargs):
        """Initialize search matches with properties."""
        super().__init__(**kwargs)
