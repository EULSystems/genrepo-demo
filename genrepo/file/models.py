from django.conf import settings
from django.db.models import Model
from eulcore.fedora import DigitalObject
from eulcore.fedora.models import FileDatastream
from genrepo.collection.models import AccessibleObject


class File(Model):
    '''File place-holder object to define Django permissions on
    :class:`FileObject` . 
    '''
    class Meta:
        permissions = (
            # add, change, and delete are created by default
        )


class FileObject(DigitalObject):
    '''An opaque file for repositing on behalf of a user. Inherits the
    standard Dublin Core and RELS-EXT datastreams from
    :class:`~eulcore.fedora.models.DigitalObject`, and adds both a
    ``master`` datastream to contain the user's file as well as a content
    model for identifying these objects.
    '''
    CONTENT_MODELS = [ AccessibleObject.PUBLIC_ACCESS_CMODEL ]

    default_pidspace = getattr(settings, 'FEDORA_PIDSPACE', None)

    master = FileDatastream("master", "reposited master file", defaults={
            'versionable': True,
        })
    "reposited master :class:`~eulcore.fedora.models.FileDatastream`"
