from django import forms

from eulcore.xmlmap.dc import DublinCore
from eulcore.django.forms import XmlObjectForm

class CollectionDCEditForm(XmlObjectForm):
    """Form to edit
    :class:`~genrepo.collection.models.CollectionObject` metadata."""
    title = forms.CharField(required=True,
        help_text='Title or label for the collection.')
    description = forms.CharField(required=False,
        help_text='General description of the collection and its contents. (optional)',
        widget=forms.Textarea)
    # should we offer any other fields at the collection level?
    class Meta:
        model = DublinCore
        fields = ['title', 'description']
