from mock import patch, Mock
import re
    
from django.core.urlresolvers import reverse
from django.test import Client

from eulcore.django.fedora import Repository
from eulcore.django.test import TestCase as EulcoreTestCase
from eulcore.fedora.api import  ApiFacade
from eulcore.fedora.util import RequestFailed, PermissionDenied

from genrepo.collection.forms import CollectionDCEditForm
from genrepo.collection.models import CollectionObject

class CollectionViewsTest(EulcoreTestCase):
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

        # on GET, form should be displayed
        response = self.client.get(new_coll_url)
        expected, code = 200, response.status_code
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s'
                             % (expected, code, new_coll_url))
        self.assert_(isinstance(response.context['form'], CollectionDCEditForm),
                "CollectionDCEditForm should be set in response context")

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
