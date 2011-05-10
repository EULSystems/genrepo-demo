from django.conf import settings
from django.db.models import Model

from eulcore.django.fedora import Repository
from eulcore.fedora.models import DigitalObject

class AccessibleObject(DigitalObject):
    """A place-holder Fedora Object for auto-generating a PublicAccess
    content model which will be used for Fedora XACML access controls.
    """
    PUBLIC_ACCESS_CMODEL = 'info:fedora/emory-control:PublicAccess'
    CONTENT_MODELS = [ PUBLIC_ACCESS_CMODEL ]



class Collection(Model):
    '''Collection place-holder object to define Django permissions on
    :class:`CollectionObject` . 
    '''
    class Meta:
        permissions = (
            # add, change, and delete are created by default
        )


class CollectionObject(DigitalObject):
    """A Fedora CollectionObject.  Inherits the standard Dublin Core
    and RELS-EXT datastreams from
    :class:`~eulcore.fedora.models.DigitalObject`, and adds a content
    model to identify this item as a Collection object.
    """
    COLLECTION_CONTENT_MODEL = 'info:fedora/emory-control:Collection-1.0'
    CONTENT_MODELS = [ COLLECTION_CONTENT_MODEL, AccessibleObject.PUBLIC_ACCESS_CMODEL ]

    # use configured fedora pidspace (if any) when minting pids
    default_pidspace = getattr(settings, 'FEDORA_PIDSPACE', None)

    @staticmethod
    def all():
        """
        Returns all collections in the repository as
        :class:`~genrepo.collection.models.CollectionObject`
        """
        repo = Repository()
        colls = repo.get_objects_with_cmodel(CollectionObject.COLLECTION_CONTENT_MODEL, type=CollectionObject)
        return colls

