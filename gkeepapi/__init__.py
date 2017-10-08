# -*- coding: utf-8 -*-
"""
.. moduleauthor:: Kai <z@kwi.li>
"""

import logging

from uuid import getnode as get_mac

import gpsoauth
import requests

from . import node as _node

logger = logging.getLogger('keep')

class APIException(Exception):
    """The API server returned an error"""
    pass

class KeepException(Exception):
    """Generic Keep error"""

class API(object):
    """Low level Google Keep API client. Mimics the Android Google Keep app.

    You probably want to use :class:`Keep` instead.
    """
    API_URL = 'https://www.googleapis.com/notes/v1/'
    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({'User-Agent': 'gkeepapi/0.1'})
        self._auth_token = None

    def login(self, email, password, android_id):
        """Authenticate to Google with the provided credentials.

        Args:
            email (str): The account to use.
            password (str): The account password.
            android_id (str): An identifier for this client.

        Returns:
            bool: True if login was successful.
        """
        res = gpsoauth.perform_master_login(email, password, android_id)
        if 'Token' not in res:
            return False
        master_token = res['Token']

        res = gpsoauth.perform_oauth(
            email, master_token, android_id,
            service='memento', app='com.google.android.keep',
            client_sig='38918a453d07199354f8b19af05ec6562ced5788'
        )
        if 'Auth' not in res:
            return False

        self._auth_token = res['Auth']
        return True

    def send(self, **req_kwargs):
        """Send an authenticated request to the Google Keep API.

        Args:
            **req_kwargs: Arbitrary keyword arguments to pass to Requests.

        Return:
            dict: The parsed JSON response.

        Raises:
            APIException: If the server returns an error.
        """
        req_kwargs.setdefault('headers', {})

        # does this expire?
        req_kwargs['headers']['Authorization'] = 'OAuth ' + self._auth_token

        response = self._session.request(**req_kwargs).json()
        if 'error' in response:
            raise APIException(response['error'])

        return response

    def changes(self, target_version=None, nodes=None):
        """Sync up (and down) all changes.

        Args:
            target_version (str): The local change version.
            nodes (list[dict]): A list of nodes to sync up to the server.

        Return:
            dict: Description of all changes.

        Raises:
            APIException: If the server returns an error.
        """
        if nodes is None:
            nodes = []

        params = {
            'nodes': nodes,
            'requestHeader': {
                'capabilities': [
                    {'type': 'NC'}, # Color support
                    {'type': 'PI'}, # Pinned support
                    {'type': 'LB'}, # Labels support
                    {'type': 'AN'}, # Annotations support
                    {'type': 'SH'}, # Sharing support
                    {'type': 'DR'}, # Drawing support

                    # TODO: Figure out what these do:
                    # {'type': 'TR'}, # Hide delete time?
                    # {'type': 'CO'}, # VSS_SUCCEEDED when off?
                    # {'type': 'EC'}, # ???
                    # {'type': 'RB'}, # ???
                    # {'type': 'EX'}, # ???
                    # {'type': 'MI'}, # ???
                ]
            },
        }
        if target_version is not None:
            params['targetVersion'] = target_version

        return self.send(
            url=self.API_URL + 'changes',
            method='POST',
            json=params
        )

class Keep(object):
    """High level Google Keep client.

    Stores a local copy of the Keep node tree. To start, first login and sync Notes::

        keep.login('...', '...')
        keep.sync()

    Individual Notes can be retrieved by id::

        note = keep.get('some_id')

    These Notes can be modified and synced up to the server::

        note.text = 'Test'
        keep.update(note)
        keep.sync()
    """
    TZ_FMT = '%Y-%m-%dT%H:%M:%S.%fZ'
    def __init__(self):
        self._api = API()
        self._version = None
        self._dirty = []
        self._labels = {}

        self._nodes = {}
        root_node = _node.Root()
        self._nodes[_node.Root.ID] = root_node

    def login(self, username, password):
        """Authenticate to Google with the provided credentials.

        Args:
            email (str): The account to use.
            password (str): The account password.

        Returns:
            bool: True if login was successful.
        """
        return self._api.login(username, password, get_mac())

    def get(self, node_id):
        """Get a note with the given ID.

        Args:
            node_id (str): The note ID.

        Returns:
            gkeepapi.node.XNode: The Note or None if not found.
        """
        return self._nodes[_node.Root.ID].get(node_id)

    def update(self, node):
        """Register a node (and its children) for syncing up to the server.

        Args:
            node (gkeepapi.node.Node): The node to sync.
        """
        if node.parent_id not in self._nodes:
            raise KeepException('Parent node not found')

        self._nodes[node.id] = node
        self._nodes[node.parent_id].append(node)
        self._dirty.append(node)
        for child_node in node.children:
            if child_node.new or child_node.dirty:
                self.update(child_node)

    def find(self, rexp=None, labels=None, colors=None):
        """Find Notes based on the specified criteria.

        Args:
            rexp (_sre.SRE_Pattern): A regular expression to match.
            labels (list[str]): A list of labels to match.
            colors (list[str]): A list of colors to match.

        Return:
            list[gkeepapi.node.XNode]: Results.
        """
        # FIXME: Handle labels
        return (node for node in self.all() if
            (rexp is None or (rexp.search(node.title) or rexp.search(node.text))) and
            (colors is None or node.color in colors)
        )

    def labels(self):
        """Get all labels.

        Returns:
            list[str]: Labels
        """
        return self._labels.keys()

    def all(self):
        """Get all Notes.

        Returns:
            list[gkeepapi.node.XNode]: Notes
        """
        return self._nodes[_node.Root.ID].children

    def sync(self):
        """Sync the local Keep tree with the server.
        """
        while True:
            logger.debug('Starting sync: %s', self._version)
            changes = self._api.changes(
                target_version=self._version,
                nodes=[i.save() for i in self._dirty]
            )
            self._dirty = []
            if changes.get('forceFullResync'):
                raise KeepException('Full resync required')

            if 'userInfo' in changes:
                self._parseUserInfo(changes['userInfo'])

            if 'nodes' in changes:
                self._parseNodes(changes['nodes'])

            self._version = changes['toVersion']
            logger.debug('Finishing sync: %s', self._version)
            if not changes['truncated']:
                break

        self._clean()

    def _parseNodes(self, raw):
        updated_nodes = []
        deleted_nodes = []
        for raw_node in raw:
            if raw_node['id'] in self._nodes:
                node = self._nodes[raw_node['id']]

                if 'parentId' in raw_node:
                    node.load(raw_node)
                    # FIXME: Is this necessary?
                    # Does parentId ever change?
                    # What happens if you delete a list_item?
                    updated_nodes.append(node)
                    logger.debug('Updated node: %s', raw_node['id'])
                else:
                    deleted_nodes.append(node)

            else:
                node = _node.from_json(raw_node)
                self._nodes[raw_node['id']] = node
                updated_nodes.append(node)
                logger.debug('Created node: %s', raw_node['id'])

        for node in updated_nodes:
            logger.debug('Attached node: %s to %s',
                node.id if node else None,
                node.parent_id if node else None
            )
            parent_node = self._nodes.get(node.parent_id)
            parent_node.append(node)

        for node in deleted_nodes:
            del self._nodes[node.id]
            logger.debug('Deleted node: %s', node.id)

    def _parseUserInfo(self, raw):
        if 'labels' in raw['userInfo']:
            for label in raw['userInfo']['labels']:
                self._labels[label['name']] = label

    def _clean(self):
        """Recursively check that all nodes are reachable.
        """
        found_ids = {}
        nodes = [self._nodes[_node.Root.ID]]
        while len(nodes) > 0:
            node = nodes.pop()
            found_ids[node.id] = None
            nodes = nodes + node.children

        for node_id, _ in self._nodes:
            if node_id in found_ids:
                continue
            logger.info('Dangling node: %s', node_id)

        for node_id in found_ids:
            if node_id in self._nodes:
                continue
            logger.info('Unregistered node: %s', node_id)
