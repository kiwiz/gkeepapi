# -*- coding: utf-8 -*-
"""
.. automodule:: gkeepapi
   :members:
   :inherited-members:

.. moduleauthor:: Kai <z@kwi.li>
"""

import datetime
import logging
import time
import random
import enum
import six
from operator import attrgetter

from future.utils import raise_from
from . import exception

DEBUG = False

logger = logging.getLogger(__name__)

class NodeType(enum.Enum):
    """Valid note types."""

    Note = 'NOTE'
    """A Note"""

    List = 'LIST'
    """A List"""

    ListItem = 'LIST_ITEM'
    """A List item"""

    Blob = 'BLOB'
    """A blob (attachment)"""

class BlobType(enum.Enum):
    """Valid blob types."""

    Audio = 'AUDIO'
    """Audio"""

    Image = 'IMAGE'
    """Image"""

    Drawing = 'DRAWING'
    """Drawing"""

class ColorValue(enum.Enum):
    """Valid note colors."""

    White = 'DEFAULT'
    """White"""

    Red = 'RED'
    """Red"""

    Orange = 'ORANGE'
    """Orange"""

    Yellow = 'YELLOW'
    """Yellow"""

    Green = 'GREEN'
    """Green"""

    Teal = 'TEAL'
    """Teal"""

    Blue = 'BLUE'
    """Blue"""

    DarkBlue = 'CERULEAN'
    """Dark blue"""

    Purple = 'PURPLE'
    """Purple"""

    Pink = 'PINK'
    """Pink"""

    Brown = 'BROWN'
    """Brown"""

    Gray = 'GRAY'
    """Gray"""

class CategoryValue(enum.Enum):
    """Valid note categories."""

    Books = 'BOOKS'
    """Books"""

    Food = 'FOOD'
    """Food"""

    Movies = 'MOVIES'
    """Movies"""

    Music = 'MUSIC'
    """Music"""

    Places = 'PLACES'
    """Places"""

    Quotes = 'QUOTES'
    """Quotes"""

    Travel = 'TRAVEL'
    """Travel"""

    TV = 'TV'
    """TV"""

class SuggestValue(enum.Enum):
    """Valid task suggestion categories."""

    GroceryItem = 'GROCERY_ITEM'
    """Grocery item"""

class NewListItemPlacementValue(enum.Enum):
    """Target location to put new list items."""

    Top = 'TOP'
    """Top"""

    Bottom = 'BOTTOM'
    """Bottom"""

class GraveyardStateValue(enum.Enum):
    """Visibility setting for the graveyard."""

    Expanded = 'EXPANDED'
    """Expanded"""

    Collapsed = 'COLLAPSED'
    """Collapsed"""

class CheckedListItemsPolicyValue(enum.Enum):
    """Movement setting for checked list items."""

    Default = 'DEFAULT'
    """Default"""

    Graveyard = 'GRAVEYARD'
    """Graveyard"""

class ShareRequestValue(enum.Enum):
    """Collaborator change type."""

    Add = 'WR'
    """Grant access."""

    Remove = 'RM'
    """Remove access."""

class RoleValue(enum.Enum):
    """Collaborator role type."""

    Owner = 'O'
    """Note owner."""

    User = 'W'
    """Note collaborator."""

class Element(object):
    """Interface for elements that can be serialized and deserialized."""
    def __init__(self):
        self._dirty = False

    def _find_discrepancies(self, raw): # pragma: no cover
        s_raw = self.save(False)
        if isinstance(raw, dict):
            for key, val in raw.items():
                if key in ['parentServerId', 'lastSavedSessionId']:
                    continue
                if key not in s_raw:
                    logger.info('Missing key for %s key %s', type(self), key)
                    continue

                if isinstance(val, (list, dict)):
                    continue

                val_a = raw[key]
                val_b = s_raw[key]
                # Python strftime's 'z' format specifier includes microseconds, but the response from GKeep
                # only has milliseconds. This causes a string mismatch, so we construct datetime objects
                # to properly compare
                if isinstance(val_a, six.string_types) and isinstance(val_b, six.string_types):
                    try:
                        tval_a = NodeTimestamps.str_to_dt(val_a)
                        tval_b = NodeTimestamps.str_to_dt(val_b)
                        val_a, val_b = tval_a, tval_b
                    except (KeyError, ValueError):
                        pass
                if val_a != val_b:
                    logger.info('Different value for %s key %s: %s != %s', type(self), key, raw[key], s_raw[key])
        elif isinstance(raw, list):
            if len(raw) != len(s_raw):
                logger.info('Different length for %s: %d != %d', type(self), len(raw), len(s_raw))

    def load(self, raw):
        """Unserialize from raw representation. (Wrapper)

        Args:
            raw (dict): Raw.
        Raises:
            ParseException: If there was an error parsing data.
        """
        try:
            self._load(raw)
        except (KeyError, ValueError) as e:
            raise_from(exception.ParseException('Parse error in %s' % (type(self)), raw), e)

    def _load(self, raw):
        """Unserialize from raw representation. (Implementation logic)

        Args:
            raw (dict): Raw.
        """
        self._dirty = raw.get('_dirty', False)

    def save(self, clean=True):
        """Serialize into raw representation. Clears the dirty bit by default.

        Args:
            clean (bool): Whether to clear the dirty bit.

        Returns:
            dict: Raw.
        """
        ret = {}
        if clean:
            self._dirty = False
        else:
            ret['_dirty'] = self._dirty
        return ret

    @property
    def dirty(self):
        """Get dirty state.

        Returns:
            str: Whether this element is dirty.
        """
        return self._dirty

class Annotation(Element):
    """Note annotations base class."""
    def __init__(self):
        super(Annotation, self).__init__()
        self.id = self._generateAnnotationId()

    def _load(self, raw):
        super(Annotation, self)._load(raw)
        self.id = raw.get('id')

    def save(self, clean=True):
        ret = {}
        if self.id is not None:
            ret = super(Annotation, self).save(clean)
        if self.id is not None:
            ret['id'] = self.id
        return ret

    @classmethod
    def _generateAnnotationId(cls):
        return '%08x-%04x-%04x-%04x-%012x' % (
            random.randint(0x00000000, 0xffffffff),
            random.randint(0x0000, 0xffff),
            random.randint(0x0000, 0xffff),
            random.randint(0x0000, 0xffff),
            random.randint(0x000000000000, 0xffffffffffff)
        )

class WebLink(Annotation):
    """Represents a link annotation on a :class:`TopLevelNode`."""
    def __init__(self):
        super(WebLink, self).__init__()
        self._title = ''
        self._url = ''
        self._image_url = None
        self._provenance_url = ''
        self._description = ''

    def _load(self, raw):
        super(WebLink, self)._load(raw)
        self._title = raw['webLink']['title']
        self._url = raw['webLink']['url']
        self._image_url = raw['webLink']['imageUrl'] if 'imageUrl' in raw['webLink'] else self.image_url
        self._provenance_url = raw['webLink']['provenanceUrl']
        self._description = raw['webLink']['description']

    def save(self, clean=True):
        ret = super(WebLink, self).save(clean)
        ret['webLink'] = {
            'title': self._title,
            'url': self._url,
            'imageUrl': self._image_url,
            'provenanceUrl': self._provenance_url,
            'description': self._description,
        }
        return ret

    @property
    def title(self):
        """Get the link title.

        Returns:
            str: The link title.
        """
        return self._title

    @title.setter
    def title(self, value):
        self._title = value
        self._dirty = True

    @property
    def url(self):
        """Get the link url.

        Returns:
            str: The link url.
        """
        return self._url

    @url.setter
    def url(self, value):
        self._url = value
        self._dirty = True

    @property
    def image_url(self):
        """Get the link image url.

        Returns:
            str: The image url or None.
        """
        return self._image_url

    @image_url.setter
    def image_url(self, value):
        self._image_url = value
        self._dirty = True

    @property
    def provenance_url(self):
        """Get the provenance url.

        Returns:
            url: The provenance url.
        """
        return self._provenance_url

    @provenance_url.setter
    def provenance_url(self, value):
        self._provenance_url = value
        self._dirty = True

    @property
    def description(self):
        """Get the link description.

        Returns:
            str: The link description.
        """
        return self._description

    @description.setter
    def description(self, value):
        self._description = value
        self._dirty = True

class Category(Annotation):
    """Represents a category annotation on a :class:`TopLevelNode`."""
    def __init__(self):
        super(Category, self).__init__()
        self._category = None

    def _load(self, raw):
        super(Category, self)._load(raw)
        self._category = CategoryValue(raw['topicCategory']['category'])

    def save(self, clean=True):
        ret = super(Category, self).save(clean)
        ret['topicCategory'] = {
            'category': self._category.value
        }
        return ret

    @property
    def category(self):
        """Get the category.

        Returns:
            gkeepapi.node.CategoryValue: The category.
        """
        return self._category

    @category.setter
    def category(self, value):
        self._category = value
        self._dirty = True

class TaskAssist(Annotation):
    """Unknown."""
    def __init__(self):
        super(TaskAssist, self).__init__()
        self._suggest = None

    def _load(self, raw):
        super(TaskAssist, self)._load(raw)
        self._suggest = raw['taskAssist']['suggestType']

    def save(self, clean=True):
        ret = super(TaskAssist, self).save(clean)
        ret['taskAssist'] = {
            'suggestType': self._suggest
        }
        return ret

    @property
    def suggest(self):
        """Get the suggestion.

        Returns:
            str: The suggestion.
        """
        return self._suggest

    @suggest.setter
    def suggest(self, value):
        self._suggest = value
        self._dirty = True

class Context(Annotation):
    """Represents a context annotation, which may contain other annotations."""
    def __init__(self):
        super(Context, self).__init__()
        self._entries = {}

    def _load(self, raw):
        super(Context, self)._load(raw)
        self._entries = {}
        for key, entry in raw.get('context', {}).items():
            self._entries[key] = NodeAnnotations.from_json({key: entry})

    def save(self, clean=True):
        ret = super(Context, self).save(clean)
        context = {}
        for entry in self._entries.values():
            context.update(entry.save(clean))
        ret['context'] = context
        return ret

    def all(self):
        """Get all sub annotations.

        Returns:
            List[gkeepapi.node.Annotation]: Sub Annotations.
        """
        return self._entries.values()

    @property
    def dirty(self):
        return super(Context, self).dirty or any((annotation.dirty for annotation in self._entries.values()))

class NodeAnnotations(Element):
    """Represents the annotation container on a :class:`TopLevelNode`."""
    def __init__(self):
        super(NodeAnnotations, self).__init__()
        self._annotations = {}

    def __len__(self):
        return len(self._annotations)

    @classmethod
    def from_json(cls, raw):
        """Helper to construct an annotation from a dict.

        Args:
            raw (dict): Raw annotation representation.

        Returns:
            Node: An Annotation object or None.
        """
        bcls = None
        if 'webLink' in raw:
            bcls = WebLink
        elif 'topicCategory' in raw:
            bcls = Category
        elif 'taskAssist' in raw:
            bcls = TaskAssist
        elif 'context' in raw:
            bcls = Context

        if bcls is None:
            logger.warning('Unknown annotation type: %s', raw.keys())
            return None
        annotation = bcls()
        annotation.load(raw)

        return annotation

    def all(self):
        """Get all annotations.

        Returns:
            List[gkeepapi.node.Annotation]: Annotations.
        """
        return self._annotations.values()

    def _load(self, raw):
        super(NodeAnnotations, self)._load(raw)
        self._annotations = {}
        if 'annotations' not in raw:
            return

        for raw_annotation in raw['annotations']:
            annotation = self.from_json(raw_annotation)
            self._annotations[annotation.id] = annotation

    def save(self, clean=True):
        ret = super(NodeAnnotations, self).save(clean)
        ret['kind'] = 'notes#annotationsGroup'
        if self._annotations:
            ret['annotations'] = [annotation.save(clean) for annotation in self._annotations.values()]
        return ret

    def _get_category_node(self):
        for annotation in self._annotations.values():
            if isinstance(annotation, Category):
                return annotation
        return None

    @property
    def category(self):
        """Get the category.

        Returns:
            Union[gkeepapi.node.CategoryValue, None]: The category or None.
        """
        node = self._get_category_node()

        return node.category if node is not None else None

    @category.setter
    def category(self, value):
        node = self._get_category_node()
        if value is None:
            if node is not None:
                del self._annotations[node.id]
        else:
            if node is None:
                node = Category()
                self._annotations[node.id] = node

            node.category = value
        self._dirty = True

    @property
    def links(self):
        """Get all links.

        Returns:
            list[gkeepapi.node.WebLink]: A list of links.
        """
        return [annotation for annotation in self._annotations.values()
            if isinstance(annotation, WebLink)
        ]

    def append(self, annotation):
        """Add an annotation.

        Args:
            annotation (gkeepapi.node.Annotation): An Annotation object.

        Returns:
            gkeepapi.node.Annotation: The Annotation.
        """
        self._annotations[annotation.id] = annotation
        self._dirty = True
        return annotation

    def remove(self, annotation):
        """Removes an annotation.

        Args:
            annotation (gkeepapi.node.Annotation): An Annotation object.

        Returns:
            gkeepapi.node.Annotation: The Annotation.
        """
        if annotation.id in self._annotations:
            del self._annotations[annotation.id]
        self._dirty = True

    @property
    def dirty(self):
        return super(NodeAnnotations, self).dirty or any((annotation.dirty for annotation in self._annotations.values()))

class NodeTimestamps(Element):
    """Represents the timestamps associated with a :class:`TopLevelNode`."""
    TZ_FMT = '%Y-%m-%dT%H:%M:%S.%fZ'

    def __init__(self, create_time=None):
        super(NodeTimestamps, self).__init__()
        if create_time is None:
            create_time = time.time()

        self._created = self.int_to_dt(create_time)
        self._deleted = self.int_to_dt(0)
        self._trashed = self.int_to_dt(0)
        self._updated = self.int_to_dt(create_time)
        self._edited = self.int_to_dt(create_time)

    def _load(self, raw):
        super(NodeTimestamps, self)._load(raw)
        if 'created' in raw:
            self._created = self.str_to_dt(raw['created'])
        self._deleted = self.str_to_dt(raw['deleted']) \
            if 'deleted' in raw else None
        self._trashed = self.str_to_dt(raw['trashed']) \
            if 'trashed' in raw else None
        self._updated = self.str_to_dt(raw['updated'])
        self._edited = self.str_to_dt(raw['userEdited']) \
            if 'userEdited' in raw else None

    def save(self, clean=True):
        ret = super(NodeTimestamps, self).save(clean)
        ret['kind'] = 'notes#timestamps'
        ret['created'] = self.dt_to_str(self._created)
        if self._deleted is not None:
            ret['deleted'] = self.dt_to_str(self._deleted)
        if self._trashed is not None:
            ret['trashed'] = self.dt_to_str(self._trashed)
        ret['updated'] = self.dt_to_str(self._updated)
        if self._edited is not None:
            ret['userEdited'] = self.dt_to_str(self._edited)
        return ret

    @classmethod
    def str_to_dt(cls, tzs):
        """Convert a datetime string into an object.

        Params:
            tsz (str): Datetime string.

        Returns:
            datetime.datetime: Datetime.
        """
        return datetime.datetime.strptime(tzs, cls.TZ_FMT)

    @classmethod
    def int_to_dt(cls, tz):
        """Convert a unix timestamp into an object.

        Params:
            ts (int): Unix timestamp.

        Returns:
            datetime.datetime: Datetime.
        """
        return datetime.datetime.utcfromtimestamp(tz)

    @classmethod
    def dt_to_str(cls, dt):
        """Convert a datetime to a str.

        Returns:
            str: Datetime string.
        """
        return dt.strftime(cls.TZ_FMT)

    @classmethod
    def int_to_str(cls, tz):
        """Convert a unix timestamp to a str.

        Returns:
            str: Datetime string.
        """
        return cls.dt_to_str(cls.int_to_dt(tz))

    @property
    def created(self):
        """Get the creation datetime.

        Returns:
            datetime.datetime: Datetime.
        """
        return self._created

    @created.setter
    def created(self, value):
        self._created = value
        self._dirty = True

    @property
    def deleted(self):
        """Get the deletion datetime.

        Returns:
            datetime.datetime: Datetime.
        """
        return self._deleted

    @deleted.setter
    def deleted(self, value):
        self._deleted = value
        self._dirty = True

    @property
    def trashed(self):
        """Get the move-to-trash datetime.

        Returns:
            datetime.datetime: Datetime.
        """
        return self._trashed

    @trashed.setter
    def trashed(self, value):
        self._trashed = value
        self._dirty = True

    @property
    def updated(self):
        """Get the updated datetime.

        Returns:
            datetime.datetime: Datetime.
        """
        return self._updated

    @updated.setter
    def updated(self, value):
        self._updated = value
        self._dirty = True

    @property
    def edited(self):
        """Get the user edited datetime.

        Returns:
            datetime.datetime: Datetime.
        """
        return self._edited

    @edited.setter
    def edited(self, value):
        self._edited = value
        self._dirty = True

class NodeSettings(Element):
    """Represents the settings associated with a :class:`TopLevelNode`."""
    def __init__(self):
        super(NodeSettings, self).__init__()
        self._new_listitem_placement = NewListItemPlacementValue.Bottom
        self._graveyard_state = GraveyardStateValue.Collapsed
        self._checked_listitems_policy = CheckedListItemsPolicyValue.Graveyard

    def _load(self, raw):
        super(NodeSettings, self)._load(raw)
        self._new_listitem_placement = NewListItemPlacementValue(raw['newListItemPlacement'])
        self._graveyard_state = GraveyardStateValue(raw['graveyardState'])
        self._checked_listitems_policy = CheckedListItemsPolicyValue(raw['checkedListItemsPolicy'])

    def save(self, clean=True):
        ret = super(NodeSettings, self).save(clean)
        ret['newListItemPlacement'] = self._new_listitem_placement.value
        ret['graveyardState'] = self._graveyard_state.value
        ret['checkedListItemsPolicy'] = self._checked_listitems_policy.value
        return ret

    @property
    def new_listitem_placement(self):
        """Get the default location to insert new listitems.

        Returns:
            gkeepapi.node.NewListItemPlacementValue: Placement.
        """
        return self._new_listitem_placement

    @new_listitem_placement.setter
    def new_listitem_placement(self, value):
        self._new_listitem_placement = value
        self._dirty = True

    @property
    def graveyard_state(self):
        """Get the visibility state for the list graveyard.

        Returns:
            gkeepapi.node.GraveyardStateValue: Visibility.
        """
        return self._graveyard_state

    @graveyard_state.setter
    def graveyard_state(self, value):
        self._graveyard_state = value
        self._dirty = True

    @property
    def checked_listitems_policy(self):
        """Get the policy for checked listitems.

        Returns:
            gkeepapi.node.CheckedListItemsPolicyValue: Policy.
        """
        return self._checked_listitems_policy

    @checked_listitems_policy.setter
    def checked_listitems_policy(self, value):
        self._checked_listitems_policy = value
        self._dirty = True

class NodeCollaborators(Element):
    """Represents the collaborators on a :class:`TopLevelNode`."""
    def __init__(self):
        super(NodeCollaborators, self).__init__()
        self._collaborators = {}

    def __len__(self):
        return len(self._collaborators)

    def load(self, collaborators_raw, requests_raw): # pylint: disable=arguments-differ
        # Parent method not called.
        if requests_raw and isinstance(requests_raw[-1], bool):
            self._dirty = requests_raw.pop()
        else:
            self._dirty = False
        self._collaborators = {}
        for collaborator in collaborators_raw:
            self._collaborators[collaborator['email']] = RoleValue(collaborator['role'])
        for collaborator in requests_raw:
            self._collaborators[collaborator['email']] = ShareRequestValue(collaborator['type'])

    def save(self, clean=True):
        # Parent method not called.
        collaborators = []
        requests = []
        for email, action in self._collaborators.items():
            if isinstance(action, ShareRequestValue):
                requests.append({'email': email, 'type': action.value})
            else:
                collaborators.append({'email': email, 'role': action.value, 'auxiliary_type': 'None'})
        if not clean:
            requests.append(self._dirty)
        else:
            self._dirty = False
        return (collaborators, requests)

    def add(self, email):
        """Add a collaborator.

        Args:
            str : Collaborator email address.
        """
        if email not in self._collaborators:
            self._collaborators[email] = ShareRequestValue.Add
        self._dirty = True

    def remove(self, email):
        """Remove a Collaborator.

        Args:
            str : Collaborator email address.
        """
        if email in self._collaborators:
            if self._collaborators[email] == ShareRequestValue.Add:
                del self._collaborators[email]
            else:
                self._collaborators[email] = ShareRequestValue.Remove
        self._dirty = True

    def all(self):
        """Get all collaborators.

        Returns:
            List[str]: Collaborators.
        """
        return [email for email, action in self._collaborators.items() if action in [RoleValue.Owner, RoleValue.User, ShareRequestValue.Add]]

class NodeLabels(Element):
    """Represents the labels on a :class:`TopLevelNode`."""
    def __init__(self):
        super(NodeLabels, self).__init__()
        self._labels = {}

    def __len__(self):
        return len(self._labels)

    def _load(self, raw):
        # Parent method not called.
        if raw and isinstance(raw[-1], bool):
            self._dirty = raw.pop()
        else:
            self._dirty = False
        self._labels = {}
        for raw_label in raw:
            self._labels[raw_label['labelId']] = None

    def save(self, clean=True):
        # Parent method not called.
        ret = [
            {'labelId': label_id, 'deleted': NodeTimestamps.dt_to_str(datetime.datetime.utcnow()) if label is None else NodeTimestamps.int_to_str(0)}
        for label_id, label in self._labels.items()]
        if not clean:
            ret.append(self._dirty)
        else:
            self._dirty = False
        return ret

    def add(self, label):
        """Add a label.

        Args:
            label (gkeepapi.node.Label): The Label object.
        """
        self._labels[label.id] = label
        self._dirty = True

    def remove(self, label):
        """Remove a label.

        Args:
            label (gkeepapi.node.Label): The Label object.
        """
        if label.id in self._labels:
            self._labels[label.id] = None
        self._dirty = True

    def get(self, label_id):
        """Get a label by ID.

        Args:
            label_id (str): The label ID.
        """
        return self._labels.get(label_id)

    def all(self):
        """Get all labels.

        Returns:
            List[gkeepapi.node.Label]: Labels.
        """
        return [label for _, label in self._labels.items() if label is not None]

class TimestampsMixin(object):
    """A mixin to add methods for updating timestamps."""
    def touch(self, edited=False):
        """Mark the node as dirty.

        Args:
            edited (bool): Whether to set the edited time.
        """
        self._dirty = True
        dt = datetime.datetime.utcnow()
        self.timestamps.updated = dt
        if edited:
            self.timestamps.edited = dt

    @property
    def trashed(self):
        """Get the trashed state.

        Returns:
            bool: Whether this item is trashed.
        """
        return self.timestamps.trashed is not None and self.timestamps.trashed > NodeTimestamps.int_to_dt(0)

    def trash(self):
        """Mark the item as trashed."""
        self.timestamps.trashed = datetime.datetime.utcnow()

    def untrash(self):
        """Mark the item as untrashed."""
        self.timestamps.trashed = None

    @property
    def deleted(self):
        """Get the deleted state.

        Returns:
            bool: Whether this item is deleted.
        """
        return self.timestamps.deleted is not None and self.timestamps.deleted > NodeTimestamps.int_to_dt(0)

    def delete(self):
        """Mark the item as deleted."""
        self.timestamps.deleted = datetime.datetime.utcnow()

    def undelete(self):
        """Mark the item as undeleted."""
        self.timestamps.deleted = None

class Node(Element, TimestampsMixin):
    """Node base class."""
    def __init__(self, id_=None, type_=None, parent_id=None):
        super(Node, self).__init__()

        create_time = time.time()

        self.parent = None
        self.id = self._generateId(create_time) if id_ is None else id_
        self.server_id = None
        self.parent_id = parent_id
        self.type = type_
        self._sort = random.randint(1000000000, 9999999999)
        self._version = None
        self._text = ''
        self._children = {}
        self.timestamps = NodeTimestamps(create_time)
        self.settings = NodeSettings()
        self.annotations = NodeAnnotations()

        # Set if there is no baseVersion in the raw data
        self._moved = False

    @classmethod
    def _generateId(cls, tz):
        return '%x.%016x' % (
            int(tz * 1000),
            random.randint(0x0000000000000000, 0xffffffffffffffff)
        )

    def _load(self, raw):
        super(Node, self)._load(raw)
        # Verify this is a valid type
        NodeType(raw['type'])
        if raw['kind'] not in ['notes#node']:
            logger.warning('Unknown node kind: %s', raw['kind'])

        if 'mergeConflict' in raw:
            raise exception.MergeException(raw)

        self.id = raw['id']
        self.server_id = raw['serverId'] if 'serverId' in raw else self.server_id
        self.parent_id = raw['parentId']
        self._sort = raw['sortValue'] if 'sortValue' in raw else self.sort
        self._version = raw['baseVersion'] if 'baseVersion' in raw else self._version
        self._text = raw['text'] if 'text' in raw else self._text
        self.timestamps.load(raw['timestamps'])
        self.settings.load(raw['nodeSettings'])
        self.annotations.load(raw['annotationsGroup'])

    def save(self, clean=True):
        ret = super(Node, self).save(clean)
        ret['id'] = self.id
        ret['kind'] = 'notes#node'
        ret['type'] = self.type.value
        ret['parentId'] = self.parent_id
        ret['sortValue'] = self._sort
        if not self._moved and self._version is not None:
            ret['baseVersion'] = self._version
        ret['text'] = self._text
        if self.server_id is not None:
            ret['serverId'] = self.server_id
        ret['timestamps'] = self.timestamps.save(clean)
        ret['nodeSettings'] = self.settings.save(clean)
        ret['annotationsGroup'] = self.annotations.save(clean)
        return ret

    @property
    def sort(self):
        """Get the sort id.

        Returns:
            int: Sort id.
        """
        return self._sort

    @sort.setter
    def sort(self, value):
        self._sort = value
        self.touch()

    @property
    def version(self):
        """Get the node version.

        Returns:
            int: Version.
        """
        return self._version

    @property
    def text(self):
        """Get the text value.

        Returns:
            str: Text value.
        """
        return self._text

    @text.setter
    def text(self, value):
        """Set the text value.

        Args:
            value (str): Text value.
        """
        self._text = value
        self.timestamps.edited = datetime.datetime.utcnow()
        self.touch(True)

    @property
    def children(self):
        """Get all children.

        Returns:
            list[gkeepapi.Node]: Children nodes.
        """
        return list(self._children.values())

    def get(self, node_id):
        """Get child node with the given ID.

        Args:
            node_id (str): The node ID.

        Returns:
            gkeepapi.Node: Child node.
        """
        return self._children.get(node_id)

    def append(self, node, dirty=True):
        """Add a new child node.

        Args:
            node (gkeepapi.Node): Node to add.
            dirty (bool): Whether this node should be marked dirty.
        """
        self._children[node.id] = node
        node.parent = self
        if dirty:
            self.touch()

        return node

    def remove(self, node, dirty=True):
        """Remove the given child node.

        Args:
            node (gkeepapi.Node): Node to remove.
            dirty (bool): Whether this node should be marked dirty.
        """
        if node.id in self._children:
            self._children[node.id].parent = None
            del self._children[node.id]
        if dirty:
            self.touch()

    @property
    def new(self):
        """Get whether this node has been persisted to the server.

        Returns:
            bool: True if node is new.
        """
        return self.server_id is None

    @property
    def dirty(self):
        return super(Node, self).dirty or self.timestamps.dirty or self.annotations.dirty or self.settings.dirty or any((node.dirty for node in self.children))

class Root(Node):
    """Internal root node."""
    ID = 'root'
    def __init__(self):
        super(Root, self).__init__(id_=self.ID)

    @property
    def dirty(self):
        return False

class TopLevelNode(Node):
    """Top level node base class."""
    _TYPE = None
    def __init__(self, **kwargs):
        super(TopLevelNode, self).__init__(parent_id=Root.ID, **kwargs)
        self._color = ColorValue.White
        self._archived = False
        self._pinned = False
        self._title = ''
        self.labels = NodeLabels()
        self.collaborators = NodeCollaborators()

    def _load(self, raw):
        super(TopLevelNode, self)._load(raw)
        self._color = ColorValue(raw['color']) if 'color' in raw else ColorValue.White
        self._archived = raw['isArchived'] if 'isArchived' in raw else False
        self._pinned = raw['isPinned'] if 'isPinned' in raw else False
        self._title = raw['title'] if 'title' in raw else ''
        self.labels.load(raw['labelIds'] if 'labelIds' in raw else [])

        self.collaborators.load(
            raw['roleInfo'] if 'roleInfo' in raw else [],
            raw['shareRequests'] if 'shareRequests' in raw else [],
        )
        self._moved = 'moved' in raw

    def save(self, clean=True):
        ret = super(TopLevelNode, self).save(clean)
        ret['color'] = self._color.value
        ret['isArchived'] = self._archived
        ret['isPinned'] = self._pinned
        ret['title'] = self._title
        labels = self.labels.save(clean)

        collaborators, requests = self.collaborators.save(clean)
        if labels:
            ret['labelIds'] = labels
        ret['collaborators'] = collaborators
        if requests:
            ret['shareRequests'] = requests
        return ret

    @property
    def color(self):
        """Get the node color.

        Returns:
            gkeepapi.node.Color: Color.
        """
        return self._color

    @color.setter
    def color(self, value):
        self._color = value
        self.touch(True)

    @property
    def archived(self):
        """Get the archive state.

        Returns:
            bool: Whether this node is archived.
        """
        return self._archived

    @archived.setter
    def archived(self, value):
        self._archived = value
        self.touch(True)

    @property
    def pinned(self):
        """Get the pin state.

        Returns:
            bool: Whether this node is pinned.
        """
        return self._pinned

    @pinned.setter
    def pinned(self, value):
        self._pinned = value
        self.touch(True)

    @property
    def title(self):
        """Get the title.

        Returns:
            str: Title.
        """
        return self._title

    @title.setter
    def title(self, value):
        self._title = value
        self.touch(True)

    @property
    def url(self):
        """Get the url for this node.

        Returns:
            str: Google Keep url.
        """
        return 'https://keep.google.com/u/0/#' + self._TYPE.value + '/' + self.id

    @property
    def dirty(self):
        return super(TopLevelNode, self).dirty or self.labels.dirty or self.collaborators.dirty

    @property
    def blobs(self):
        """Get all media blobs.

        Returns:
            list[gkeepapi.node.Blob]: Media blobs.
        """
        return [node for node in self.children if isinstance(node, Blob)]

    @property
    def images(self):
        return [blob for blob in self.blobs if isinstance(blob.blob, NodeImage)]

    @property
    def drawings(self):
        return [blob for blob in self.blobs if isinstance(blob.blob, NodeDrawing)]

    @property
    def audio(self):
        return [blob for blob in self.blobs if isinstance(blob.blob, NodeAudio)]

class Note(TopLevelNode):
    """Represents a Google Keep note."""
    _TYPE = NodeType.Note
    def __init__(self, **kwargs):
        super(Note, self).__init__(type_=self._TYPE, **kwargs)

    def _get_text_node(self):
        node = None
        for child_node in self.children:
            if isinstance(child_node, ListItem):
                node = child_node
                break

        return node

    @property
    def text(self):
        node = self._get_text_node()

        if node is None:
            return self._text
        return node.text

    @text.setter
    def text(self, value):
        node = self._get_text_node()
        if node is None:
            node = ListItem(parent_id=self.id)
            self.append(node, True)
        node.text = value
        self.touch(True)

    def __str__(self):
        return '\n'.join([self.title, self.text])

class List(TopLevelNode):
    """Represents a Google Keep list."""
    _TYPE = NodeType.List
    SORT_DELTA = 10000 # Arbitrary constant
    def __init__(self, **kwargs):
        super(List, self).__init__(type_=self._TYPE, **kwargs)

    def add(self, text, checked=False, sort=None):
        """Add a new item to the list.

        Args:
            text (str): The text.
            checked (bool): Whether this item is checked.
            sort (Union[gkeepapi.node.NewListItemPlacementValue, int]): Item id for sorting or a placement policy.
        """
        node = ListItem(parent_id=self.id, parent_server_id=self.server_id)
        node.checked = checked
        node.text = text

        items = list(self.items)
        if isinstance(sort, int):
            node.sort = sort
        elif isinstance(sort, NewListItemPlacementValue) and len(items):
            func = max
            delta = self.SORT_DELTA
            if sort == NewListItemPlacementValue.Bottom:
                func = min
                delta *= -1

            node.sort = func((int(item.sort) for item in items)) + delta

        self.append(node, True)
        self.touch(True)
        return node

    @property
    def text(self):
        return '\n'.join((six.text_type(node) for node in self.items))

    @classmethod
    def sorted_items(cls, items):
        """Generate a list of sorted list items, taking into account parent items.

        Args:
            items (list[gkeepapi.node.ListItem]): Items to sort.
        Returns:
            list[gkeepapi.node.ListItem]: Sorted items.
        """
        class t(tuple):
            """Tuple with element-based sorting"""
            def __cmp__(self, other):
                for a, b in six.moves.zip_longest(self, other):
                    if a != b:
                        if a is None:
                            return 1
                        if b is None:
                            return -1
                        return a - b
                return 0

            def __lt__(self, other): # pragma: no cover
                return self.__cmp__(other) < 0
            def __gt_(self, other): # pragma: no cover
                return self.__cmp__(other) > 0
            def __le__(self, other): # pragma: no cover
                return self.__cmp__(other) <= 0
            def __ge_(self, other): # pragma: no cover
                return self.__cmp__(other) >= 0
            def __eq__(self, other): # pragma: no cover
                return self.__cmp__(other) == 0
            def __ne__(self, other): # pragma: no cover
                return self.__cmp__(other) != 0

        def key_func(x):
            if x.indented:
                return t((int(x.parent_item.sort), int(x.sort)))
            return t((int(x.sort), ))

        return sorted(items, key=key_func, reverse=True)

    def _items(self, checked=None):
        return [
            node for node in self.children
            if isinstance(node, ListItem) and not node.deleted and (
                checked is None or node.checked == checked
            )
        ]

    def sort_items(self, key=attrgetter('text'), reverse=False):
        """Sort list items in place. By default, the items are alphabetized,
        but a custom function can be specified.

        Args:
            key (callable): A filter function.
            reverse (bool): Whether to reverse the output.
        """
        sorted_children = sorted(self._items(), key=key, reverse=reverse)
        sort_value = random.randint(1000000000, 9999999999)

        for node in sorted_children:
            node.sort = sort_value
            sort_value -= self.SORT_DELTA

    def __str__(self):
        return '\n'.join(([self.title] + [six.text_type(node) for node in self.items]))

    @property
    def items(self):
        """Get all listitems.

        Returns:
            list[gkeepapi.node.ListItem]: List items.
        """
        return self.sorted_items(self._items())

    @property
    def checked(self):
        """Get all checked listitems.

        Returns:
            list[gkeepapi.node.ListItem]: List items.
        """
        return self.sorted_items(self._items(True))

    @property
    def unchecked(self):
        """Get all unchecked listitems.

        Returns:
            list[gkeepapi.node.ListItem]: List items.
        """
        return self.sorted_items(self._items(False))

class ListItem(Node):
    """Represents a Google Keep listitem.
    Interestingly enough, :class:`Note`s store their content in a single
    child :class:`ListItem`.
    """
    def __init__(self, parent_id=None, parent_server_id=None, super_list_item_id=None, **kwargs):
        super(ListItem, self).__init__(type_=NodeType.ListItem, parent_id=parent_id, **kwargs)
        self.parent_item = None
        self.parent_server_id = parent_server_id
        self.super_list_item_id = super_list_item_id
        self.prev_super_list_item_id = None
        self._subitems = {}
        self._checked = False

    def _load(self, raw):
        super(ListItem, self)._load(raw)
        self.prev_super_list_item_id = self.super_list_item_id
        self.super_list_item_id = raw.get('superListItemId') or None
        self._checked = raw.get('checked', False)

    def save(self, clean=True):
        ret = super(ListItem, self).save(clean)
        ret['parentServerId'] = self.parent_server_id
        ret['superListItemId'] = self.super_list_item_id
        ret['checked'] = self._checked
        return ret

    def add(self, text, checked=False, sort=None):
        """Add a new sub item to the list. This item must already be attached to a list.

        Args:
            text (str): The text.
            checked (bool): Whether this item is checked.
            sort (int): Item id for sorting.
        """
        if self.parent is None:
            raise exception.InvalidException('Item has no parent')
        node = self.parent.add(text, checked, sort)
        self.indent(node)
        return node

    def indent(self, node, dirty=True):
        """Indent an item. Does nothing if the target has subitems.

        Args:
            node (gkeepapi.node.ListItem): Item to indent.
            dirty (bool): Whether this node should be marked dirty.
        """
        if node.subitems:
            return

        self._subitems[node.id] = node
        node.super_list_item_id = self.id
        node.parent_item = self
        if dirty:
            node.touch(True)

    def dedent(self, node, dirty=True):
        """Dedent an item. Does nothing if the target is not indented under this item.

        Args:
            node (gkeepapi.node.ListItem): Item to dedent.
            dirty (bool): Whether this node should be marked dirty.
        """
        if node.id not in self._subitems:
            return

        del self._subitems[node.id]
        node.super_list_item_id = None
        node.parent_item = None
        if dirty:
            node.touch(True)

    @property
    def subitems(self):
        """Get subitems for this item.

        Returns:
            list[gkeepapi.node.ListItem]: Subitems.
        """
        return List.sorted_items(
            self._subitems.values()
        )

    @property
    def indented(self):
        """Get indentation state.

        Returns:
            bool: Whether this item is indented.
        """
        return self.parent_item is not None

    @property
    def checked(self):
        """Get the checked state.

        Returns:
            bool: Whether this item is checked.
        """
        return self._checked

    @checked.setter
    def checked(self, value):
        self._checked = value
        self.touch(True)

    def __str__(self):
        return u'%s%s %s' % (
            '  ' if self.indented else '',
            u'☑' if self.checked else u'☐',
            self.text
        )

class NodeBlob(Element):
    """Represents a blob descriptor."""
    _TYPE = None
    def __init__(self, type_=None):
        super(NodeBlob, self).__init__()
        self.blob_id = None
        self.type = type_
        self._media_id = None
        self._mimetype = ''
        self._is_uploaded = False

    def _load(self, raw):
        super(NodeBlob, self)._load(raw)
        # Verify this is a valid type
        BlobType(raw['type'])
        self.blob_id = raw.get('blob_id')
        self._media_id = raw.get('media_id')
        self._mimetype = raw.get('mimetype')

    def save(self, clean=True):
        ret = super(NodeBlob, self).save(clean)
        ret['kind'] = 'notes#blob'
        ret['type'] = self.type.value
        if self.blob_id is not None:
            ret['blob_id'] = self.blob_id
        if self._media_id is not None:
            ret['media_id'] = self._media_id
        ret['mimetype'] = self._mimetype
        return ret

class NodeAudio(NodeBlob):
    """Represents an audio blob."""
    _TYPE = BlobType.Audio
    def __init__(self):
        super(NodeAudio, self).__init__(type_=self._TYPE)
        self._length = None

    def _load(self, raw):
        super(NodeAudio, self)._load(raw)
        self._length = raw.get('length')

    def save(self, clean=True):
        ret = super(NodeAudio, self).save(clean)
        if self._length is not None:
            ret['length'] = self._length
        return ret

    @property
    def length(self):
        """Get length of the audio clip.
        Returns:
            int: Audio length.
        """
        return self._length

class NodeImage(NodeBlob):
    """Represents an image blob."""
    _TYPE = BlobType.Image
    def __init__(self):
        super(NodeImage, self).__init__(type_=self._TYPE)
        self._is_uploaded = False
        self._width = 0
        self._height = 0
        self._byte_size = 0
        self._extracted_text = ''
        self._extraction_status = ''

    def _load(self, raw):
        super(NodeImage, self)._load(raw)
        self._is_uploaded = raw.get('is_uploaded') or False
        self._width = raw.get('width')
        self._height = raw.get('height')
        self._byte_size = raw.get('byte_size')
        self._extracted_text = raw.get('extracted_text')
        self._extraction_status = raw.get('extraction_status')

    def save(self, clean=True):
        ret = super(NodeImage, self).save(clean)
        ret['width'] = self._width
        ret['height'] = self._height
        ret['byte_size'] = self._byte_size
        ret['extracted_text'] = self._extracted_text
        ret['extraction_status'] = self._extraction_status
        return ret

    @property
    def width(self):
        """Get width of image.
        Returns:
            int: Image width.
        """
        return self._width

    @property
    def height(self):
        """Get height of image.
        Returns:
            int: Image height.
        """
        return self._height

    @property
    def byte_size(self):
        """Get size of image in bytes.
        Returns:
            int: Image byte size.
        """
        return self._byte_size

    @property
    def extracted_text(self):
        """Get text extracted from image
        Returns:
            str: Extracted text.
        """
        return self._extracted_text

    @property
    def url(self):
        """Get a url to the image.
        Returns:
            str: Image url.
        """
        raise NotImplementedError()

class NodeDrawing(NodeBlob):
    """Represents a drawing blob."""
    _TYPE = BlobType.Drawing
    def __init__(self):
        super(NodeDrawing, self).__init__(type_=self._TYPE)
        self._extracted_text = ''
        self._extraction_status = ''
        self._drawing_info = None

    def _load(self, raw):
        super(NodeDrawing, self)._load(raw)
        self._extracted_text = raw.get('extracted_text')
        self._extraction_status = raw.get('extraction_status')
        drawing_info = None
        if 'drawingInfo' in raw:
            drawing_info = NodeDrawingInfo()
            drawing_info.load(raw['drawingInfo'])
        self._drawing_info = drawing_info

    def save(self, clean=True):
        ret = super(NodeDrawing, self).save(clean)
        ret['extracted_text'] = self._extracted_text
        ret['extraction_status'] = self._extraction_status
        if self._drawing_info is not None:
            ret['drawingInfo'] = self._drawing_info.save(clean)
        return ret

    @property
    def extracted_text(self):
        """Get text extracted from image
        Returns:
            str: Extracted text.
        """
        return self._drawing_info.snapshot.extracted_text \
            if self._drawing_info is not None else ''

class NodeDrawingInfo(Element):
    """Represents information about a drawing blob."""
    def __init__(self):
        super(NodeDrawingInfo, self).__init__()
        self.drawing_id = ''
        self.snapshot = NodeImage()
        self._snapshot_fingerprint = ''
        self._thumbnail_generated_time = NodeTimestamps.int_to_dt(0)
        self._ink_hash = ''
        self._snapshot_proto_fprint = ''

    def _load(self, raw):
        super(NodeDrawingInfo, self)._load(raw)
        self.drawing_id = raw['drawingId']
        self.snapshot.load(raw['snapshotData'])
        self._snapshot_fingerprint = raw['snapshotFingerprint'] if 'snapshotFingerprint' in raw else self._snapshot_fingerprint
        self._thumbnail_generated_time = NodeTimestamps.str_to_dt(raw['thumbnailGeneratedTime']) if 'thumbnailGeneratedTime' in raw else NodeTimestamps.int_to_dt(0)
        self._ink_hash = raw['inkHash'] if 'inkHash' in raw else ''
        self._snapshot_proto_fprint = raw['snapshotProtoFprint'] if 'snapshotProtoFprint' in raw else self._snapshot_proto_fprint

    def save(self, clean=True):
        ret = super(NodeDrawingInfo, self).save(clean)
        ret['drawingId'] = self.drawing_id
        ret['snapshotData'] = self.snapshot.save(clean)
        ret['snapshotFingerprint'] = self._snapshot_fingerprint
        ret['thumbnailGeneratedTime'] = NodeTimestamps.dt_to_str(self._thumbnail_generated_time)
        ret['inkHash'] = self._ink_hash
        ret['snapshotProtoFprint'] = self._snapshot_proto_fprint
        return ret

class Blob(Node):
    """Represents a Google Keep blob."""
    _blob_type_map = {
        BlobType.Audio: NodeAudio,
        BlobType.Image: NodeImage,
        BlobType.Drawing: NodeDrawing,
    }

    def __init__(self, parent_id=None, **kwargs):
        super(Blob, self).__init__(type_=NodeType.Blob, parent_id=parent_id, **kwargs)
        self.blob = None

    @classmethod
    def from_json(cls, raw):
        """Helper to construct a blob from a dict.

        Args:
            raw (dict): Raw blob representation.

        Returns:
            NodeBlob: A NodeBlob object or None.
        """
        if raw is None:
            return None

        _type = raw.get('type')
        if _type is None:
            return None

        bcls = None
        try:
            bcls = cls._blob_type_map[BlobType(_type)]
        except (KeyError, ValueError) as e:
            logger.warning('Unknown blob type: %s', _type)
            if DEBUG: # pragma: no cover
                raise_from(exception.ParseException('Parse error for %s' % (_type), raw), e)
            return None
        blob = bcls()
        blob.load(raw)

        return blob

    def _load(self, raw):
        super(Blob, self)._load(raw)
        self.blob = self.from_json(raw.get('blob'))

    def save(self, clean=True):
        ret = super(Blob, self).save(clean)
        if self.blob is not None:
            ret['blob'] = self.blob.save(clean)
        return ret

class Label(Element, TimestampsMixin):
    """Represents a label."""
    def __init__(self):
        super(Label, self).__init__()

        create_time = time.time()

        self.id = self._generateId(create_time)
        self._name = ''
        self.timestamps = NodeTimestamps(create_time)
        self._merged = NodeTimestamps.int_to_dt(0)

    @classmethod
    def _generateId(cls, tz):
        return 'tag.%s.%x' % (
            ''.join([random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(12)]),
            int(tz * 1000)
        )

    def _load(self, raw):
        super(Label, self)._load(raw)
        self.id = raw['mainId']
        self._name = raw['name']
        self.timestamps.load(raw['timestamps'])
        self._merged = NodeTimestamps.str_to_dt(raw['lastMerged']) if 'lastMerged' in raw else NodeTimestamps.int_to_dt(0)

    def save(self, clean=True):
        ret = super(Label, self).save(clean)
        ret['mainId'] = self.id
        ret['name'] = self._name
        ret['timestamps'] = self.timestamps.save(clean)
        ret['lastMerged'] = NodeTimestamps.dt_to_str(self._merged)
        return ret

    @property
    def name(self):
        """Get the label name.

        Returns:
            str: Label name.
        """
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        self.touch(True)

    @property
    def merged(self):
        """Get last merge datetime.

        Returns:
            datetime: Datetime.
        """
        return self._merged

    @merged.setter
    def merged(self, value):
        self._merged = value
        self.touch()

    @property
    def dirty(self):
        return super(Label, self).dirty or self.timestamps.dirty

    def __str__(self):
        return self.name

_type_map = {
    NodeType.Note: Note,
    NodeType.List: List,
    NodeType.ListItem: ListItem,
    NodeType.Blob: Blob,
}

def from_json(raw):
    """Helper to construct a node from a dict.

    Args:
        raw (dict): Raw node representation.

    Returns:
        Node: A Node object or None.
    """
    ncls = None
    _type = raw.get('type')
    try:
        ncls = _type_map[NodeType(_type)]
    except (KeyError, ValueError) as e:
        logger.warning('Unknown node type: %s', _type)
        if DEBUG: # pragma: no cover
            raise_from(exception.ParseException('Parse error for %s' % (_type), raw), e)
        return None
    node = ncls()
    node.load(raw)

    return node

if DEBUG: # pragma: no cover
    Node.__load = Node._load # pylint: disable=protected-access
    def _load(self, raw): # pylint: disable=missing-docstring
        self.__load(raw) # pylint: disable=protected-access
        self._find_discrepancies(raw) # pylint: disable=protected-access
    Node._load = _load # pylint: disable=protected-access
