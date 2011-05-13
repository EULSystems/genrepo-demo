from mock import patch, Mock
import re

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import Client, TestCase

from eulcore.django.fedora import Repository
from eulcore.django.test import TestCase as EulcoreTestCase
from eulcore.fedora.api import  ApiFacade
from eulcore.fedora.models import DigitalObject
from eulcore.fedora.rdfns import relsext
from eulcore.fedora.util import RequestFailed, PermissionDenied
from eulcore.xmlmap.dc import DublinCore

from genrepo.collection.forms import CollectionDCEditForm
from genrepo.collection.models import CollectionObject

# users defined in users.json fixture
ADMIN_CREDENTIALS = {'username': 'repoeditor', 'password': 'r3p03d'} 
# in repository editor group
# NOTE: this user should be defined as a test fedora user & be added to the genrepo xacml policy
NONADMIN_CREDENTIALS = {'username': 'nobody', 'password': 'nobody'}  
# no permissions


class CollectionViewsTest(EulcoreTestCase):
    fixtures =  ['users']
    # repository with default access (no credentials)
    repo = Repository()
    # repository with test credentials for loading & removing test objects
    repo_admin = Repository(username=getattr(settings, 'FEDORA_TEST_USER', None),
                            password=getattr(settings, 'FEDORA_TEST_PASSWORD', None))

    new_coll_url = reverse('collection:new')
    
    def setUp(self):
        self.client = Client()
        # create test collection object for testing view/edit functionality
        self.obj = self.repo_admin.get_object(type=CollectionObject)
        self.obj.label = 'Genrepo test collection'
        self.obj.dc.content.title = 'my test title'
        self.obj.dc.content.description = 'this collection contains test content'
        self.obj.save()
        self.edit_coll_url = reverse('collection:edit', kwargs={'pid': self.obj.pid})
        self.view_coll_url = reverse('collection:view', kwargs={'pid': self.obj.pid})

        self.pids = [self.obj.pid]

    def tearDown(self):
        # purge any objects created by individual tests
        for pid in self.pids:
            self.repo_admin.purge_object(pid)

    def test_get_create_form(self):
        # test creating a collection object 

        # not logged in - should redirect to login page
        response = self.client.get(self.new_coll_url)
        code = response.status_code
        expected = 302
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s as AnonymousUser'
                             % (expected, code, self.new_coll_url))

        # logged in as user without required permissions - should 403
        self.client.login(**NONADMIN_CREDENTIALS)
        response = self.client.get(self.new_coll_url)
        code = response.status_code
        expected = 403
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s as logged in non-repo editor'
                             % (expected, code, self.new_coll_url))

        # log in as repository editor for all other tests
        # NOTE: using admin view so user credentials will be used to access fedora
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)

        # on GET, form should be displayed
        response = self.client.get(self.new_coll_url)
        expected, code = 200, response.status_code
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s'
                             % (expected, code, self.new_coll_url))
        self.assert_(isinstance(response.context['form'], CollectionDCEditForm),
                "CollectionDCEditForm should be set in response context")
        self.assertContains(response, 'Create a new collection')

    def test_create_invalid(self):
        # invalid post on collection object create form
        
        # log in as repository editor 
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)

        # test submitting incomplete/invalid data - should redisplay form with errors
        # title is required
        test_data = {'title': '', 'description': 'a new test collection'}
        response = self.client.post(self.new_coll_url, test_data)
        self.assert_(isinstance(response.context['form'], CollectionDCEditForm),
                "CollectionDCEditForm is set in response context when form is POSTed without title")
        self.assertContains(response, 'This field is required', 1,
            msg_prefix='error message for 1 missing required fields')

    def test_create_valid(self):
        # valid post to create collection object

        # log in as repository editor 
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
        
        # POST and create new object, verify in fedora
        test_data = {'title': 'genrepo test collection',
                     'description': 'my second test collection'}
        response = self.client.post(self.new_coll_url, test_data, follow=True)
        # on success, should redirect with a message about the object
        messages = [ str(msg) for msg in response.context['messages'] ]
        self.assert_('Successfully created new collection' in messages[0],
                     'successful collection creation message displayed to user')
        # inspect newly created object and in fedora
        # - pull the pid out of the success message
        pidmatch = re.search('<b>(.*)</b>', messages[0])
        pid = pidmatch.group(1) # first parenthesized subgroup
        # append to list of pids to be cleaned up after the test
        self.pids.append(pid)

        # inspect object - use repo_admin so we can access it
        new_obj = self.repo_admin.get_object(pid, type=CollectionObject)
        self.assertTrue(new_obj.has_requisite_content_models,
                 'new object was created with the expected content models for a CollectionObject')
        self.assertEqual(test_data['title'], new_obj.dc.content.title,
        	"posted title should be set in dc:title; expected '%s', got '%s'" % \
                 (test_data['title'], new_obj.dc.content.title))
        self.assertEqual(test_data['description'], new_obj.dc.content.description,
                 "posted description should be set in dc:description; expected '%s', got '%s'" % \
                 (test_data['description'], new_obj.dc.content.description))
        self.assertEqual(test_data['title'], new_obj.label,
                 "posted title should be set in object label; expected '%s', got '%s'" % \
                 (test_data['title'], new_obj.label))

        # confirm that current site user appears in fedora audit trail
        xml, uri = new_obj.api.getObjectXML(pid)
        self.assert_('<audit:responsibility>%s</audit:responsibility>' % \
                     ADMIN_CREDENTIALS['username'] in xml)

    def test_create_save_errors(self):
        # simulate fedora errors with mock objects

        # log in as repository editor 
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
        
        testobj = Mock(name='MockDigitalObject')
        testobj.dc.content = DublinCore()
        # Create a RequestFailed exception to simulate Fedora error 
        # - eulcore.fedora wrap around an httplib response
        err_resp = Mock()
        err_resp.status = 500
   	err_resp.read.return_value = 'error message'
        # generate Fedora error on object save
        testobj.save.side_effect = RequestFailed(err_resp)

        # valid form data to post
        test_data = {'title': 'foo', 'description': 'bar'}

        # 500 error / request failed
        # patch the repository class to return the mock object instead of a real one
	with patch.object(Repository, 'get_object', new=Mock(return_value=testobj)):            
            response = self.client.post(self.new_coll_url, test_data, follow=True)
            expected, code = 500, response.status_code
            self.assertEqual(code, expected,
            	'Expected %s but returned %s for %s (Fedora 500 error)'
                % (expected, code, self.new_coll_url))
            messages = [ str(msg) for msg in response.context['messages'] ]
            self.assert_('error communicating with the repository' in messages[0])

        # update the mock error to generate a permission denied error
        err_resp.status = 401
        err_resp.read.return_value = 'denied'
        # generate Fedora error on object save
        testobj.save.side_effect = PermissionDenied(err_resp) 
        
        # 401 error -  permission denied
	with patch.object(Repository, 'get_object', new=Mock(return_value=testobj)):            
            response = self.client.post(self.new_coll_url, test_data, follow=True)
            expected, code = 401, response.status_code
            self.assertEqual(code, expected,
            	'Expected %s but returned %s for %s (Fedora 401 error)'
                % (expected, code, self.new_coll_url))
            messages = [ str(msg) for msg in response.context['messages'] ]
            self.assert_("You don't have permission to create a collection"
                         in messages[0])

    def test_get_edit_form(self):
        # not logged in - should redirect to login page
        response = self.client.get(self.edit_coll_url)
        code = response.status_code
        expected = 302
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s as AnonymousUser'
                             % (expected, code, self.edit_coll_url))

        # logged in as user without required permissions - should 403
        self.client.post(settings.LOGIN_URL, NONADMIN_CREDENTIALS)
        response = self.client.get(self.edit_coll_url)
        code = response.status_code
        expected = 403
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s as logged in non-repo editor'
                             % (expected, code, self.edit_coll_url))

        # log in as repository editor 
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)

        # on GET, form should be displayed
        response = self.client.get(self.edit_coll_url)
        expected, code = 200, response.status_code
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s'
                             % (expected, code, self.edit_coll_url))
        self.assert_(isinstance(response.context['form'], CollectionDCEditForm),
                "CollectionDCEditForm should be set in response context")
        self.assertEqual(response.context['form'].instance, self.obj.dc.content)
        self.assertContains(response, 'Update %s' % self.obj.label)

    def test_valid_edit_form(self):
        # log in as repository editor 
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)

        # POST data and update object, verify in fedora
        update_data = {
            'title': 'new title',
            'description': 'new description too'
        }
        response = self.client.post(self.edit_coll_url, update_data, follow=True)
        # on success, should redirect with a message about the object
        messages = [ str(msg) for msg in response.context['messages'] ]
        self.assert_('Successfully updated collection' in messages[0],
                     'successful collection update message displayed to user')
        # get a fresh copy of the object to compare
        updated_obj = self.repo_admin.get_object(self.obj.pid, type=CollectionObject)
        self.assertEqual(update_data['title'], updated_obj.dc.content.title,
        	"posted title should be set in dc:title; expected '%s', got '%s'" % \
                 (update_data['title'], updated_obj.dc.content.title))
        self.assertEqual(update_data['description'], updated_obj.dc.content.description,
                 "posted description should be set in dc:description; expected '%s', got '%s'" % \
                 (update_data['description'], updated_obj.dc.content.description))
        self.assertEqual(update_data['title'], updated_obj.label,
                 "posted title should be set in object label; expected '%s', got '%s'" % \
                 (update_data['title'], updated_obj.label))

    def test_view(self):
        # test viewing an existing collection object

        # not logged in - public access content only for now, should
        # be accessible to anyone
        response = self.client.get(self.view_coll_url)
        code = response.status_code
        expected = 200
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s as AnonymousUser'
                             % (expected, code, self.view_coll_url))
        self.assertNotContains(response, reverse('collection:edit', kwargs={'pid': self.obj.pid}),
            msg_prefix='collection view should not include edit link for non repo editor')


        # logged in as user without required permissions - should still be accessible
        # NOTE: using admin view so user credentials will be used to access fedora
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
        response = self.client.get(self.view_coll_url)
        code = response.status_code
        expected = 200
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s as logged in non-repo editor'
                             % (expected, code, self.view_coll_url))
        

        # check for object display
        self.assert_(isinstance(response.context['obj'], CollectionObject),
                     'collection object should be set in response context')
        self.assertEqual(self.obj.pid, response.context['obj'].pid,
                         'correct collection object should be set in response context')

        self.assertContains(response, self.obj.label,
                            msg_prefix='response should include title of collection object')
        self.assertContains(response, self.obj.dc.content.description,
                            msg_prefix='response should include description of collection object')
        self.assertContains(response, reverse('collection:edit', kwargs={'pid': self.obj.pid}),
            msg_prefix='collection view should include edit link for repo editor')


    def test_view_nonexistent(self):
        # non-existent object should 404
        view_coll_url = reverse('collection:view', kwargs={'pid': 'bogus:nonexistent-pid'})

        response = self.client.get(view_coll_url)
        code = response.status_code
        expected = 404
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s (nonexistent object)'
                             % (expected, code, view_coll_url))

    def test_view_members(self):
        # collection view should include brief listing of items that belong to the collection
        # use mock objects to test collection member view
        testcoll = Mock(name='MockCollectionObject')
        testcoll.pid = 'coll:1'
        file1 = Mock(name='MockDigitalObject')
        file1.pid = 'file:1'
        file1.label = 'One Fish'
        file2 = Mock(name='MockDigitalObject')
        file2.pid = 'file:2'
        file2.label = 'Two Fish'
        testcoll.members = [file1, file2]

        # patch the repository class to return the mock object instead of a real one
	with patch.object(Repository, 'get_object', new=Mock(return_value=testcoll)):
            response = self.client.get(self.view_coll_url)
            code = response.status_code
            expected = 200
            self.assertEqual(code, expected,
                             'Expected %s but returned %s for %s as AnonymousUser'
                             % (expected, code, self.view_coll_url))
            
            # member items should be listed
            self.assertContains(response, file1.label,
                msg_prefix='collection view should include first member item label')
            self.assertContains(response, file2.label,
                msg_prefix='collection view should include second member item label')
            self.assertContains(response, reverse('file:view', kwargs={'pid': file1.pid}),
                msg_prefix='collection view should include link to view first member item')
            self.assertContains(response, reverse('file:view', kwargs={'pid': file2.pid}),
                msg_prefix='collection view should include link to view second member item')
            self.assertNotContains(response, reverse('file:edit', kwargs={'pid': file1.pid}),
                msg_prefix='collection view should include link to edit first member item (not repo editor)')
            self.assertNotContains(response, reverse('file:edit', kwargs={'pid': file2.pid}),
                msg_prefix='collection view should include link to edit second member item (not repo editor)')

        # log in as repo editor - should also see item edit links
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
	with patch.object(Repository, 'get_object', new=Mock(return_value=testcoll)):
            response = self.client.get(self.view_coll_url)
            self.assertContains(response, reverse('file:edit', kwargs={'pid': file1.pid}),
                msg_prefix='collection view should include link to edit first member item (repo editor)')
            self.assertContains(response, reverse('file:edit', kwargs={'pid': file2.pid}),
                msg_prefix='collection view should include link to edit second member item (repo editor)')


        
class CollectionObjectTest(TestCase):
    'Tests for :mod:`genrepo.collection.models.CollectionObject`'
    
    def setUp(self):
        # use an in-ingested collection object with a mock API for now (until we need more)
        self.coll = CollectionObject(Mock())
        
    def test_members(self):
        # mock out risearch call
        member_pids = ['pid:1', 'pid:2']
        mockri = Mock(name='MockRIsearch')
        mockri.get_subjects.return_value = member_pids
        with patch.object(Repository, 'risearch', new=mockri):
            members = list(self.coll.members)
            self.assertEqual(len(member_pids), len(members),
                'collection members length should equal number of items returned by risearch call')
            self.assert_(isinstance(members[0], DigitalObject),
                'collection members should be instances of DigitalObject')
            self.assert_(isinstance(members[1], DigitalObject),
                'collection members should be instances of DigitalObject')
            mockri.get_subjects.assert_called_once_with(relsext.isMemberOfCollection,
                                                        self.coll.uri)

        
