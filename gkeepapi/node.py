# -*- coding: utf-8 -*-
"""
.. moduleauthor:: Kai <z@kwi.li>
"""

import datetime
import logging
import time
import random

logger = logging.getLogger(__name__)

def from_json(raw):
    cls = None
    if raw['type'] == 'NOTE':
        cls = Note
    elif raw['type'] == 'LIST':
        cls = List
    elif raw['type'] == 'LIST_ITEM':
        cls = ListItem
    elif raw['type'] == 'BLOB':
        cls = Blob

    if cls is None:
        logger.warning('Unknown node type: %s', raw['type'])
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
    """
    Interface for elements that can be serialized and deserialized
    """
    def load(self, raw):
        raise NotImplementedError('Not implemented')

    def save(self):
        raise NotImplementedError('Not implemented')

class Annotation(Element):
    def __init__(self):
        self.id = self._generateAnnotationId()

    def load(self, raw):
        self.id = raw['id']

    def save(self):
        return {
            'id': self.id
        }

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
    def __init__(self):
        super(WebLink, self).__init__()
        self.title = ''
        self.url = ''
        self.image_url = ''
        self.provenance_url = ''
        self.description = ''

    def load(self, raw):
        super(WebLink, self).load(raw)
        self.title = raw['webLink']['title']
        self.url = raw['webLink']['url']
        self.image_url = raw['webLink']['imageUrl']
        self.provenance_url = raw['webLink']['provenanceUrl']
        self.description = raw['webLink']['description']

    def save(self):
        ret = super(WebLink, self).save()
        ret['webLink'] = {
            'title': self.title,
            'url': self.url,
            'imageUrl': self.image_url,
            'provenanceUrl': self.provenance_url,
            'description': self.description,
        }
        return ret

class Category(Annotation):
    def __init__(self):
        super(Category, self).__init__()
        self.category = None

    def load(self, raw):
        super(Category, self).load(raw)
        self.category = raw['topicCategory']['category']

    def save(self):
        ret = super(Category, self).save()
        ret['topicCategory'] = {
            'category': self.category
        }
        return ret

class Annotations(Element):
    def __init__(self):
        self._annotations = {}

    @classmethod
    def from_json(cls, raw):
        cls = None
        if 'webLink' in raw:
            cls = WebLink
        elif 'topicCategory' in raw:
            cls = Category

        if cls is None:
            logger.warning('Unknown annotation type: %s', raw.keys())
            return None
        annotation = cls()
        annotation.load(raw)
        return annotation

    def load(self, raw):
        self._annotations = {}
        if 'annotations' not in raw:
            return

        for raw_annotation in raw['annotations']:
            annotation = self.from_json(raw_annotation)
            self._annotations[annotation.id] = annotation

    def save(self):
        ret = {
            'kind': 'notes#annotationsGroup',
        }
        if len(self._annotations) > 0:
            # What about deleting annotations?
            for i in self._annotations:
                print i

            ret['annotations'] = [annotation.save() for annotation in self._annotations]
        return ret

    @property
    def category(self):
        cat = None
        for annotation in self._annotations.values():
            if isinstance(annotation, Category):
                cat = annotation.category
                break

        return cat

    @property
    def links(self):
        return [annotation for annotation in self._annotations.values()
            if isinstance(annotation, WebLink)
        ]

class Timestamps(Element):
    TZ_FMT = '%Y-%m-%dT%H:%M:%S.%fZ'

    def __init__(self, create_time):
        self.created = datetime.datetime.utcfromtimestamp(create_time)
        self.deleted = datetime.datetime.utcfromtimestamp(0)
        self.trashed = datetime.datetime.utcfromtimestamp(0)
        self.updated = datetime.datetime.utcfromtimestamp(create_time)
        self.edited = datetime.datetime.utcfromtimestamp(create_time)

    def load(self, raw):
        self.created = datetime.datetime.strptime(raw['created'], self.TZ_FMT)
        self.deleted = datetime.datetime.strptime(raw['deleted'], self.TZ_FMT) \
            if 'deleted' in raw else \
            datetime.datetime.utcfromtimestamp(0)
        self.trashed = datetime.datetime.strptime(raw['trashed'], self.TZ_FMT)
        self.updated = datetime.datetime.strptime(raw['updated'], self.TZ_FMT)
        self.edited = datetime.datetime.strptime(raw['userEdited'], self.TZ_FMT) \
            if 'userEdited' in raw else \
            datetime.datetime.utcfromtimestamp(0)

    def save(self):
        return {
            'type': 'notes#timestamps',
            'created': self.created.strftime(self.TZ_FMT),
            'deleted': self.deleted.strftime(self.TZ_FMT),
            'trashed': self.trashed.strftime(self.TZ_FMT),
            'updated': self.updated.strftime(self.TZ_FMT),
            'userEdited': self.edited.strftime(self.TZ_FMT),
        }

class Settings(Element):
    def __init__(self):
        self.new_listitem_placement = NEW_LISTITEM_PLACEMENT['BOTTOM']
        self.graveyard_state = GRAVEYARD_STATE['COLLAPSED']
        self.checked_listitems_policy = CHECKED_LISTITEMS_POLICY['GRAVEYARD']

    def load(self, raw):
        self.new_listitem_placement = raw['newListItemPlacement']
        self.graveyard_state = raw['graveyardState']
        self.checked_listitems_policy = raw['checkedListItemsPolicy']

    def save(self):
        return {
            'newListItemPlacement': self.new_listitem_placement,
            'graveyardState': self.graveyard_state,
            'checkedListItemsPolicy': self.checked_listitems_policy
        }

class Node(Element):
    def __init__(self, id_=None, type_=None, parent_id=None):
        create_time = time.time()

        self.dirty = True
        self.id = self._generateId(create_time) if id_ is None else id_
        self.server_id = None
        self.parent_id = parent_id
        self.type = type_
        self.timestamps = Timestamps(create_time)
        self.sort = random.randint(1000000000, 9999999999)
        self.version = 1
        self._text = ''
        self._children = {}

    @classmethod
    def _generateId(cls, tz):
        return '%x.%016x' % (
            tz * 1000,
            random.randint(0x0000000000000000, 0xffffffffffffffff)
        )

    def load(self, raw):
        if 'reminders' in raw:
            print raw['reminders']
            # FIXE
            # lastModifierEmail
            # roleInfo
            # timestamps.recentSharedChangesSeen
            # shareState
            # reminders
        assert(raw['type'] in TYPE.values())
        assert(raw['kind'] in ['notes#node'])
        self.dirty = False
        self.id = raw['id']
        self.server_id = raw['serverId'] if 'serverId' in raw else self.server_id
        self.parent_id = raw['parentId']
        self.timestamps.load(raw['timestamps'])
        self.sort = raw['sortValue'] if 'sortValue' in raw else self.sort
        self.version = raw['baseVersion']
        self._text = raw['text'] if 'text' in raw else ''

    def save(self):
        self.dirty = False
        ret = {
            'id': self.id,
            'kind': 'notes#node',
            'type': self.type,
            'parentId': self.parent_id,
            'timestamps': self.timestamps.save(),
            'sortValue': self.sort,
            'baseVersion': self.version,
            'text': self._text,
        }
        if self.server_id is not None:
            ret['serverId'] = self.server_id

        return ret

    def touch(self):
        self.dirty = True
        self.timestamps.updated = datetime.datetime.now()

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value
        self.timestamps.edited = datetime.datetime.now()
        self.touch()

    @property
    def children(self):
        return self._children.values()

    def get(self, node_id):
        return self._children.get(node_id)

    def append(self, node, dirty=False):
        self._children[node.id] = node
        if dirty:
            self.touch()

    def remove(self, node, dirty=False):
        if node.id in self._children:
            del self._children[node.id]
        # FIXME: Make sure to remove from parent
        if dirty:
            self.touch()

    @property
    def new(self):
        return self.server_id is None

class Root(Node):
    ID = 'root'
    def __init__(self):
        super(Root, self).__init__(id=self.ID)

class XNode(Node): # FIXME: Rename this!
    _TYPE = None
    def __init__(self, **kwargs):
        super(XNode, self).__init__(parent_id=Root.ID, **kwargs)
        self.color = COLOR['WHITE']
        self.archived = False
        self.pinned = False
        self.title = ''
        self.annotations = Annotations()
        self.settings = Settings()

    def load(self, raw):
        super(XNode, self).load(raw)
        self.color = raw['color'] if 'color' in raw else COLOR['WHITE']
        self.archived = raw['isArchived']
        self.pinned = raw['isPinned'] if 'isPinned' in raw else False
        self.title = raw['title']
        self.settings.load(raw['nodeSettings'])
        if 'annotationsGroup' in raw:
            self.annotations.load(raw['annotationsGroup'])

    def save(self):
        ret = super(XNode, self).save()
        ret['color'] = self.color
        ret['isArchived'] = self.archived
        ret['isPinned'] = self.pinned
        ret['title'] = self.title
        ret['nodeSettings'] = self.settings.save()
        ret['annotationsGroup'] = self.annotations.save()
        return ret

    @property
    def url(self):
        return 'https://keep.google.com/u/0/#' + self._TYPE + '/' + self.id

class Note(XNode):
    _TYPE = TYPE['NOTE']
    def __init__(self):
        super(Note, self).__init__(type=self._TYPE)

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
        self.timestamps.edited = datetime.datetime.now()
        self.touch()

class List(XNode):
    _TYPE = TYPE['LIST']
    def __init__(self):
        super(List, self).__init__(type=self._TYPE)

    def add(self, text, checked=False):
        node = ListItem(parent_id=self.id)
        node.checked = checked
        node.text = text
        self.append(node, True)
        return node

    @property
    def text(self):
        return '\n'.join((unicode(node) for node in self.children))

    @property
    def items(self):
        return [node for node in self.children if type(node) == ListItem]

class ListItem(Node):
    def __init__(self, parent_id=None):
        super(ListItem, self).__init__(type=TYPE['LISTITEM'], parent_id=parent_id)
        self.checked = False

    def load(self, raw):
        super(ListItem, self).load(raw)
        self.checked = raw['checked']

    def save(self):
        ret = super(ListItem, self).save()
        ret['checked'] = self.checked
        return ret

    def __str__(self):
        return u'%s %s' % (u'☑' if self.checked else u'☐', self.text)


class Blob(Node):
    def __init__(self, parent_id=None):
        super(Blob, self).__init__(type=TYPE['BLOB'], parent_id=parent_id)

    def load(self, raw):
        super(Blob, self).load(raw)
        self._raw = raw

    def save(self):
        super(Blob, self).save()
        return self._raw
