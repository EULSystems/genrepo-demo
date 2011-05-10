import os
import re

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import Client
from rdflib import URIRef

from eulcore.django.test import TestCase as EulcoreTestCase
from eulcore.django.fedora import Repository
from eulcore.fedora.rdfns import relsext

from genrepo.file.forms import IngestForm
from genrepo.file.models import FileObject
from genrepo.collection.tests import ADMIN_CREDENTIALS, NONADMIN_CREDENTIALS

class FileViewsTest(EulcoreTestCase):
    fixtures =  ['users']   # re-using collection users fixture & credentials

    repo_admin = Repository(username=getattr(settings, 'FEDORA_TEST_USER', None),
                            password=getattr(settings, 'FEDORA_TEST_PASSWORD', None))

    ingest_fname = os.path.join(settings.BASE_DIR, 'file', 'fixtures', 'hello.txt')

    ingest_url = reverse('file:ingest')

    def setUp(self):
        self.client = Client()
        self.pids = []

    def tearDown(self):
        for pid in self.pids:
            self.repo_admin.purge_object(pid)

    # ingest

    def test_get_ingest_form(self):
        # not logged in - should redirect to login page
        response = self.client.get(self.ingest_url)
        code = response.status_code
        expected = 302
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s as AnonymousUser'
                             % (expected, code, self.ingest_url))

        # logged in as user without required permissions - should 403
        self.client.login(**NONADMIN_CREDENTIALS)
        response = self.client.get(self.ingest_url)
        code = response.status_code
        expected = 403
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for GET %s as logged in non-repo editor'
                         % (expected, code, self.ingest_url))

        # log in as repository editor 
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
        # on GET, form should be displayed
        response = self.client.get(self.ingest_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.context['form'], IngestForm))

    def test_incomplete_ingest_form(self):
        # not logged in - should redirect to login page
        response = self.client.post(self.ingest_url)
        code = response.status_code
        expected = 302
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for POST %s as AnonymousUser'
                         % (expected, code, self.ingest_url))

        # logged in as user without required permissions - should 403
        self.client.login(**NONADMIN_CREDENTIALS)
        response = self.client.post(self.ingest_url)
        code = response.status_code
        expected = 403
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for POST %s as logged in non-repo editor'
                         % (expected, code, self.ingest_url))

        # log in as repository editor for normal behavior
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)


        # on POST with incomplete data, should be rejected
        response = self.client.post(self.ingest_url, {
                'collection': 'info:fedora/example:42',
            })
        self.assertTrue(isinstance(response.context['form'], IngestForm))
        self.assertContains(response, 'This field is required')

    def test_correct_ingest_form(self):
        # log in as repository editor for normal behavior
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
        
        # first find a valid collection
        collections = IngestForm().fields['collection'].choices
        collection_tuple = collections[1] # 0 is blank. 1 is the first non-blank one
        collection_uri = collection_tuple[0]

        # log in
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)

        # on POST, ingest object
        with open(self.ingest_fname) as ingest_f:
            response = self.client.post(self.ingest_url, {
                'collection': collection_uri,
                'file': ingest_f,
            }, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][1], 303)
        self.assertEqual(response.status_code, 200)
        messages = [ str(msg) for msg in response.context['messages'] ]
        self.assertTrue('Successfully ingested' in messages[0])
        pid = re.search('<b>(.*)</b>', messages[0]).group(1)
        self.pids.append(pid)

        new_obj = self.repo_admin.get_object(pid, type=FileObject)
        self.assertTrue(new_obj.has_requisite_content_models)
        statement = (new_obj.uriref, relsext.isMemberOfCollection, URIRef(collection_uri))
        self.assertTrue(statement in new_obj.rels_ext.content, msg='RELS-EXT should have collection statement')
        with open(self.ingest_fname) as ingest_f:
            self.assertEqual(new_obj.master.content.read(), ingest_f.read())
