from django.forms import FileField, Form

from eulcore.django.forms.fields import DynamicChoiceField

from genrepo.collection.models import CollectionObject
from genrepo.util import accessible

def _collection_options():
    collections = list(accessible(CollectionObject.all()))
    options = [('', '')] + \
        [ ('info:fedora/' + c.pid, c.label or c.pid)
          for c in collections ]
    return options

class IngestForm(Form):
    """Form to ingest new files into the repository."""
    collection = DynamicChoiceField(choices=_collection_options, required=True,
        help_text="Add the new item to this collection.")
    file = FileField()
