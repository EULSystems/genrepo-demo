from django.forms import FileField, Form, Textarea, TextInput, ChoiceField

from eulcore.django.forms.fields import DynamicChoiceField
from eulcore.django.forms import XmlObjectForm
from eulcore.xmlmap.dc import DublinCore

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

class ReadOnlyInput(TextInput):
    def __init__(self, *args, **kwargs):
        readonly_attrs = {
            'readonly':'readonly',
            'class': 'readonly',
            'tabindex': '-1'
            }
        if 'attrs' in kwargs:
            kwargs['attrs'].update(readonly_attrs)
        else:
            kwargs['attrs'] = readonly_attrs
        super(ReadOnlyInput, self).__init__(*args, **kwargs)


class EditDublinCore(XmlObjectForm):
    """Form to edit Dublin Core metadata."""
    type = ChoiceField(choices=[(t, t) for t in DublinCore.DCMI_TYPES.keys()])

    class Meta:
        model = DublinCore
        fields = ['title', 'description', 'creator', 'contributor',
                  'date', 'coverage', 'language', 'publisher',
                  'relation', 'rights', 'source', 'subject', 'type',
                  'format', 'identifier']
        widgets = {
            'description': Textarea,
            'format':  ReadOnlyInput,
            'identifier':  TextInput(attrs={'readonly':'readonly', 'class': 'readonly', 'tabindex': '-1'}),
        }
