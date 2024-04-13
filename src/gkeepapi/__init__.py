""".. moduleauthor:: Kai <z@kwi.li>"""

__version__ = "0.16.0"

import datetime
import http
import logging
import random
import re
import time
from collections.abc import Callable, Iterator
from typing import IO, Any
from uuid import getnode as get_mac

import gpsoauth
import requests

from . import exception
from . import node as _node

logger = logging.getLogger(__name__)


class APIAuth:
    """Authentication token manager"""

    def __init__(self, scopes: str) -> None:
        """Construct API authentication manager"""
        self._master_token = None
        self._auth_token = None
        self._email = None
        self._device_id = None
        self._scopes = scopes

    def login(self, email: str, password: str, device_id: str) -> None:
        """Authenticate to Google with the provided credentials.

        Args:
            email: The account to use.
            password: The account password.
            device_id: An identifier for this client.

        Raises:
            LoginException: If there was a problem logging in.
        """
        self._email = email
        self._device_id = device_id

        # Obtain a master token.
        res = gpsoauth.perform_master_login(self._email, password, self._device_id)

        # Bail if browser login is required.
        if res.get("Error") == "NeedsBrowser":
            raise exception.BrowserLoginRequiredException(res.get("Url"))

        # Bail if no token was returned.
        if "Token" not in res:
            raise exception.LoginException(res.get("Error"), res.get("ErrorDetail"))

        self._master_token = res["Token"]

        # Obtain an OAuth token.
        self.refresh()

    def load(self, email: str, master_token: str, device_id: str) -> bool:
        """Authenticate to Google with the provided master token.

        Args:
            email: The account to use.
            master_token: The master token.
            device_id: An identifier for this client.

        Raises:
            LoginException: If there was a problem logging in.
        """
        self._email = email
        self._device_id = device_id
        self._master_token = master_token

        # Obtain an OAuth token.
        self.refresh()
        return True

    def getMasterToken(self) -> str:
        """Gets the master token.

        Returns:
            The account master token.
        """
        return self._master_token

    def setMasterToken(self, master_token: str) -> None:
        """Sets the master token. This is useful if you'd like to authenticate with the API without providing your username & password. Do note that the master token has full access to your account.

        Args:
            master_token: The account master token.
        """
        self._master_token = master_token

    def getEmail(self) -> str:
        """Gets the account email.

        Returns:
            The account email.
        """
        return self._email

    def setEmail(self, email: str) -> None:
        """Sets the account email.

        Args:
            email: The account email.
        """
        self._email = email

    def getDeviceId(self) -> str:
        """Gets the device id.

        Returns:
            The device id.
        """
        return self._device_id

    def setDeviceId(self, device_id: str) -> None:
        """Sets the device id.

        Args:
            device_id: The device id.
        """
        self._device_id = device_id

    def getAuthToken(self) -> str | None:
        """Gets the auth token.

        Returns:
            The auth token.
        """
        return self._auth_token

    def refresh(self) -> str:
        """Refresh the OAuth token.

        Returns:
            The auth token.

        Raises:
            LoginException: If there was a problem refreshing the OAuth token.
        """
        # Obtain an OAuth token with the necessary scopes by pretending to be
        # the keep android client.
        res = gpsoauth.perform_oauth(
            self._email,
            self._master_token,
            self._device_id,
            service=self._scopes,
            app="com.google.android.keep",
            client_sig="38918a453d07199354f8b19af05ec6562ced5788",
        )
        # Bail if no token was returned.
        if "Auth" not in res and "Token" not in res:
            raise exception.LoginException(res.get("Error"))

        self._auth_token = res["Auth"]
        return self._auth_token

    def logout(self) -> None:
        """Log out of the account."""
        self._master_token = None
        self._auth_token = None
        self._email = None
        self._device_id = None


class API:
    """Base API wrapper"""

    RETRY_CNT = 2

    def __init__(self, base_url: str, auth: APIAuth | None = None) -> None:
        """Construct a low-level API client"""
        self._session = requests.Session()
        self._auth = auth
        self._base_url = base_url
        self._session.headers.update(
            {
                "User-Agent": "x-gkeepapi/%s (https://github.com/kiwiz/gkeepapi)"
                % __version__
            }
        )

    def getAuth(self) -> APIAuth:
        """Get authentication details for this API.

        Return:
            auth: The auth object
        """
        return self._auth

    def setAuth(self, auth: APIAuth) -> None:
        """Set authentication details for this API.

        Args:
            auth: The auth object
        """
        self._auth = auth

    def send(self, **req_kwargs: dict) -> dict:
        """Send an authenticated request to a Google API. Automatically retries if the access token has expired.

        Args:
            **req_kwargs: Arbitrary keyword arguments to pass to Requests.

        Return:
            The parsed JSON response.

        Raises:
            APIException: If the server returns an error.
            LoginException: If session is not authenticated.
        """
        # Send a request to the API servers, with retry handling. OAuth tokens
        # are valid for several hours (as of this comment).
        i = 0
        while True:
            # Send off the request. If there was no error, we're good.
            response = self._send(**req_kwargs).json()
            if "error" not in response:
                break

            # Otherwise, check if it was a non-401 response code. These aren't
            # handled, so bail.
            error = response["error"]
            if error["code"] != http.HTTPStatus.UNAUTHORIZED:
                raise exception.APIException(error["code"], error)

            # If we've exceeded the retry limit, also bail.
            if i >= self.RETRY_CNT:
                raise exception.APIException(error["code"], error)

            # Otherwise, try requesting a new OAuth token.
            logger.info("Refreshing access token")
            self._auth.refresh()
            i += 1

        return response

    def _send(self, **req_kwargs: dict) -> requests.Response:
        """Send an authenticated request to a Google API.

        Args:
            **req_kwargs: Arbitrary keyword arguments to pass to Requests.

        Return:
            The raw response.

        Raises:
            LoginException: If session is not authenticated.
        """
        # Bail if we don't have an OAuth token.
        auth_token = self._auth.getAuthToken()
        if auth_token is None:
            raise exception.LoginException("Not logged in")

        # Add the token to the request.
        req_kwargs.setdefault("headers", {"Authorization": "OAuth " + auth_token})

        return self._session.request(**req_kwargs)


class KeepAPI(API):
    """Low level Google Keep API client. Mimics the Android Google Keep app.

    You probably want to use :py:class:`Keep` instead.
    """

    API_URL = "https://www.googleapis.com/notes/v1/"

    def __init__(self, auth: APIAuth | None = None) -> None:
        """Construct a low-level Google Keep API client"""
        super().__init__(self.API_URL, auth)

        create_time = time.time()
        self._session_id = self._generateId(create_time)

    @classmethod
    def _generateId(cls, tz: int) -> str:
        return "s--%d--%d" % (
            int(tz * 1000),
            random.randint(1000000000, 9999999999),  # noqa: S311
        )

    def changes(
        self,
        target_version: str | None = None,
        nodes: list[dict] | None = None,
        labels: list[dict] | None = None,
    ) -> dict:
        """Sync up (and down) all changes.

        Args:
            target_version: The local change version.
            nodes: A list of nodes to sync up to the server.
            labels: A list of labels to sync up to the server.

        Return:
            Description of all changes.

        Raises:
            APIException: If the server returns an error.
        """
        # Handle defaults.
        if nodes is None:
            nodes = []
        if labels is None:
            labels = []

        current_time = time.time()

        # Initialize request parameters.
        params = {
            "nodes": nodes,
            "clientTimestamp": _node.NodeTimestamps.int_to_str(current_time),
            "requestHeader": {
                "clientSessionId": self._session_id,
                "clientPlatform": "ANDROID",
                "clientVersion": {
                    "major": "9",
                    "minor": "9",
                    "build": "9",
                    "revision": "9",
                },
                "capabilities": [
                    {"type": "NC"},  # Color support (Send note color)
                    {"type": "PI"},  # Pinned support (Send note pinned)
                    {"type": "LB"},  # Labels support (Send note labels)
                    {"type": "AN"},  # Annotations support (Send annotations)
                    {"type": "SH"},  # Sharing support
                    {"type": "DR"},  # Drawing support
                    {"type": "TR"},  # Trash support (Stop setting the delete timestamp)
                    {"type": "IN"},  # Indentation support (Send listitem parent)
                    {"type": "SNB"},  # Allows modification of shared notes?
                    {"type": "MI"},  # Concise blob info?
                    {"type": "CO"},  # VSS_SUCCEEDED when off?
                    # TODO: Figure out what these do:
                    # {'type': 'EC'}, # ???
                    # {'type': 'RB'}, # Rollback?
                    # {'type': 'EX'}, # ???
                ],
            },
        }

        # Add the targetVersion if set. This tells the server what version the
        # client is currently at.
        if target_version is not None:
            params["targetVersion"] = target_version

        # Add any new or updated labels to the request.
        if labels:
            params["userInfo"] = {"labels": labels}

        logger.debug("Syncing %d labels and %d nodes", len(labels), len(nodes))

        return self.send(url=self._base_url + "changes", method="POST", json=params)


class MediaAPI(API):
    """Low level Google Media API client. Mimics the Android Google Keep app.

    You probably want to use :py:class:`Keep` instead.
    """

    API_URL = "https://keep.google.com/media/v2/"

    def __init__(self, auth: APIAuth | None = None) -> None:
        """Construct a low-level Google Media API client"""
        super().__init__(self.API_URL, auth)

    def get(self, blob: _node.Blob) -> str:
        """Get the canonical link to a media blob.

        Args:
            blob: The blob.

        Returns:
            A link to the media.
        """
        url = self._base_url + blob.parent.server_id + "/" + blob.server_id
        if blob.blob.type == _node.BlobType.Drawing:
            url += "/" + blob.blob._drawing_info.drawing_id  # noqa: SLF001
        return self._send(url=url, method="GET", allow_redirects=False).headers[
            "location"
        ]


class RemindersAPI(API):
    """Low level Google Reminders API client. Mimics the Android Google Keep app.

    You probably want to use :py:class:`Keep` instead.
    """

    API_URL = "https://www.googleapis.com/reminders/v1internal/reminders/"

    def __init__(self, auth: APIAuth | None = None) -> None:
        """Construct a low-level Google Reminders API client"""
        super().__init__(self.API_URL, auth)
        self.static_params = {
            "taskList": [
                {"systemListId": "MEMENTO"},
            ],
            "requestParameters": {
                "userAgentStructured": {
                    "clientApplication": "KEEP",
                    "clientApplicationVersion": {
                        "major": "9",
                        "minor": "9.9.9.9",
                    },
                    "clientPlatform": "ANDROID",
                },
            },
        }

    def create(
        self, node_id: str, node_server_id: str, dtime: datetime.datetime
    ) -> Any:  # noqa: ANN401
        """Create a new reminder.

        Args:
            node_id: The note ID.
            node_server_id: The note server ID.
            dtime: The due date of this reminder.

        Return: ???

        Raises:
            APIException: If the server returns an error.
        """
        params = {}
        params.update(self.static_params)

        params.update(
            {
                "task": {
                    "dueDate": {
                        "year": dtime.year,
                        "month": dtime.month,
                        "day": dtime.day,
                        "time": {
                            "hour": dtime.hour,
                            "minute": dtime.minute,
                            "second": dtime.second,
                        },
                    },
                    "snoozed": True,
                    "extensions": {
                        "keepExtension": {
                            "reminderVersion": "V2",
                            "clientNoteId": node_id,
                            "serverNoteId": node_server_id,
                        },
                    },
                },
                "taskId": {
                    "clientAssignedId": "KEEP/v2/" + node_server_id,
                },
            }
        )

        return self.send(url=self._base_url + "create", method="POST", json=params)

    def update_internal(
        self, node_id: str, node_server_id: str, dtime: datetime.datetime
    ) -> Any:  # noqa: ANN401
        """Update an existing reminder.

        Args:
            node_id: The note ID.
            node_server_id: The note server ID.
            dtime: The due date of this reminder.

        Return: ???

        Raises:
            APIException: If the server returns an error.
        """
        params = {}
        params.update(self.static_params)

        params.update(
            {
                "newTask": {
                    "dueDate": {
                        "year": dtime.year,
                        "month": dtime.month,
                        "day": dtime.day,
                        "time": {
                            "hour": dtime.hour,
                            "minute": dtime.minute,
                            "second": dtime.second,
                        },
                    },
                    "snoozed": True,
                    "extensions": {
                        "keepExtension": {
                            "reminderVersion": "V2",
                            "clientNoteId": node_id,
                            "serverNoteId": node_server_id,
                        },
                    },
                },
                "taskId": {
                    "clientAssignedId": "KEEP/v2/" + node_server_id,
                },
                "updateMask": {
                    "updateField": [
                        "ARCHIVED",
                        "DUE_DATE",
                        "EXTENSIONS",
                        "LOCATION",
                        "TITLE",
                    ]
                },
            }
        )

        return self.send(url=self._base_url + "update", method="POST", json=params)

    def delete(self, node_server_id: str) -> Any:  # noqa: ANN401
        """Delete an existing reminder.

        Args:
            node_server_id: The note server ID.

        Return: ???

        Raises:
            APIException: If the server returns an error.
        """
        params = {}
        params.update(self.static_params)

        params.update(
            {
                "batchedRequest": [
                    {
                        "deleteTask": {
                            "taskId": [
                                {"clientAssignedId": "KEEP/v2/" + node_server_id}
                            ]
                        }
                    }
                ]
            }
        )

        return self.send(url=self._base_url + "batchmutate", method="POST", json=params)

    def list(self, master: bool = True) -> Any:  # noqa: ANN401
        """List current reminders.

        Args:
            master: ???

        Return:
            ???

        Raises:
            APIException: If the server returns an error.
        """
        params = {}
        params.update(self.static_params)

        if master:
            params.update(
                {
                    "recurrenceOptions": {
                        "collapseMode": "MASTER_ONLY",
                    },
                    "includeArchived": True,
                    "includeDeleted": False,
                }
            )
        else:
            current_time = time.time()
            start_time = int((current_time - (365 * 24 * 60 * 60)) * 1000)
            end_time = int((current_time + (24 * 60 * 60)) * 1000)

            params.update(
                {
                    "recurrenceOptions": {
                        "collapseMode": "INSTANCES_ONLY",
                        "recurrencesOnly": True,
                    },
                    "includeArchived": False,
                    "includeCompleted": False,
                    "includeDeleted": False,
                    "dueAfterMs": start_time,
                    "dueBeforeMs": end_time,
                    "recurrenceId": [],
                }
            )

        return self.send(url=self._base_url + "list", method="POST", json=params)

    def history(self, storage_version: str) -> Any:  # noqa: ANN401
        """Get reminder changes.

        Args:
            storage_version: The local storage version.

        Returns:
            ???

        Raises:
            APIException: If the server returns an error.
        """
        params = {
            "storageVersion": storage_version,
            "includeSnoozePresetUpdates": True,
        }
        params.update(self.static_params)

        return self.send(url=self._base_url + "history", method="POST", json=params)

    def update(self) -> Any:  # noqa: ANN401
        """Sync up changes to reminders."""
        params = {}
        return self.send(url=self._base_url + "update", method="POST", json=params)


class Keep:
    """High level Google Keep client.

    Manipulates a local copy of the Keep node tree. First, obtain a master token for your account.

    To start, first authenticate::

        keep.authenticate('...', '...')

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

    OAUTH_SCOPES = "oauth2:https://www.googleapis.com/auth/memento https://www.googleapis.com/auth/reminders"

    def __init__(self) -> None:
        """Construct a Google Keep client"""
        self._keep_api = KeepAPI()
        self._reminders_api = RemindersAPI()
        self._media_api = MediaAPI()
        self._keep_version = None
        self._reminder_version = None
        self._labels = {}
        self._nodes = {}
        self._sid_map = {}

        self._clear()

    def _clear(self) -> None:
        self._keep_version = None
        self._reminder_version = None
        self._labels = {}
        self._nodes = {}
        self._sid_map = {}

        root_node = _node.Root()
        self._nodes[_node.Root.ID] = root_node

    def login(
        self,
        email: str,
        password: str,
        state: dict | None = None,
        sync: bool = True,
        device_id: str | None = None,
    ) -> None:
        """Authenticate to Google with the provided credentials & sync.

        This flow is discouraged.

        Args:
            email: The account to use.
            password: The account password.
            state: Serialized state to load.
            sync: Whether to sync data.
            device_id: Device id.

        Raises:
            LoginException: If there was a problem logging in.
        """
        logger.warning("'Keep.login' is deprecated. Please use 'Keep.authenticate' instead")
        auth = APIAuth(self.OAUTH_SCOPES)
        if device_id is None:
            device_id = f"{get_mac():x}"

        auth.login(email, password, device_id)
        self.load(auth, state, sync)

    def resume(
        self,
        email: str,
        master_token: str,
        state: dict | None = None,
        sync: bool = True,
        device_id: str | None = None,
    ) -> None:
        logger.warning("'Keep.resume' has been renamed to 'Keep.authenticate'. Please update your code")
        self.authenticate(email, master_token, state, sync, device_id)

    def authenticate(
        self,
        email: str,
        master_token: str,
        state: dict | None = None,
        sync: bool = True,
        device_id: str | None = None,
    ) -> None:
        """Authenticate to Google with the provided master token & sync.

        Args:
            email: The account to use.
            master_token: The master token.
            state: Serialized state to load.
            sync: Whether to sync data.
            device_id: Device id.

        Raises:
            LoginException: If there was a problem logging in.
        """
        auth = APIAuth(self.OAUTH_SCOPES)
        if device_id is None:
            device_id = f"{get_mac():x}"

        auth.load(email, master_token, device_id)
        self.load(auth, state, sync)

    def getMasterToken(self) -> str:
        """Get master token for resuming.

        Returns:
            The master token.
        """
        return self._keep_api.getAuth().getMasterToken()

    def load(self, auth: APIAuth, state: dict | None = None, sync: bool = True) -> None:
        """Authenticate to Google with a prepared authentication object & sync.

        Args:
            auth: Authentication object.
            state: Serialized state to load.
            sync: Whether to sync data.

        Raises:
            LoginException: If there was a problem logging in.
        """
        self._keep_api.setAuth(auth)
        self._reminders_api.setAuth(auth)
        self._media_api.setAuth(auth)
        if state is not None:
            self.restore(state)
        if sync:
            self.sync()

    def dump(self) -> dict:
        """Serialize note data.

        Returns:
            Serialized state.
        """
        # Find all nodes manually, as the Keep object isn't aware of new
        # ListItems until they've been synced to the server.
        nodes = []
        for node in self.all():
            nodes.append(node)
            nodes.extend(node.children)
        return {
            "keep_version": self._keep_version,
            "labels": [label.save(False) for label in self.labels()],
            "nodes": [node.save(False) for node in nodes],
        }

    def restore(self, state: dict) -> None:
        """Unserialize saved note data.

        Args:
            state: Serialized state to load.
        """
        self._clear()
        self._parseUserInfo({"labels": state["labels"]})
        self._parseNodes(state["nodes"])
        self._keep_version = state["keep_version"]

    def get(self, node_id: str) -> _node.TopLevelNode:
        """Get a note with the given ID.

        Args:
            node_id: The note ID.

        Returns:
            The Note or None if not found.
        """
        return self._nodes[_node.Root.ID].get(node_id) or self._nodes[
            _node.Root.ID
        ].get(self._sid_map.get(node_id))

    def add(self, node: _node.Node) -> None:
        """Register a top level node (and its children) for syncing up to the server. There's no need to call this for nodes created by :py:meth:`createNote` or :py:meth:`createList` as they are automatically added.

        Args:
            node: The node to sync.

        Raises:
            InvalidException: If the parent node is not found.
        """
        if node.parent_id != _node.Root.ID:
            raise exception.InvalidException("Not a top level node")

        self._nodes[node.id] = node
        self._nodes[node.parent_id].append(node, False)

    def find(
        self,
        query: re.Pattern | str | None = None,
        func: Callable | None = None,
        labels: list[str] | None = None,
        colors: list[str] | None = None,
        pinned: bool | None = None,
        archived: bool | None = None,
        trashed: bool = False,
    ) -> Iterator[_node.TopLevelNode]:
        """Find Notes based on the specified criteria.

        Args:
            query: A str or regular expression to match against the title and text.
            func: A filter function.
            labels: A list of label ids or objects to match. An empty list matches notes with no labels.
            colors: A list of colors to match.
            pinned: Whether to match pinned notes.
            archived: Whether to match archived notes.
            trashed: Whether to match trashed notes.

        Return:
            Search results.
        """
        if labels is not None:
            labels = [i.id if isinstance(i, _node.Label) else i for i in labels]

        return (
            node
            for node in self.all()
            if
            # Process the query.
            (
                query is None
                or (
                    (
                        isinstance(query, str)
                        and (query in node.title or query in node.text)
                    )
                    or (
                        isinstance(query, re.Pattern)
                        and (query.search(node.title) or query.search(node.text))
                    )
                )
            )
            and
            # Process the func.
            (func is None or func(node))
            and (  # Process the labels.
                labels is None
                or (not labels and not node.labels.all())
                or (any(node.labels.get(i) is not None for i in labels))
            )
            and (colors is None or node.color in colors)  # Process the colors.
            and (pinned is None or node.pinned == pinned)  # Process the pinned state.
            and (  # Process the archive state.
                archived is None or node.archived == archived
            )
            and (trashed is None or node.trashed == trashed)  # Process the trash state.
        )

    def createNote(
        self, title: str | None = None, text: str | None = None
    ) -> _node.Node:
        """Create a new managed note. Any changes to the note will be uploaded when :py:meth:`sync` is called.

        Args:
            title: The title of the note.
            text: The text of the note.

        Returns:
            The new note.
        """
        node = _node.Note()
        if title is not None:
            node.title = title
        if text is not None:
            node.text = text
        self.add(node)
        return node

    def createList(
        self,
        title: str | None = None,
        items: list[tuple[str, bool]] | None = None,
    ) -> _node.List:
        """Create a new list and populate it. Any changes to the note will be uploaded when :py:meth:`sync` is called.

        Args:
            title: The title of the list.
            items: A list of tuples. Each tuple represents the text and checked status of the listitem.

        Returns:
            The new list.
        """
        if items is None:
            items = []

        node = _node.List()
        if title is not None:
            node.title = title

        sort = random.randint(1000000000, 9999999999)  # noqa: S311
        for text, checked in items:
            node.add(text, checked, sort)
            sort -= _node.List.SORT_DELTA
        self.add(node)
        return node

    def createLabel(self, name: str) -> _node.Label:
        """Create a new label.

        Args:
            name: Label name.

        Returns:
            The new label.

        Raises:
            LabelException: If the label exists.
        """
        if self.findLabel(name):
            raise exception.LabelException("Label exists")
        node = _node.Label()
        node.name = name
        self._labels[node.id] = node
        return node

    def findLabel(
        self, query: re.Pattern | str, create: bool = False
    ) -> _node.Label | None:
        """Find a label with the given name.

        Args:
            query: A str or regular expression to match against the name.
            create: Whether to create the label if it doesn't exist (only if name is a str).

        Returns:
            The label.
        """
        is_str = isinstance(query, str)
        name = None
        if is_str:
            name = query
            query = query.lower()

        for label in self._labels.values():
            # Match the label against query, which may be a str or Pattern.
            if (is_str and query == label.name.lower()) or (
                isinstance(query, re.Pattern) and query.search(label.name)
            ):
                return label

        return self.createLabel(name) if create and is_str else None

    def getLabel(self, label_id: str) -> _node.Label | None:
        """Get an existing label.

        Args:
            label_id: Label id.

        Returns:
            The label.
        """
        return self._labels.get(label_id)

    def deleteLabel(self, label_id: str) -> None:
        """Deletes a label.

        Args:
            label_id: Label id.
        """
        if label_id not in self._labels:
            return

        label = self._labels[label_id]
        label.delete()
        for node in self.all():
            node.labels.remove(label)

    def labels(self) -> list[_node.Label]:
        """Get all labels.

        Returns:
            Labels
        """
        return list(self._labels.values())

    def __UNSTABLE_API_uploadMedia(self, fh: IO)-> None:
        pass

    def getMediaLink(self, blob: _node.Blob) -> str:
        """Get the canonical link to media.

        Args:
            blob: The media resource.

        Returns:
            A link to the media.
        """
        return self._media_api.get(blob)

    def all(self) -> list[_node.TopLevelNode]:
        """Get all Notes.

        Returns:
            All notes.
        """
        return self._nodes[_node.Root.ID].children

    def sync(self, resync: bool = False) -> None:
        """Sync the local Keep tree with the server. If resyncing, local changes will be destroyed. Otherwise, local changes to notes, labels and reminders will be detected and synced up.

        Args:
            resync: Whether to resync data.

        Raises:
            SyncException: If there is a consistency issue.
        """
        # Clear all state if we want to resync.
        if resync:
            self._clear()

        # self._sync_reminders()
        self._sync_notes()

        if _node.DEBUG:
            self._clean()

    def _sync_reminders(self) -> None:
        # Fetch updates until we reach the newest version.
        while True:
            logger.debug("Starting reminder sync: %s", self._reminder_version)
            changes = self._reminders_api.list()

            # Hydrate the individual "tasks".
            if "task" in changes:
                self._parseTasks(changes["task"])

            self._reminder_version = changes["storageVersion"]
            logger.debug("Finishing sync: %s", self._reminder_version)

            # Check if we've reached the newest version.
            history = self._reminders_api.history(self._reminder_version)
            if self._reminder_version == history["highestStorageVersion"]:
                break

    def _sync_notes(self) -> None:
        # Fetch updates until we reach the newest version.
        while True:
            logger.debug("Starting keep sync: %s", self._keep_version)

            # Collect any changes and send them up to the server.
            labels_updated = any(i.dirty for i in self._labels.values())
            changes = self._keep_api.changes(
                target_version=self._keep_version,
                nodes=[i.save() for i in self._findDirtyNodes()],
                labels=[i.save() for i in self._labels.values()]
                if labels_updated
                else None,
            )

            if changes.get("forceFullResync"):
                raise exception.ResyncRequiredException("Full resync required")

            if changes.get("upgradeRecommended"):
                raise exception.UpgradeRecommendedException("Upgrade recommended")

            # Hydrate labels.
            if "userInfo" in changes:
                self._parseUserInfo(changes["userInfo"])

            # Hydrate notes and any children.
            if "nodes" in changes:
                self._parseNodes(changes["nodes"])

            self._keep_version = changes["toVersion"]
            logger.debug("Finishing sync: %s", self._keep_version)

            # Check if there are more changes to retrieve.
            if not changes["truncated"]:
                break

    def _parseTasks(self, raw: dict) -> None:
        pass

    def _parseNodes(self, raw: dict) -> None:  # noqa: C901, PLR0912
        created_nodes = []
        deleted_nodes = []
        listitem_nodes = []

        # Loop over each updated node.
        for raw_node in raw:
            # If the id exists, then we already know about it. In other words,
            # update a local node.
            if raw_node["id"] in self._nodes:
                node = self._nodes[raw_node["id"]]

                if "parentId" in raw_node:
                    # If the parentId field is set, this is an update. Load it
                    # into the existing node.
                    node.load(raw_node)
                    self._sid_map[node.server_id] = node.id
                    logger.debug("Updated node: %s", raw_node["id"])
                else:
                    # Otherwise, this node has been deleted. Add it to the list.
                    deleted_nodes.append(node)

            else:
                # Otherwise, this is a new node. Attempt to hydrate it.
                node = _node.from_json(raw_node)
                if node is None:
                    logger.debug("Discarded unknown node")
                else:
                    # Append the new node into the node tree.
                    self._nodes[raw_node["id"]] = node
                    self._sid_map[node.server_id] = node.id
                    created_nodes.append(node)
                    logger.debug("Created node: %s", raw_node["id"])

            # If the node is a listitem, keep track of it.
            if isinstance(node, _node.ListItem):
                listitem_nodes.append(node)

        # Attach each listitem to its parent list. Indented items point to their
        # parent listitem, so we need to traverse up until we reach the list.
        for node in listitem_nodes:
            prev = node.prev_super_list_item_id
            curr = node.super_list_item_id
            if prev == curr:
                continue

            # Apply proper indentation.
            if prev is not None and prev in self._nodes:
                self._nodes[prev].dedent(node, False)
            if curr is not None and curr in self._nodes:
                self._nodes[curr].indent(node, False)

        # Attach created nodes to the tree.
        for node in created_nodes:
            logger.debug(
                "Attached node: %s to %s",
                node.id if node else None,
                node.parent_id if node else None,
            )
            parent_node = self._nodes.get(node.parent_id)
            parent_node.append(node, False)

        # Detach deleted nodes from the tree.
        for node in deleted_nodes:
            node.parent.remove(node)
            del self._nodes[node.id]
            if node.server_id is not None:
                del self._sid_map[node.server_id]
            logger.debug("Deleted node: %s", node.id)

        # Hydrate label references in notes.
        for node in self.all():
            for label_id in node.labels._labels:  # noqa: SLF001
                node.labels._labels[label_id] = self._labels.get(  # noqa: SLF001
                    label_id
                )

    def _parseUserInfo(self, raw: dict) -> None:
        labels = {}
        if "labels" in raw:
            for label in raw["labels"]:
                # If the mainId field exists, this is an update.
                if label["mainId"] in self._labels:
                    node = self._labels[label["mainId"]]
                    # Remove this key from our list of labels.
                    del self._labels[label["mainId"]]
                    logger.debug("Updated label: %s", label["mainId"])
                else:
                    # Otherwise, this is a brand new label.
                    node = _node.Label()
                    logger.debug("Created label: %s", label["mainId"])
                node.load(label)
                labels[label["mainId"]] = node

        # All remaining labels are deleted.
        for label_id in self._labels:
            logger.debug("Deleted label: %s", label_id)

        self._labels = labels

    def _findDirtyNodes(self) -> list[_node.Node]:
        # Find nodes that aren't in our internal nodes list and insert them.
        for node in list(self._nodes.values()):
            for child in node.children:
                if child.id not in self._nodes:
                    self._nodes[child.id] = child

        # Collect all dirty nodes (any nodes from above will be caught too).
        return [node for node in self._nodes.values() if node.dirty]

    def _clean(self) -> None:
        """Recursively check that all nodes are reachable."""
        found_ids = set()
        nodes = [self._nodes[_node.Root.ID]]

        # Enumerate all nodes from the root node
        while nodes:
            node = nodes.pop()
            found_ids.add(node.id)
            nodes = nodes + node.children

        # Find nodes that can't be reached from the root
        for node_id in self._nodes:
            if node_id in found_ids:
                continue
            logger.error("Dangling node: %s", node_id)

        # Find nodes that don't exist in the collection
        for node_id in found_ids:
            if node_id in self._nodes:
                continue
            logger.error("Unregistered node: %s", node_id)
