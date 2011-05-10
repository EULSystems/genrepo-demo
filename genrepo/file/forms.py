from django.forms import FileField, Form, TextInput, Textarea, ChoiceField

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


class DublinCoreEditForm(XmlObjectForm):
    """Form to edit Dublin Core metadata for a
    :class:`~genrepo.file.models.FileObject`."""
    # configure dc:type as a choice field populated by DCMI type vocabulary
    _type_choices = [(t, t) for t in DublinCore().dcmi_types]
    # add a blank value first so there is no default value
    _type_choices.insert(0, (None, '')) 
    type = ChoiceField(choices=_type_choices, required=False)

    class Meta:
        model = DublinCore
        fields = ['title', 'description', 'creator', 'contributor',
                  'date', 'coverage', 'language', 'publisher',
                  'relation', 'rights', 'source', 'subject', 'type',
                  'format', 'identifier']
        widgets = {
            'description': Textarea,
            'format':  ReadOnlyInput,
            'identifier': ReadOnlyInput,
        }
