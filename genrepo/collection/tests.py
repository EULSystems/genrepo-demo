from mock import patch, Mock
import re

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import Client

from eulcore.django.fedora import Repository
from eulcore.django.test import TestCase as EulcoreTestCase
from eulcore.fedora.api import  ApiFacade
from eulcore.fedora.util import RequestFailed, PermissionDenied

from genrepo.collection.forms import CollectionDCEditForm
from genrepo.collection.models import CollectionObject

# users defined in users.json fixture
ADMIN_CREDENTIALS = {'username': 'repoeditor', 'password': 'r3p03d'} # in repository editor group
NONADMIN_CREDENTIALS = {'username': 'nobody', 'password': 'nobody'}  # no permissions


class CollectionViewsTest(EulcoreTestCase):
    fixtures =  ['users']
    repo = Repository()

    def setUp(self):
        self.client = Client()
        self.pids = []

    def tearDown(self):
        # purge any objects created by individual tests
        for pid in self.pids:
            self.repo.purge_object(pid)

    def test_create(self):
        # test creating a collection object

        # No login/credentials required for now  (TODO later)
        new_coll_url = reverse('collection:new')

        # not logged in - should redirect to login page
        response = self.client.get(new_coll_url)
        code = response.status_code
        expected = 302
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s as AnonymousUser'
                             % (expected, code, new_coll_url))

        # logged in as user without required permissions - should 403
        self.client.login(**NONADMIN_CREDENTIALS)
        response = self.client.get(new_coll_url)
        code = response.status_code
        expected = 403
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s as logged in non-repo editor'
                             % (expected, code, new_coll_url))

        # log in as repository editor for all other tests
        # NOTE: using admin view so user credentials will be used to access fedora
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
#        self.client.login(**ADMIN_CREDENTIALS)

        # on GET, form should be displayed
        response = self.client.get(new_coll_url)
        expected, code = 200, response.status_code
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s'
                             % (expected, code, new_coll_url))
        self.assert_(isinstance(response.context['form'], CollectionDCEditForm),
                "CollectionDCEditForm should be set in response context")
        self.assertContains(response, 'Create a new collection')

        # test submitting incomplete/invalid data - should redisplay form with errors
        # title is required
        test_data = {'title': '', 'description': 'a new test collection'}
        response = self.client.post(new_coll_url, test_data)
        self.assert_(isinstance(response.context['form'], CollectionDCEditForm),
                "CollectionDCEditForm is set in response context when form is POSTed without title")
        self.assertContains(response, 'This field is required', 1,
            msg_prefix='error message for 1 missing required fields')

        # POST and create new object, verify in fedora
        test_data['title'] = 'genrepo test collection'
        response = self.client.post(new_coll_url, test_data, follow=True)
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
        
        new_obj = self.repo.get_object(pid, type=CollectionObject)
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
        self.assert_('<audit:responsibility>%s</audit:responsibility>' % ADMIN_CREDENTIALS['username'] in xml)

        # simulate fedora errors with mock objects

	mockrepo = Mock(spec=Repository, name='MockRepository')
        # this actually mocks the class, so return same mock when class is instantiated
        mockrepo.return_value = mockrepo
        # create a mockapi to pass to collection object
        mockapi = Mock(name='MockApiFacade')
        # create a test collection object with a mock api
        # (easier to use an actual collection object since xmlobjectform inspects the fields)
        testobj = CollectionObject(api=mockapi)
        # Create a RequestFailed exception to simulate Fedora error 
        # - eulcore.fedora exceptions are initialized from httplib response,
        #   which can't be instantiated directly; create a mock response
        err_resp = Mock()
        err_resp.status = 500
        err_resp.reason = 'error'
        err_resp.read.return_value = 'error message'
        # generate Fedora error on getNextPID (first api call made for a new object)
        testobj.api.getNextPID.side_effect = RequestFailed(err_resp)
        # set testobj with mock api to be returned by mockrepo
        mockrepo.get_object.return_value = testobj

        # 500 error / request failed
	with patch('genrepo.collection.views.Repository', new=mockrepo):
            response = self.client.post(new_coll_url, test_data, follow=True)
            expected, code = 500, response.status_code
            self.assertEqual(code, expected,
            	'Expected %s but returned %s for %s (Fedora 500 error)'
                % (expected, code, new_coll_url))
            messages = [ str(msg) for msg in response.context['messages'] ]
            self.assert_('error communicating with the repository' in messages[0])

        # update the mock api to generate a permission denied error
        err_resp.status = 401
        err_resp.reason = 'unauthorized'
        err_resp.read.return_value = 'denied'
        # generate Fedora error on getNextPID (first api call made for new object)
        testobj.api.getNextPID.side_effect = PermissionDenied(err_resp)
        
        # 401 error -  permission denied
	with patch('genrepo.collection.views.Repository', new=mockrepo):
            response = self.client.post(new_coll_url, test_data, follow=True)
            expected, code = 401, response.status_code
            self.assertEqual(code, expected,
            	'Expected %s but returned %s for %s (Fedora 401 error)'
                % (expected, code, new_coll_url))
            messages = [ str(msg) for msg in response.context['messages'] ]
            self.assert_("You don't have permission to create a collection"
                         in messages[0])

    def test_edit(self):
        # test editing an existing collection
        obj = self.repo.get_object(type=CollectionObject)
        obj.label = 'Genrepo test collection'
        obj.dc.content.title = 'my test title'
        obj.dc.content.description = 'this collection contains test content'
        obj.save()
        # append to list of pids to be cleaned up after the test
        self.pids.append(obj.pid)
        
        edit_coll_url = reverse('collection:edit', kwargs={'pid': obj.pid})

        # not logged in - should redirect to login page
        response = self.client.get(edit_coll_url)
        code = response.status_code
        expected = 302
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s as AnonymousUser'
                             % (expected, code, edit_coll_url))

        # logged in as user without required permissions - should 403
        self.client.login(**NONADMIN_CREDENTIALS)
        response = self.client.get(edit_coll_url)
        code = response.status_code
        expected = 403
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s as logged in non-repo editor'
                             % (expected, code, edit_coll_url))

        # log in as repository editor for all other tests
        self.client.login(**ADMIN_CREDENTIALS)

        # on GET, form should be displayed
        response = self.client.get(edit_coll_url)
        expected, code = 200, response.status_code
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s'
                             % (expected, code, edit_coll_url))
        self.assert_(isinstance(response.context['form'], CollectionDCEditForm),
                "CollectionDCEditForm should be set in response context")
        self.assertEqual(response.context['form'].instance, obj.dc.content)
        self.assertContains(response, 'Update %s' % obj.label)

        # POST data and update object, verify in fedora
        update_data = {
            'title': 'new title',
            'description': 'new description too'
        }
        response = self.client.post(edit_coll_url, update_data, follow=True)
        # on success, should redirect with a message about the object
        messages = [ str(msg) for msg in response.context['messages'] ]
        self.assert_('Successfully updated collection' in messages[0],
                     'successful collection update message displayed to user')
        # get a fresh copy of the object to compare
        updated_obj = self.repo.get_object(obj.pid, type=CollectionObject)
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
       # test viewing an existing collection
        obj = self.repo.get_object(type=CollectionObject)
        obj.label = 'Genrepo test collection'
        obj.dc.content.title = 'my test title for view'
        obj.dc.content.description = 'this collection contains test content for view'
        obj.save()
        # append to list of pids to be cleaned up after the test
        self.pids.append(obj.pid)

        view_coll_url = reverse('collection:view', kwargs={'pid': obj.pid})

        # not logged in - public access content only for now, should
        # be accessible to anyone
        response = self.client.get(view_coll_url)
        code = response.status_code
        expected = 200
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s as AnonymousUser'
                             % (expected, code, view_coll_url))

        # logged in as user without required permissions - should still be accessible
        # NOTE: using admin view so user credentials will be used to access fedora
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
        response = self.client.get(view_coll_url)
        code = response.status_code
        expected = 200
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s as logged in non-repo editor'
                             % (expected, code, view_coll_url))

        # check for object display
        self.assert_(isinstance(response.context['obj'], CollectionObject),
                     'collection object should be set in response context')
        self.assertEqual(obj.pid, response.context['obj'].pid,
                         'correct collection object should be set in response context')

        self.assertContains(response, obj.label,
                            msg_prefix='response should include title of collection object')
        self.assertContains(response, obj.dc.content.description,
                            msg_prefix='response should include description of collection object')

        # non-existent object
        view_coll_url = reverse('collection:view', kwargs={'pid': 'bogus:nonexistent-pid'})

        response = self.client.get(view_coll_url)
        code = response.status_code
        expected = 404
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s (nonexistint object)'
                             % (expected, code, view_coll_url))
        
