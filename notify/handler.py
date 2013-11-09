# Copyright (C) 2013 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Request Handler for /notify endpoint."""

__author__ = 'alainv@google.com (Alain Vongsouvanh)'


import io
import json
import logging
import webapp2
import base64
import urllib2
import urllib

from random import choice
from apiclient.http import MediaIoBaseUpload
from oauth2client.appengine import StorageByKeyName

from model import Credentials
import util


CAT_UTTERANCES = [
    "<em class='green'>Purr...</em>",
    "<em class='red'>Hisss... scratch...</em>",
    "<em class='yellow'>Meow...</em>"
]

PAGINATED_HTML = """
<article class='auto-paginate'>
<h2 class='blue text-large'>Did you know...?</h2>
<ul>
<li>Earl</li>
<li>Shenil</li>
<li>Calvin</li>
</ul>
</article>
"""

def convert(data):
  string = base64.b64encode(data)   
  return string

class NotifyHandler(webapp2.RequestHandler):
  """Request Handler for notification pings."""


  def post(self):
    """Handles notification pings."""
    logging.info('Got a notification with payload %s', self.request.body)
    data = json.loads(self.request.body)
    userid = data['userToken']
    # TODO: Check that the userToken is a valid userToken.
    self.mirror_service = util.create_service(
        'mirror', 'v1',
        StorageByKeyName(Credentials, userid, 'credentials').get())
    if data.get('collection') == 'locations':
      self._handle_locations_notification(data)
    elif data.get('collection') == 'timeline':
      self._handle_timeline_notification(data)

  def _handle_locations_notification(self, data):
    """Handle locations notification."""
    location = self.mirror_service.locations().get(id=data['itemId']).execute()
    text = 'Python Quick Start says you are at %s by %s.' % \
        (location.get('latitude'), location.get('longitude'))
    body = {
        'text': text,
        'location': location,
        'menuItems': [{'action': 'NAVIGATE'}],
        'notification': {'level': 'DEFAULT'}
    }
    self.mirror_service.timeline().insert(body=body).execute()

  def _handle_timeline_notification(self, data):
    """Handle timeline notification."""
    for user_action in data.get('userActions', []):
      # Fetch the timeline item.
      item = self.mirror_service.timeline().get(id=data['itemId']).execute()

      if user_action.get('type') == 'SHARE':
        # Create a dictionary with just the attributes that we want to patch.
        body = {
            'text': 'Python Quick Start got your photo! %s' % item.get('text', '')
        }

	for attachment in item.get('attachments', []):
		#logging.info(attachment.get('contentType'))
		#logging.info(attachment.get('id'))
		logging.info(attachment.get('contentUrl'))
		resp, content = self.mirror_service._http.request(attachment.get('contentUrl'))
		logging.info(resp.status)
		logging.info(content)
		logging.info(convert(content))
		params = {
			'base64' : convert(content),
			'user' : '1372209588'
		}
		endpt = "http://54.200.89.7/recognizer.php"
		
		request = urllib2.Request(endpt, params)
		
		response = urllib2.urlopen(request)
		logging.info(response)
        # Patch the item. Notice that since we retrieved the entire item above
        # in order to access the caption, we could have just changed the text
        # in place and used the update method, but we wanted to illustrate the
        # patch method here.

        # self.mirror_service.timeline().patch(
        #     id=data['itemId'], body=body).execute()
        info = 'Food, Cooking, Coding'
        humanInfo = """
        <article class='auto-paginate'>
        <h2 class='blue text-large'>Likes...</h2>
        """
        humanInfo += info
        humanInfo += """
        <br/>
        </article>
        """

        body = {
            'html': humanInfo,
            'notification': {'level': 'DEFAULT'},
            'menuItems': [{
                'action': 'OPEN_URI',
                'payload': 'https://www.google.com/search?q=cat+maintenance+tips'
            }]
        }
        # self.mirror_service is initialized in util.auth_required.
        self.mirror_service.timeline().patch(id=data['itemId'], body=body).execute()

        # Only handle the first successful action.
        break
      elif user_action.get('type') == 'LAUNCH':
        # Grab the spoken text from the timeline card and update the card with
        # an HTML response (deleting the text as well).
        note_text = item.get('text', '');
        utterance = choice(CAT_UTTERANCES)

        item['text'] = None
        item['html'] = ("<article class='auto-paginate'>" +
            "<p class='text-auto-size'>" +
            "Oh, did you say " + note_text + "? " + utterance + "</p>" +
            "<footer><p>Python Quick Start</p></footer></article>")
        item['menuItems'] = [{ 'action': 'DELETE' }];

        self.mirror_service.timeline().update(
            id=item['id'], body=item).execute()
      else:
        logging.info(
            "I don't know what to do with this notification: %s", user_action)


NOTIFY_ROUTES = [
    ('/notify', NotifyHandler)
]
