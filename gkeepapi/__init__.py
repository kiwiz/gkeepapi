# -*- coding: utf-8 -*-
"""
.. moduleauthor:: Kai <z@kwi.li>
"""

__version__ = '0.11.2'

import logging
import re
import time
import random

from uuid import getnode as get_mac

import six
import gpsoauth
import requests

from . import node as _node
from . import exception

logger = logging.getLogger('keep')

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
            raise exception.LoginException(res.get('Error'), res.get('ErrorDetail'))
        self._master_token = res['Token']

        self.refresh()
        return True

    def load(self, email, master_token, android_id):
        """Authenticate to Google with the provided master token.

        Args:
            email (str): The account to use.
            master_token (str): The master token.
            android_id (str): An identifier for this client.

        Raises:
            LoginException: If there was a problem logging in.
        """
        self._email = email
        self._android_id = android_id
        self._master_token = master_token

        self.refresh()
        return True

    def getMasterToken(self):
        """Gets the master token.

        Returns:
            str: The account master token.
        """
        return self._master_token

    def setMasterToken(self, master_token):
        """Sets the master token. This is useful if you'd like to authenticate
        with the API without providing your username & password.
        Do note that the master token has full access to your account.

        Args:
            master_token (str): The account master token.
        """
        self._master_token = master_token

    def getEmail(self):
        """Gets the account email.

        Returns:
            str: The account email.
        """
        return self._email

    def setEmail(self, email):
        """Gets the account email.

        Args:
            email (str): The account email.
        """
        self._email = email

    def getAndroidId(self):
        """Gets the device id.

        Returns:
            str: The device id.
        """
        return self._android_id

    def setAndroidId(self, android_id):
        """Sets the device id.

        Args:
            android_id (str): The device id.
        """
        self._android_id = android_id

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
                raise exception.LoginException(res.get('Error'))

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
        self._session.headers.update({'User-Agent': 'gkeepapi/' + __version__})

    def getAuth(self):
        """Get authentication details for this API.

        Args:
            auth (APIAuth): The auth object
        """
        return self._auth

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
            raise exception.LoginException('Not logged in')

        req_kwargs.setdefault('headers', {})

        i = 0
        while True:
            req_kwargs['headers']['Authorization'] = 'OAuth ' + auth_token

            response = self._session.request(**req_kwargs).json()
            if 'error' not in response:
                break

            error = response['error']
            if error['code'] != 401:
                raise exception.APIException(error['code'], error)

            if i >= self.RETRY_CNT:
                raise exception.APIException(error['code'], error)

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
                    {'type': 'IN'}, # Indentation support (Send listitem parent)

                    {'type': 'SNB'}, # Allows modification of shared notes?
                    {'type': 'MI'}, # Concise blob info?
                    {'type': 'CO'}, # VSS_SUCCEEDED when off?

                    # TODO: Figure out what these do:
                    # {'type': 'EC'}, # ???
                    # {'type': 'RB'}, # Rollback?
                    # {'type': 'EX'}, # ???
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
        self.static_params = {
            "taskList": [
                {"systemListId": "MEMENTO"},
            ],
            "requestParameters": {
                "userAgentStructured": {
                    "clientApplication": "KEEP",
                    "clientApplicationVersion": {
                        "major": "9", "minor": "9.9.9.9",
                    },
                    "clientPlatform": "ANDROID",
                },
            },
        }

    def create(self):
        """Create a new reminder.
        """
        params = {}
        return self.send(
            url=self._base_url + 'create',
            method='POST',
            json=params
        )

    def list(self, master=True):
        """List current reminders.
        """
        params = {}
        params.update(self.static_params)

        if master:
            params.update({
                "recurrenceOptions": {
                    "collapseMode": "MASTER_ONLY",
                },
                "includeArchived": True,
                "includeDeleted": False,
            })
        else:
            current_time = time.time()
            start_time = int((current_time - (365 * 24 * 60 * 60)) * 1000)
            end_time = int((current_time + (24 * 60 * 60)) * 1000)

            params.update({
                "recurrenceOptions": {
                    "collapseMode":"INSTANCES_ONLY",
                    "recurrencesOnly": True,
                },
                "includeArchived": False,
                "includeCompleted": False,
                "includeDeleted": False,
                "dueAfterMs": start_time,
                "dueBeforeMs": end_time,
                "recurrenceId": [],
            })

        return self.send(
            url=self._base_url + 'list',
            method='POST',
            json=params
        )

    def history(self, storage_version):
        """Get reminder changes.
        """
        params = {
            "storageVersion": storage_version,
            "includeSnoozePresetUpdates": True,
        }
        params.update(self.static_params)

        return self.send(
            url=self._base_url + 'history',
            method='POST',
            json=params
        )

    def update(self):
        """Sync up changes to reminders.
        """
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
    OAUTH_SCOPES = 'oauth2:https://www.googleapis.com/auth/memento https://www.googleapis.com/auth/reminders'

    def __init__(self):
        self._keep_api = KeepAPI()
        self._reminders_api = RemindersAPI()
        self._keep_version = None
        self._reminder_version = None
        self._labels = {}
        self._nodes = {}

        self._clear()

    def _clear(self):
        self._keep_version = None
        self._reminder_version = None
        self._labels = {}
        self._nodes = {}

        root_node = _node.Root()
        self._nodes[_node.Root.ID] = root_node

    def login(self, username, password, state=None, sync=True):
        """Authenticate to Google with the provided credentials & sync.

        Args:
            email (str): The account to use.
            password (str): The account password.
            state (dict): Serialized state to load.

        Raises:
            LoginException: If there was a problem logging in.
        """
        auth = APIAuth(self.OAUTH_SCOPES)

        ret = auth.login(username, password, get_mac())
        if ret:
            self.load(auth, state, sync)

        return ret

    def resume(self, email, master_token, state=None, sync=True):
        """Authenticate to Google with the provided master token & sync.

        Args:
            email (str): The account to use.
            master_token (str): The master token.
            state (dict): Serialized state to load.

        Raises:
            LoginException: If there was a problem logging in.
        """
        auth = APIAuth(self.OAUTH_SCOPES)

        ret = auth.load(email, master_token, android_id=get_mac())
        if ret:
            self.load(auth, state, sync)

        return ret

    def getMasterToken(self):
        """Get master token for resuming.

        Returns:
            str: The master token.
        """
        return self._keep_api.getAuth().getMasterToken()

    def load(self, auth, state=None, sync=True):
        """Authenticate to Google with a prepared authentication object & sync.
        Args:
            auth (APIAuth): Authentication object.
            state (dict): Serialized state to load.

        Raises:
            LoginException: If there was a problem logging in.
        """
        self._keep_api.setAuth(auth)
        self._reminders_api.setAuth(auth)
        if state is not None:
            self.restore(state)
        if sync:
            self.sync(True)

    def dump(self):
        """Serialize note data.

        Args:
            state (dict): Serialized state to load.
        """
        # Find all nodes manually, as the Keep object isn't aware of new ListItems
        # until they've been synced to the server.
        nodes = []
        for node in self.all():
            nodes.append(node)
            for child in node.children:
                nodes.append(child)
        return {
            'keep_version': self._keep_version,
            'labels': [label.save(False) for label in self.labels()],
            'nodes': [node.save(False) for node in nodes]
        }

    def restore(self, state):
        """Unserialize saved note data.

        Args:
            state (dict): Serialized state to load.
        """
        self._clear()
        self._parseUserInfo({'labels': state['labels']})
        self._parseNodes(state['nodes'])
        self._keep_version = state['keep_version']

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
            raise exception.SyncException('Not a top level node')

        self._nodes[node.id] = node
        self._nodes[node.parent_id].append(node, False)

    def find(self, query=None, func=None, labels=None, colors=None, pinned=None, archived=None, trashed=False): # pylint: disable=too-many-arguments
        """Find Notes based on the specified criteria.

        Args:
            query (Union[_sre.SRE_Pattern, str, None]): A str or regular expression to match against the title and text.
            func (Union[callable, None]): A filter function.
            labels (Union[List[str], None]): A list of label ids or objects to match. An empty list matches notes with no labels.
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
            (labels is None or \
             (not labels and not node.labels.all()) or \
             (any((node.labels.get(i) is not None for i in labels)))
            ) and \
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
        if self.findLabel(name):
            raise exception.LabelException('Label exists')
        node = _node.Label()
        node.name = name
        self._labels[node.id] = node # pylint: disable=protected-access
        return node

    def findLabel(self, query, create=False):
        """Find a label with the given name.

        Args:
            name (Union[_sre.SRE_Pattern, str]): A str or regular expression to match against the name.
            create (bool): Whether to create the label if it doesn't exist (only if name is a str).

        Returns:
            Union[gkeepapi.node.Label, None]: The label.
        """
        if isinstance(query, six.string_types):
            query = query.lower()

        for label in self._labels.values():
            if (isinstance(query, six.string_types) and query == label.name.lower()) or \
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
        return self._labels.values()

    def all(self):
        """Get all Notes.

        Returns:
            List[gkeepapi.node.TopLevelNode]: Notes
        """
        return self._nodes[_node.Root.ID].children

    def sync(self, resync=False):
        """Sync the local Keep tree with the server. If resyncing, local changes will be detroyed. Otherwise, local changes to notes, labels and reminders will be detected and synced up.

        Args:
            resync (bool): Whether to resync data.

        Raises:
            SyncException: If there is a consistency issue.
        """
        if resync:
            self._clear()

        while True:
            logger.debug('Starting reminder sync: %s', self._reminder_version)
            changes = self._reminders_api.list()

            if 'task' in changes:
                self._parseTasks(changes['task'])

            self._reminder_version = changes['storageVersion']
            logger.debug('Finishing sync: %s', self._reminder_version)
            history = self._reminders_api.history(self._reminder_version)
            if self._reminder_version == history['highestStorageVersion']:
                break

        while True:
            logger.debug('Starting keep sync: %s', self._keep_version)

            labels_updated = any((i.dirty for i in self._labels.values()))
            changes = self._keep_api.changes(
                target_version=self._keep_version,
                nodes=[i.save() for i in self._findDirtyNodes()],
                labels=[i.save() for i in self._labels.values()] if labels_updated else None,
            )

            if changes.get('forceFullResync'):
                raise exception.SyncException('Full resync required')

            if changes.get('upgradeRecommended'):
                raise exception.SyncException('Upgrade recommended')

            if 'userInfo' in changes:
                self._parseUserInfo(changes['userInfo'])

            if 'nodes' in changes:
                self._parseNodes(changes['nodes'])

            self._keep_version = changes['toVersion']
            logger.debug('Finishing sync: %s', self._keep_version)
            if not changes['truncated']:
                break

        if _node.DEBUG:
            self._clean()

    def _parseTasks(self, raw):
        pass

    def _parseNodes(self, raw): # pylint: disable=too-many-branches
        created_nodes = []
        deleted_nodes = []
        listitem_nodes = []
        for raw_node in raw:
            # Update nodes
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
                    created_nodes.append(node)
                    logger.debug('Created node: %s', raw_node['id'])

            if isinstance(node, _node.ListItem):
                listitem_nodes.append(node)

        # Attach list subitems
        for node in listitem_nodes:
            prev = node.prev_super_list_item_id
            curr = node.super_list_item_id
            if prev == curr:
                continue

            if prev is not None:
                self._nodes[prev].dedent(node, False)

            if curr is not None:
                self._nodes[curr].indent(node, False)

        # Attach created nodes to the tree
        for node in created_nodes:
            logger.debug('Attached node: %s to %s',
                node.id if node else None,
                node.parent_id if node else None
            )
            parent_node = self._nodes.get(node.parent_id)
            parent_node.append(node, False)

        # Detach deleted nodes from the tree
        for node in deleted_nodes:
            node.parent.remove(node)
            del self._nodes[node.id]
            logger.debug('Deleted node: %s', node.id)

        for node in self.all():
            for label_id in node.labels._labels: # pylint: disable=protected-access
                node.labels._labels[label_id] = self._labels.get(label_id) # pylint: disable=protected-access

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
            logger.error('Dangling node: %s', node_id)

        for node_id in found_ids:
            if node_id in self._nodes:
                continue
            logger.error('Unregistered node: %s', node_id)
