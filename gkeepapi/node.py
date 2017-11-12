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
import six

DEBUG = True

logger = logging.getLogger(__name__)

def from_json(raw):
    """Helper to construct a node from a dict.

    Args:
        raw (dict): Raw node representation.

    Returns:
        Node: A Node object or None.
    """
    cls = None
    _type = raw.get('type')
    if _type == 'NOTE':
        cls = Note
    elif _type == 'LIST':
        cls = List
    elif _type == 'LIST_ITEM':
        cls = ListItem
    elif _type == 'BLOB':
        cls = Blob

    if cls is None:
        logger.warning('Unknown node type: %s', _type)
        return None
    node = cls()
    node.load(raw)
    return node

COLOR = {
    'WHITE': 'DEFAULT',
    'RED': 'RED',
    'ORANGE': 'ORANGE',
    'YELLOW': 'YELLOW',
    'GREEN': 'GREEN',
    'TEAL': 'TEAL',
    'BLUE': 'BLUE',
    'DARKBLUE': 'CERULEAN',
    'PURPLE': 'PURPLE',
    'PINK': 'PINK',
    'BROWN': 'BROWN',
    'GRAY': 'GRAY',
}

TYPE = {
    'NOTE': 'NOTE',
    'LIST': 'LIST',
    'LISTITEM': 'LIST_ITEM',
    'BLOB': 'BLOB',
}

CATEGORY = {
    'BOOKS': 'BOOKS',
    'FOOD': 'FOOD',
    'MOVIES': 'MOVIES',
    'MUSIC': 'MUSIC',
    'PLACES': 'PLACES',
    'QUOTES': 'QUOTES',
    'TRAVEL': 'TRAVEL',
    'TV': 'TV',
}

NEW_LISTITEM_PLACEMENT = {
    'TOP': 'TOP',
    'BOTTOM': 'BOTTOM'
}
GRAVEYARD_STATE = {
    'EXPANDED': 'EXPANDED',
    'COLLAPSED': 'COLLAPSED',
}
CHECKED_LISTITEMS_POLICY = {
    'GRAVEYARD': 'GRAVEYARD'
}

class Element(object):
    """Interface for elements that can be serialized and deserialized."""
    def __init__(self):
        self._dirty = False

    def _find_discrepancies(self, raw):
        s_raw = self.save()
        if isinstance(raw, dict):
            for key, val in raw.items():
                if key in ['parentServerId', 'lastSavedSessionId']:
                    continue
                if key not in s_raw:
                    logger.warning('Missing key for %s key %s', type(self), key)
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
                    except ValueError:
                        pass
                if val_a != val_b:
                    logger.warning('Different value for %s key %s: %s != %s', type(self), key, raw[key], s_raw[key])
        elif isinstance(raw, list):
            if len(raw) != len(s_raw):
                logger.warning('Different length for %s: %d != %d', type(self), len(raw), len(s_raw))

    def load(self, raw): # pylint: disable=unused-argument
        """Unserialize from raw representation.

        Args:
            raw (dict): Raw.
        """
        self._dirty = False

    def save(self):
        """Serialize into raw representation

        Returns:
            dict: Raw.
        """
        self._dirty = False
        return {}

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

    def load(self, raw):
        super(Annotation, self).load(raw)
        self.id = raw['id']

    def save(self):
        ret = super(Annotation, self).save()
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

    def load(self, raw):
        super(WebLink, self).load(raw)
        self._title = raw['webLink']['title']
        self._url = raw['webLink']['url']
        self._image_url = raw['webLink']['imageUrl'] if 'imageUrl' in raw['webLink'] else self.image_url
        self._provenance_url = raw['webLink']['provenanceUrl']
        self._description = raw['webLink']['description']

    def save(self):
        ret = super(WebLink, self).save()
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

    def load(self, raw):
        super(Category, self).load(raw)
        self._category = raw['topicCategory']['category']

    def save(self):
        ret = super(Category, self).save()
        ret['topicCategory'] = {
            'category': self._category
        }
        return ret

    @property
    def category(self):
        """Get the category.

        Returns:
            str: The category.
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

    def load(self, raw):
        super(TaskAssist, self).load(raw)
        self._suggest = raw['taskAssist']['suggestType']

    def save(self):
        ret = super(TaskAssist, self).save()
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

class NodeAnnotations(Element):
    """Represents the annotation container on a :class:`TopLevelNode`."""
    def __init__(self):
        super(NodeAnnotations, self).__init__()
        self._annotations = {}

    @classmethod
    def from_json(cls, raw):
        """Helper to construct an annotation from a dict.

        Args:
            raw (dict): Raw annotation representation.

        Returns:
            Node: An Annotation object or None.
        """
        cls = None
        if 'webLink' in raw:
            cls = WebLink
        elif 'topicCategory' in raw:
            cls = Category
        elif 'taskAssist' in raw:
            cls = TaskAssist

        if cls is None:
            logger.warning('Unknown annotation type: %s', raw.keys())
            return None
        annotation = cls()
        annotation.load(raw)
        return annotation

    def load(self, raw):
        super(NodeAnnotations, self).load(raw)
        self._annotations = {}
        if 'annotations' not in raw:
            return

        for raw_annotation in raw['annotations']:
            annotation = self.from_json(raw_annotation)
            self._annotations[annotation.id] = annotation

    def save(self):
        ret = super(NodeAnnotations, self).save()
        ret['kind'] = 'notes#annotationsGroup'
        if self._annotations:
            ret['annotations'] = [annotation.save() for annotation in self._annotations.values()]
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
            str: The category or None.
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

    def load(self, raw):
        super(NodeTimestamps, self).load(raw)
        self._created = self.str_to_dt(raw['created'])
        self._deleted = self.str_to_dt(raw['deleted']) \
            if 'deleted' in raw else None
        self._trashed = self.str_to_dt(raw['trashed']) \
            if 'trashed' in raw else None
        self._updated = self.str_to_dt(raw['updated'])
        self._edited = self.str_to_dt(raw['userEdited']) \
            if 'userEdited' in raw else None

    def save(self):
        ret = super(NodeTimestamps, self).save()
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
        self._new_listitem_placement = NEW_LISTITEM_PLACEMENT['BOTTOM']
        self._graveyard_state = GRAVEYARD_STATE['COLLAPSED']
        self._checked_listitems_policy = CHECKED_LISTITEMS_POLICY['GRAVEYARD']

    def load(self, raw):
        super(NodeSettings, self).load(raw)
        self._new_listitem_placement = raw['newListItemPlacement']
        self._graveyard_state = raw['graveyardState']
        self._checked_listitems_policy = raw['checkedListItemsPolicy']

    def save(self):
        ret = super(NodeSettings, self).save()
        ret['newListItemPlacement'] = self._new_listitem_placement
        ret['graveyardState'] = self._graveyard_state
        ret['checkedListItemsPolicy'] = self._checked_listitems_policy
        return ret

    @property
    def new_listitem_placement(self):
        """Get the default location to insert new listitems.

        Returns:
            str: Placement.
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
            str: Visibility.
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
            str: Policy.
        """
        return self._checked_listitems_policy

    @checked_listitems_policy.setter
    def checked_listitems_policy(self, value):
        self._checked_listitems_policy = value
        self._dirty = True

class NodeLabels(Element):
    """Represents the labels on a :class:`TopLevelNode`."""
    def __init__(self):
        super(NodeLabels, self).__init__()
        self._labels = {}

    def load(self, raw):
        super(NodeLabels, self).load(raw)
        self._labels = {}
        for raw_label in raw:
            self._labels[raw_label['labelId']] = None

    def save(self):
        super(NodeLabels, self).save()
        return [
            {'labelId': label_id, 'deleted': NodeTimestamps.dt_to_str(datetime.datetime.utcnow()) if label is None else NodeTimestamps.int_to_str(0)}
        for label_id, label in self._labels.items()]

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
        self._version = 1
        self._text = ''
        self._children = {}
        self.timestamps = NodeTimestamps(create_time)
        self.settings = NodeSettings()
        self.annotations = NodeAnnotations()

    @classmethod
    def _generateId(cls, tz):
        return '%x.%016x' % (
            int(tz * 1000),
            random.randint(0x0000000000000000, 0xffffffffffffffff)
        )

    def load(self, raw):
        super(Node, self).load(raw)
        if raw['type'] not in TYPE.values():
            logger.warning('Unknown node type: %s', raw['type'])
        if raw['kind'] not in ['notes#node']:
            logger.warning('Unknown node kind: %s', raw['kind'])

        self.id = raw['id']
        self.server_id = raw['serverId'] if 'serverId' in raw else self.server_id
        self.parent_id = raw['parentId']
        self._sort = raw['sortValue'] if 'sortValue' in raw else self.sort
        self._version = raw['baseVersion']
        self._text = raw['text'] if 'text' in raw else ''
        self.timestamps.load(raw['timestamps'])
        self.settings.load(raw['nodeSettings'])
        self.annotations.load(raw['annotationsGroup'])

    def save(self):
        ret = super(Node, self).save()
        ret['id'] = self.id
        ret['kind'] = 'notes#node'
        ret['type'] = self.type
        ret['parentId'] = self.parent_id
        ret['sortValue'] = self._sort
        ret['baseVersion'] = self._version
        ret['text'] = self._text
        if self.server_id is not None:
            ret['serverId'] = self.server_id
        ret['timestamps'] = self.timestamps.save()
        ret['nodeSettings'] = self.settings.save()
        ret['annotationsGroup'] = self.annotations.save()
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
    def trashed(self):
        return self.timestamps.trashed > NodeTimestamps.int_to_dt(0)

    @trashed.setter
    def trashed(self, value):
        self.timestamps.trashed = datetime.datetime.utcnow(0) if value else NodeTimestamps.int_to_dt(0)
        self.touch()

    @property
    def children(self):
        """Get all children.

        Returns:
            list[gkeepapi.Node]: Children nodes.
        """
        return self._children.values()

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
        self._color = COLOR['WHITE']
        self._archived = False
        self._pinned = False
        self._title = ''
        self.labels = NodeLabels()

    def load(self, raw):
        super(TopLevelNode, self).load(raw)
        self._color = raw['color'] if 'color' in raw else COLOR['WHITE']
        self._archived = raw['isArchived']
        self._pinned = raw['isPinned'] if 'isPinned' in raw else False
        self._title = raw['title']
        self.labels.load(raw['labelIds'] if 'labelIds' in raw else [])

    def save(self):
        ret = super(TopLevelNode, self).save()
        ret['color'] = self._color
        ret['isArchived'] = self._archived
        ret['isPinned'] = self._pinned
        ret['title'] = self._title
        labels = self.labels.save()
        if labels:
            ret['labelIds'] = labels
        return ret

    @property
    def color(self):
        """Get the node color.

        Returns:
            str: Color.
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
        return 'https://keep.google.com/u/0/#' + self._TYPE + '/' + self.id

    @property
    def dirty(self):
        return super(TopLevelNode, self).dirty or self.labels.dirty

class Note(TopLevelNode):
    """Represents a Google Keep note."""
    _TYPE = TYPE['NOTE']
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
    _TYPE = TYPE['LIST']
    def __init__(self, **kwargs):
        super(List, self).__init__(type_=self._TYPE, **kwargs)

    def add(self, text, checked=False):
        """Add a new item to the list.

        Args:
            text (str): The text.
            checked (bool): Whether this item is checked.
        """
        node = ListItem(parent_id=self.id)
        node.checked = checked
        node.text = text
        self.append(node, True)
        self.touch(True)
        return node

    @property
    def text(self):
        return '\n'.join((six.text_type(node) for node in self.children))

    @property
    def items(self):
        """Get all listitems.

        Returns:
            list[gkeepapi.node.ListItem]: List items.
        """
        return [node for node in self.children if isinstance(node, ListItem) and not node.deleted]

    def __str__(self):
        return '\n'.join(([self.title] + [six.text_type(node) for node in self.items]))

class ListItem(Node):
    """Represents a Google Keep listitem.
    Interestingly enough, :class:`Note`s store their content in a single
    child :class:`ListItem`.
    """
    def __init__(self, parent_id=None, **kwargs):
        super(ListItem, self).__init__(type_=TYPE['LISTITEM'], parent_id=parent_id, **kwargs)
        self._checked = False

    def load(self, raw):
        super(ListItem, self).load(raw)
        self._checked = raw['checked']

    def save(self):
        ret = super(ListItem, self).save()
        ret['checked'] = self.checked
        return ret

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
        return u'%s %s' % (u'☑' if self.checked else u'☐', self.text)

class NodeBlob(Element):
    """Represents a blob descriptor."""
    def __init__(self):
        super(NodeBlob, self).__init__()
        self._blob_id = None
        self._media_id = None
        self._mimetype = ''
        self._byte_size = 0
        self._is_uploaded = False

    def load(self, raw):
        super(NodeBlob, self).load(raw)
        self._blob_id = raw.get('blob_id')
        self._media_id = raw.get('media_id')
        self._mimetype = raw['mimetype']
        self._byte_size = raw['byte_size']

    def save(self):
        ret = super(NodeBlob, self).save()
        if self._blob_id is not None:
            ret['blob_id'] = self._blob_id
        if self._media_id is not None:
            ret['media_id'] = self._media_id
        ret['mimetype'] = self._mimetype
        ret['byte_size'] = self._byte_size
        return ret

class NodeAudio(NodeBlob):
    """Represents an audio blob."""
    def __init__(self):
        super(NodeAudio, self).__init__()
        self._length = 0

    def load(self, raw):
        super(NodeAudio, self).load(raw)
        self._length = raw['length']

    def save(self):
        ret = super(NodeAudio, self).save()
        ret['length'] = self._length
        return ret

class NodeImage(NodeBlob):
    """Represents an image blob."""
    def __init__(self):
        super(NodeImage, self).__init__()
        self._width = 0
        self._height = 0
        self._extracted_text = ''
        self._extraction_status = ''

    def load(self, raw):
        super(NodeImage, self).load(raw)
        self._width = raw['width']
        self._height = raw['height']
        self._extracted_text = raw['extracted_text']
        self._extraction_status = raw['extraction_status']

    def save(self):
        ret = super(NodeImage, self).save()
        ret['width'] = self._width
        ret['height'] = self._height
        ret['extracted_text'] = self._extracted_text
        ret['extraction_status'] = self._extraction_status
        return ret

class NodeDrawing(NodeBlob):
    """Represents a drawing blob."""
    pass

class Blob(Node):
    """Represents a Google Keep blob."""
    def __init__(self, parent_id=None, **kwargs):
        super(Blob, self).__init__(type_=TYPE['BLOB'], parent_id=parent_id, **kwargs)
        self.blob = NodeBlob()

    @classmethod
    def from_json(cls, raw):
        """Helper to construct a blob from a dict.

        Args:
            raw (dict): Raw blob representation.

        Returns:
            NodeBlob: A NodeBlob object or None.
        """
        cls = None
        _type = raw.get('type')
        if _type == 'AUDIO':
            cls = NodeAudio
        elif _type == 'IMAGE':
            cls = NodeImage
        elif _type == 'DRAWING':
            cls = NodeDrawing

        if cls is None:
            logger.warning('Unknown blob type: %s', _type)
            return None
        blob = cls()
        blob.load(raw)
        return blob

    def load(self, raw):
        super(Blob, self).load(raw)
        self.blob = self.from_json(raw['blob'])

    def save(self):
        ret = super(Blob, self).save()
        ret['blob'] = self.blob.save()
        return ret

class Label(Element, TimestampsMixin):
    """Represents a label."""
    def __init__(self):
        super(Label, self).__init__()

        create_time = time.time()

        self.id = self._generateId(create_time)
        self._name = ''
        self.timestamps = NodeTimestamps(create_time)
        self._revision = 0
        self._merged = NodeTimestamps.int_to_dt(0)

    @classmethod
    def _generateId(cls, tz):
        return 'tag.%s.%x' % (
            ''.join([random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(12)]),
            int(tz * 1000)
        )

    def load(self, raw):
        super(Label, self).load(raw)
        self.id = raw['mainId']
        self._name = raw['name']
        self.timestamps.load(raw['timestamps'])
        self._revision = raw['revision']
        self._merged = NodeTimestamps.str_to_dt(raw['lastMerged'])

    def save(self):
        ret = super(Label, self).save()
        ret['mainId'] = self.id
        ret['name'] = self._name
        ret['timestamps'] = self.timestamps.save()
        ret['revision'] = self._revision
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
    def revision(self):
        """Get the revision.

        Returns:
            int: Revision.
        """
        return self._revision

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

def _instrument_load(cls):
    cls._load = cls.load # pylint: disable=protected-access
    def load(self, raw): # pylint: disable=missing-docstring
        self._load(raw) # pylint: disable=protected-access
        self._find_discrepancies(raw) # pylint: disable=protected-access
    cls.load = load

if DEBUG:
    _instrumentable_classes = [
        WebLink, Category, TaskAssist, NodeAnnotations, NodeTimestamps,
        NodeSettings, NodeLabels, Note, List, ListItem, NodeAudio,
        NodeImage, NodeDrawing, Blob, Label
    ]
    for icls in _instrumentable_classes:
        _instrument_load(icls)
