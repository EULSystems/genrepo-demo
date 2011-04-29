from django.conf import settings

from eulcore.fedora.models import DigitalObject

class CollectionObject(DigitalObject):
    """A Fedora CollectionObject.  Inherits the standard Dublin Core
    and RELS-EXT datastreams from
    :class:`~eulcore.fedora.models.DigitalObject`, and adds a content
    model to identify this item as a Collection object.
    """
    COLLECTION_CONTENT_MODEL = 'info:fedora/emory-control:Collection-1.0'
    CONTENT_MODELS = [ COLLECTION_CONTENT_MODEL ]

    # use configured fedora pidspace (if any) when minting pids
    default_pidspace = getattr(settings, 'FEDORA_PIDSPACE', None)
