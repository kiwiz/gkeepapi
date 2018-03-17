# -*- coding: utf-8 -*-
"""
.. moduleauthor:: Kai <z@kwi.li>
"""

import logging
import re
import time
import random

from uuid import getnode as get_mac

import six
import gpsoauth
import requests

from . import node as _node

logger = logging.getLogger('keep')

class APIException(Exception):
    """The API server returned an error."""
    def __init__(self, code, msg):
        super(APIException, self).__init__(msg)
        self.code = code

class KeepException(Exception):
    """Generic Keep error."""
    pass

class LoginException(KeepException):
    """Login exception."""
    pass

class LabelException(KeepException):
    """Keep label error."""
    pass

class SyncException(KeepException):
    """Keep consistency error."""
    pass

class APIAuth(object):
    """Authentication token manager"""
    def __init__(self, scopes):
        self._master_token = None
        self._auth_token = None
        self._email = None
        self._android_id = None
        self._scopes = scopes

    def login(self, email, password, android_id):
        """Authenticate to Google with the provided credentials.

        Args:
            email (str): The account to use.
            password (str): The account password.
            android_id (str): An identifier for this client.

        Raises:
            LoginException: If there was a problem logging in.
        """
        self._email = email
        self._android_id = android_id
        res = gpsoauth.perform_master_login(self._email, password, self._android_id)
        if 'Token' not in res:
            raise LoginException(res.get('Error'), res.get('ErrorDetail'))
        self._master_token = res['Token']

        self.refresh()
        return True

    def setMasterToken(self, master_token):
        """Sets the master token. This is useful if you'd like to authenticate
        with the API without providing your username & password.
        Do note that the master token has full access to your account.

        Args:
            master_token (str): The account master token.
        """
        self._master_token = master_token

    def getMasterToken(self):
        """Gets the master token.

        Returns:
            str: The account master token.
        """
        return self._master_token

    def getAuthToken(self):
        """Gets the auth token.

        Returns:
            Union[str, None]: The auth token.
        """
        return self._auth_token

    def refresh(self):
        """Refresh the OAuth token.

        Returns:
            string: The auth token.

        Raises:
            LoginException: If there was a problem refreshing the OAuth token.
        """
        res = gpsoauth.perform_oauth(
            self._email, self._master_token, self._android_id,
            service=self._scopes,
            app='com.google.android.keep',
            client_sig='38918a453d07199354f8b19af05ec6562ced5788'
        )
        if 'Auth' not in res:
            if 'Token' not in res:
                raise LoginException(res.get('Error'))

        self._auth_token = res['Auth']
        return self._auth_token

    def logout(self):
        """Log out of the account."""
        self._master_token = None
        self._auth_token = None
        self._email = None
        self._android_id = None

class API(object):
    """Base API wrapper"""
    RETRY_CNT = 2
    def __init__(self, base_url, auth=None):
        self._session = requests.Session()
        self._auth = auth
        self._base_url = base_url
        self._session.headers.update({'User-Agent': 'gkeepapi/0.10.4'})

    def setAuth(self, auth):
        """Set authentication details for this API.

        Args:
            auth (APIAuth): The auth object
        """
        self._auth = auth

    def send(self, **req_kwargs):
        """Send an authenticated request to the Google Keep API.
        Automatically retries if the access token has expired.

        Args:
            **req_kwargs: Arbitrary keyword arguments to pass to Requests.

        Return:
            dict: The parsed JSON response.

        Raises:
            APIException: If the server returns an error.
            LoginException: If :py:meth:`login` has not been called.
        """
        auth_token = self._auth.getAuthToken()
        if auth_token is None:
            raise LoginException('Not logged in')

        req_kwargs.setdefault('headers', {})

        i = 0
        while True:
            req_kwargs['headers']['Authorization'] = 'OAuth ' + auth_token

            response = self._session.request(**req_kwargs).json()
            if 'error' not in response:
                break

            error = response['error']
            if error['code'] != 401:
                raise APIException(error['code'], error)

            if i >= self.RETRY_CNT:
                raise APIException(error['code'], error)

            logger.info('Refreshing access token')
            auth_token = self._auth.refresh()
            i += 1

        return response

class KeepAPI(API):
    """Low level Google Keep API client. Mimics the Android Google Keep app.

    You probably want to use :py:class:`Keep` instead.
    """
    API_URL = 'https://www.googleapis.com/notes/v1/'

    def __init__(self, auth=None):
        super(KeepAPI, self).__init__(self.API_URL, auth)

        create_time = time.time()
        self._session_id = self._generateId(create_time)

    @classmethod
    def _generateId(cls, tz):
        return 's--%d--%d' % (
            int(tz * 1000),
            random.randint(1000000000, 9999999999)
        )

    def changes(self, target_version=None, nodes=None, labels=None):
        """Sync up (and down) all changes.

        Args:
            target_version (str): The local change version.
            nodes (List[dict]): A list of nodes to sync up to the server.
            labels (List[dict]): A list of labels to sync up to the server.

        Return:
            dict: Description of all changes.

        Raises:
            APIException: If the server returns an error.
        """
        if nodes is None:
            nodes = []
        if labels is None:
            labels = []

        current_time = time.time()

        params = {
            'nodes': nodes,
            'clientTimestamp': _node.NodeTimestamps.int_to_str(current_time),
            'requestHeader': {
                'clientSessionId': self._session_id,
                'clientPlatform': 'ANDROID',
                'clientVersion': {
                    'major': '9',
                    'minor': '9',
                    'build': '9',
                    'revision': '9'
                },
                'capabilities': [
                    {'type': 'NC'}, # Color support (Send note color)
                    {'type': 'PI'}, # Pinned support (Send note pinned)
                    {'type': 'LB'}, # Labels support (Send note labels)
                    {'type': 'AN'}, # Annotations support (Send annotations)
                    {'type': 'SH'}, # Sharing support
                    {'type': 'DR'}, # Drawing support
                    {'type': 'TR'}, # Trash support (Stop setting the delete timestamp)

                    {'type': 'SNB'}, # Allows modification of shared notes?

                    # TODO: Figure out what these do:
                    # {'type': 'CO'}, # VSS_SUCCEEDED when off?
                    # {'type': 'EC'}, # ???
                    # {'type': 'RB'}, # Rollback?
                    # {'type': 'EX'}, # ???
                    # {'type': 'MI'}, # ???
                ]
            },
        }
        if target_version is not None:
            params['targetVersion'] = target_version

        if labels:
            params['userInfo'] = {
                'labels': labels
            }

        logger.debug('Syncing %d labels and %d nodes', len(labels), len(nodes))

        return self.send(
            url=self._base_url + 'changes',
            method='POST',
            json=params
        )

class RemindersAPI(API):
    """Low level Google Reminders API client. Mimics the Android Google Keep app.

    You probably want to use :py:class:`Keep` instead.
    """
    API_URL = 'https://www.googleapis.com/reminders/v1internal/reminders/'

    def __init__(self, auth=None):
        super(RemindersAPI, self).__init__(self.API_URL, auth)

    def create(self):
        params = {}
        return self.send(
            url=self._base_url + 'create',
            method='POST',
            json=params
        )

    def list(self):
        params = {}
        return self.send(
            url=self._base_url + 'list',
            method='POST',
            json=params
        )

    def history(self):
        params = {}
        return self.send(
            url=self._base_url + 'history',
            method='POST',
            json=params
        )

    def update(self):
        params = {}
        return self.send(
            url=self._base_url + 'update',
            method='POST',
            json=params
        )

class Keep(object):
    """High level Google Keep client.

    Stores a local copy of the Keep node tree. To start, first login::

        keep.login('...', '...')

    Individual Notes can be retrieved by id::

        some_note = keep.get('some_id')

    New Notes can be created::

        new_note = keep.createNote()

    These Notes can then be modified::

        some_note.text = 'Test'
        new_note.text = 'Text'

    These changes are automatically detected and synced up with::

        keep.sync()
    """
    def __init__(self):
        self._keep_api = KeepAPI()
        self._reminders_api = RemindersAPI()
        self._version = None
        self._labels = {}
        self._nodes = {}

        root_node = _node.Root()
        self._nodes[_node.Root.ID] = root_node

    def login(self, username, password):
        """Authenticate to Google with the provided credentials.

        Args:
            email (str): The account to use.
            password (str): The account password.

        Raises:
            LoginException: If there was a problem logging in.
        """
        auth = APIAuth('oauth2:https://www.googleapis.com/auth/memento https://www.googleapis.com/auth/reminders')

        ret = auth.login(username, password, get_mac())
        if ret:
            self._keep_api.setAuth(auth)
            self._reminders_api.setAuth(auth)
            self.sync()

        return ret

    def get(self, node_id):
        """Get a note with the given ID.

        Args:
            node_id (str): The note ID.

        Returns:
            gkeepapi.node.TopLevelNode: The Note or None if not found.
        """
        return self._nodes[_node.Root.ID].get(node_id)

    def add(self, node):
        """Register a top level node (and its children) for syncing up to the server. There's no need to call this for nodes created by
        :py:meth:`createNote` or :py:meth:`createList` as they are automatically added.

            LoginException: If :py:meth:`login` has not been called.
        Args:
            node (gkeepapi.node.Node): The node to sync.

        Raises:
            SyncException: If the parent node is not found.
        """
        if node.parent_id != _node.Root.ID:
            raise SyncException('Not a top level node')

        self._nodes[node.id] = node
        self._nodes[node.parent_id].append(node, False)

    def find(self, query=None, func=None, labels=None, colors=None, pinned=None, archived=None, trashed=False): # pylint: disable=too-many-arguments
        """Find Notes based on the specified criteria.

        Args:
            query (Union[_sre.SRE_Pattern, str, None]): A str or regular expression to match against the title and text.
            func (Union[callable, None]): A filter function.
            labels (Union[List[str], None]): A list of label ids or objects to match.
            colors (Union[List[str], None]): A list of colors to match.
            pinned (Union[bool, None]): Whether to match pinned notes.
            archived (Union[bool, None]): Whether to match archived notes.
            trashed (Union[bool, None]): Whether to match trashed notes.

        Return:
            List[gkeepapi.node.TopLevelNode]: Results.
        """
        if labels is not None:
            labels = [i.id if isinstance(i, _node.Label) else i for i in labels]

        return (node for node in self.all() if
            (query is None or (
                (isinstance(query, six.string_types) and (query in node.title or query in node.text)) or
                (isinstance(query, re._pattern_type) and ( # pylint: disable=protected-access
                    query.search(node.title) or query.search(node.text)
                ))
            )) and
            (func is None or func(node)) and \
            (labels is None or any((node.labels.get(i) is not None for i in labels))) and \
            (colors is None or node.color in colors) and \
            (pinned is None or node.pinned == pinned) and \
            (archived is None or node.archived == archived) and \
            (trashed is None or node.trashed == trashed)
        )

    def createNote(self, title=None, text=None):
        """Create a new managed note. Any changes to the note will be uploaded when :py:meth:`sync` is called.

        Args:
            title (str): The title of the note.
            text (str): The text of the note.

        Returns:
            gkeepapi.node.List: The new note.
        """
        node = _node.Note()
        if title is not None:
            node.title = title
        if text is not None:
            node.text = text
        self.add(node)
        return node

    def createList(self, title=None, items=None):
        """Create a new list and populate it. Any changes to the note will be uploaded when :py:meth:`sync` is called.

        Args:
            title (str): The title of the list.
            items (List[(str, bool)]): A list of tuples. Each tuple represents the text and checked status of the listitem.

        Returns:
            gkeepapi.node.List: The new list.
        """
        if items is None:
            items = []

        node = _node.List()
        if title is not None:
            node.title = title
        for text, checked in items:
            node.add(text, checked)
        self.add(node)
        return node

    def createLabel(self, name):
        """Create a new label.

        Args:
            name (str): Label name.

        Returns:
            gkeepapi.node.Label: The new label.

        Raises:
            LabelException: If the label exists.
        """
        name = name.lower()
        if name in self._labels:
            raise LabelException('Label exists')
        node = _node.Label()
        node.name = name
        self._labels[node.id] = node
        return node

    def findLabel(self, query, create=False):
        """Find a label with the given name.

        Args:
            name (Union[_sre.SRE_Pattern, str]): A str or regular expression to match against the name.
            create (bool): Whether to create the label if it doesn't exist (only if name is a str).

        Returns:
            Union[gkeepapi.node.Label, None]: The label.
        """
        for label in self._labels.values():
            if (isinstance(query, six.string_types) and query == label.name) or \
                (isinstance(query, re._pattern_type) and query.search(label.name)): # pylint: disable=protected-access
                return label

        return self.createLabel(query) if create and isinstance(query, six.string_types) else None

    def getLabel(self, label_id):
        """Get an existing label.

        Args:
            label_id (str): Label id.

        Returns:
            Union[gkeepapi.node.Label, None]: The label.
        """
        return self._labels.get(label_id)

    def deleteLabel(self, label_id):
        """Deletes a label.

        Args:
            label_id (str): Label id.
        """
        if label_id not in self._labels:
            return

        label = self._labels[label_id]
        label.delete()
        for node in self.all():
            node.labels.remove(label)

    def labels(self):
        """Get all labels.

        Returns:
            List[gkeepapi.node.Label]: Labels
        """
        return self._labels

    def all(self):
        """Get all Notes.

        Returns:
            List[gkeepapi.node.TopLevelNode]: Notes
        """
        return self._nodes[_node.Root.ID].children

    def sync(self):
        """Sync the local Keep tree with the server. Local changes to notes and labels will be detected and synced up.

        Raises:
            SyncException: If there is a consistency issue.
        """
        while True:
            logger.debug('Starting sync: %s', self._version)

            labels_updated = any((i.dirty for i in self._labels.values()))
            changes = self._keep_api.changes(
                target_version=self._version,
                nodes=[i.save() for i in self._findDirtyNodes()],
                labels=[i.save() for i in self._labels.values()] if labels_updated else None,
            )

            if changes.get('forceFullResync'):
                raise SyncException('Full resync required')

            if 'userInfo' in changes:
                self._parseUserInfo(changes['userInfo'])

            if 'nodes' in changes:
                self._parseNodes(changes['nodes'])

            self._version = changes['toVersion']
            logger.debug('Finishing sync: %s', self._version)
            if not changes['truncated']:
                break

        if _node.DEBUG:
            self._clean()

    def _parseNodes(self, raw):
        updated_nodes = []
        deleted_nodes = []
        for raw_node in raw:
            if raw_node['id'] in self._nodes:
                node = self._nodes[raw_node['id']]

                if 'parentId' in raw_node:
                    node.load(raw_node)
                    logger.debug('Updated node: %s', raw_node['id'])
                else:
                    deleted_nodes.append(node)

            else:
                node = _node.from_json(raw_node)
                if node is None:
                    logger.debug('Discarded unknown node')
                else:
                    self._nodes[raw_node['id']] = node
                    updated_nodes.append(node)
                    logger.debug('Created node: %s', raw_node['id'])

        for node in updated_nodes:
            logger.debug('Attached node: %s to %s',
                node.id if node else None,
                node.parent_id if node else None
            )
            parent_node = self._nodes.get(node.parent_id)
            parent_node.append(node, False)

        for node in deleted_nodes:
            node.parent.remove(node)
            del self._nodes[node.id]
            logger.debug('Deleted node: %s', node.id)

        for node in self.all():
            for label_id in node.labels._labels:
                node.labels._labels[label_id] = self._labels.get(label_id)

    def _parseUserInfo(self, raw):
        labels = {}
        if 'labels' in raw:
            for label in raw['labels']:
                if label['mainId'] in self._labels:
                    node = self._labels[label['mainId']]
                    del self._labels[label['mainId']]
                    logger.debug('Updated label: %s', label['mainId'])
                else:
                    node = _node.Label()
                    logger.debug('Created label: %s', label['mainId'])
                node.load(label)
                labels[label['mainId']] = node

        for label_id in self._labels:
            logger.debug('Deleted label: %s', label_id)

        self._labels = labels

    def _findDirtyNodes(self):
        for node in list(self._nodes.values()):
            for child in node.children:
                if not child.id in self._nodes:
                    self._nodes[child.id] = child

        nodes = []
        for node in self._nodes.values():
            if node.dirty:
                nodes.append(node)

        return nodes

    def _clean(self):
        """Recursively check that all nodes are reachable."""
        found_ids = {}
        nodes = [self._nodes[_node.Root.ID]]
        while nodes:
            node = nodes.pop()
            found_ids[node.id] = None
            nodes = nodes + node.children

        for node_id in self._nodes:
            if node_id in found_ids:
                continue
            logger.info('Dangling node: %s', node_id)

        for node_id in found_ids:
            if node_id in self._nodes:
                continue
            logger.info('Unregistered node: %s', node_id)
