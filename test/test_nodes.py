# -*- coding: utf-8 -*-
import six
if six.PY2:
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')

import unittest
import logging

from gkeepapi import node, exception
from operator import attrgetter

logging.getLogger(node.__name__).addHandler(logging.NullHandler())

def generate_save_load(cls):
    """Constructs an empty object and clones it from the serialized representation."""
    a = cls()
    b = cls()
    b.load(a.save())
    return a.save(), b.save()

def clean_node(n):
    n.save()
    if isinstance(n, node.Node):
        for c in n.children:
            c.save()
    assert(not n.dirty)
    return n

class AnnotationTests(unittest.TestCase):
    def test_save_load(self):
        a, b = generate_save_load(node.Annotation)
        self.assertEqual(a, b)

        # Test WebLink
        a, b = generate_save_load(node.WebLink)
        self.assertEqual(a, b)

        # Test Category
        def Category():
            c = node.Category()
            c.category = node.CategoryValue.Books
            return c
        a, b = generate_save_load(Category)
        self.assertEqual(a, b)

        # Test TaskAssist
        a, b = generate_save_load(node.TaskAssist)
        self.assertEqual(a, b)

    def test_weblink_fields(self):
        n = node.WebLink()

        TITLE = 'Title'
        URL = 'https://url.url'
        IMAGEURL = 'https://img.url'
        PROVENANCEURL = 'https://provenance.url'
        DESCRIPTION = 'Description'

        clean_node(n)
        n.title = TITLE
        self.assertTrue(n.dirty)
        self.assertEqual(TITLE, n.title)

        clean_node(n)
        n.url = URL
        self.assertTrue(n.dirty)
        self.assertEqual(URL, n.url)

        clean_node(n)
        n.image_url = IMAGEURL
        self.assertTrue(n.dirty)
        self.assertEqual(IMAGEURL, n.image_url)

        clean_node(n)
        n.provenance_url = PROVENANCEURL
        self.assertTrue(n.dirty)
        self.assertEqual(PROVENANCEURL, n.provenance_url)

        clean_node(n)
        n.description = DESCRIPTION
        self.assertTrue(n.dirty)
        self.assertEqual(DESCRIPTION, n.description)

    def test_category_fields(self):
        n = node.Category()
        n.category = node.CategoryValue.TV

        CATEGORY = node.CategoryValue.Books

        clean_node(n)
        n.category = CATEGORY
        self.assertTrue(n.dirty)
        self.assertEqual(CATEGORY, n.category)

    def test_taskassist_fields(self):
        n = node.TaskAssist()

        SUGGEST = 'UNKNOWN'

        clean_node(n)
        n.suggest = SUGGEST
        self.assertTrue(n.dirty)
        self.assertEqual(SUGGEST, n.suggest)

class ContextTests(unittest.TestCase):
    def test_save_load(self):
        a, b = generate_save_load(node.Context)
        self.assertEqual(a, b)

    def test_subannotations(self):
        n = node.Context()

        URL = 'https://url.url'

        sub = node.WebLink()
        sub.id = None
        sub.url = URL

        n._entries['x'] = sub
        self.assertTrue(n.dirty)

        self.assertEqual([sub], list(n.all()))

        data = n.save()
        n.load(data)
        self.assertEqual(1, len(n.all()))

class NodeAnnotationsTests(unittest.TestCase):
    def test_save_load(self):
        a, b = generate_save_load(node.NodeAnnotations)
        self.assertEqual(a, b)

    def test_fields(self):
        n = node.NodeAnnotations()

        CATEGORY = node.CategoryValue.Books
        CATEGORY_2 = node.CategoryValue.TV

        clean_node(n)
        n.category = None
        self.assertTrue(n.dirty)
        self.assertEqual(None, n.category)

        sub = node.Category()
        sub.category = CATEGORY
        clean_node(sub)

        clean_node(n)
        n.append(sub)
        self.assertTrue(n.dirty)
        self.assertEqual(CATEGORY, n.category)

        clean_node(n)
        sub.category = CATEGORY_2
        self.assertTrue(n.dirty)
        self.assertEqual(CATEGORY_2, n.category)

        clean_node(n)
        n.remove(sub)
        self.assertTrue(n.dirty)

        self.assertEqual([], n.links)

        sub = node.WebLink()
        clean_node(sub)

        clean_node(n)
        n.append(sub)
        self.assertTrue(n.dirty)
        self.assertEqual([sub], n.links)
        self.assertEqual(1, len(n))

class NodeTimestampsTests(unittest.TestCase):
    def test_save_load(self):
        a, b = generate_save_load(node.NodeTimestamps)
        self.assertEqual(a, b)

    def test_fields(self):
        n = node.NodeTimestamps(0)

        TZ = node.NodeTimestamps.int_to_dt(0)

        clean_node(n)
        n.created = TZ
        self.assertTrue(n.dirty)
        self.assertEqual(TZ, n.created)

        clean_node(n)
        n.deleted = TZ
        self.assertTrue(n.dirty)
        self.assertEqual(TZ, n.deleted)

        clean_node(n)
        n.trashed = TZ
        self.assertTrue(n.dirty)
        self.assertEqual(TZ, n.trashed)

        clean_node(n)
        n.updated = TZ
        self.assertTrue(n.dirty)
        self.assertEqual(TZ, n.updated)

        clean_node(n)
        n.edited = TZ
        self.assertTrue(n.dirty)
        self.assertEqual(TZ, n.edited)

class NodeSettingsTests(unittest.TestCase):
    def test_save_load(self):
        a, b = generate_save_load(node.NodeSettings)
        self.assertEqual(a, b)

    def test_fields(self):
        n = node.NodeSettings()

        ITEMPLACEMENT = node.NewListItemPlacementValue.Bottom
        GRAVEYARDSTATE = node.GraveyardStateValue.Collapsed
        ITEMPOLICY = node.CheckedListItemsPolicyValue.Graveyard

        clean_node(n)
        n.new_listitem_placement = ITEMPLACEMENT
        self.assertTrue(n.dirty)
        self.assertEqual(ITEMPLACEMENT, n.new_listitem_placement)

        clean_node(n)
        n.graveyard_state = GRAVEYARDSTATE
        self.assertTrue(n.dirty)
        self.assertEqual(GRAVEYARDSTATE, n.graveyard_state)

        clean_node(n)
        n.checked_listitems_policy = ITEMPOLICY
        self.assertTrue(n.dirty)
        self.assertEqual(ITEMPOLICY, n.checked_listitems_policy)

class NodeLabelsTests(unittest.TestCase):
    def test_save_load(self):
        a, b = generate_save_load(node.NodeLabels)
        self.assertEqual(a, b)

    def test_fields(self):
        n = node.NodeLabels()

        LABEL = 'Label'

        sub = node.Label()
        sub.name = LABEL
        clean_node(sub)

        clean_node(n)
        n.add(sub)
        self.assertTrue(n.dirty)
        self.assertEqual(sub, n.get(sub.id))
        self.assertEqual([sub], n.all())
        self.assertEqual(1, len(n))

        clean_node(n)
        n.remove(sub)
        self.assertTrue(n.dirty)
        self.assertEqual([], n.all())

class NodeTests(unittest.TestCase):
    def test_save_load(self):
        a, b = generate_save_load(lambda: node.Node(type_=node.NodeType.Note))
        self.assertEqual(a, b)

        a, b = generate_save_load(lambda: node.TopLevelNode(type_=node.NodeType.Note))
        self.assertEqual(a, b)

        a, b = generate_save_load(node.Note)
        self.assertEqual(a, b)

        a, b = generate_save_load(node.List)
        self.assertEqual(a, b)

        a, b = generate_save_load(node.ListItem)
        self.assertEqual(a, b)

        # a, b = generate_save_load(node.Blob) # FIXME: Broken
        # self.assertEqual(a, b)

    def test_fields(self):
        n = node.Node(type_=node.NodeType.Note)

        TZ = node.NodeTimestamps.int_to_dt(0)
        SORT = 1
        TEXT = 'Text'
        ITEMPLACEMENT = node.NewListItemPlacementValue.Bottom

        clean_node(n)
        n.timestamps.created = TZ
        self.assertTrue(n.dirty)
        self.assertEqual(TZ, n.timestamps.created)

        clean_node(n)
        n.sort = SORT
        self.assertTrue(n.dirty)
        self.assertEqual(SORT, n.sort)

        clean_node(n)
        n.text = TEXT
        self.assertTrue(n.dirty)
        self.assertEqual(TEXT, n.text)

        clean_node(n)
        n.settings.new_listitem_placement = ITEMPLACEMENT
        self.assertTrue(n.dirty)
        self.assertEqual(ITEMPLACEMENT, n.settings.new_listitem_placement)

        clean_node(n)
        n.annotations.category = None
        self.assertTrue(n.dirty)
        self.assertEqual(None, n.annotations.category)

        sub = node.ListItem()
        clean_node(sub)

        clean_node(n)
        n.append(sub)
        self.assertTrue(n.dirty)

        clean_node(n)
        sub.text = TEXT
        self.assertTrue(n.dirty)

        clean_node(n)
        sub.delete()
        self.assertTrue(n.dirty)

    def test_delete(self):
        n = node.Node(type_=node.NodeType.Note)
        clean_node(n)

        n.delete()
        self.assertTrue(n.timestamps.deleted)
        self.assertTrue(n.dirty)

class RootTests(unittest.TestCase):
    def test_fields(self):
        r = node.Root()

        self.assertFalse(r.dirty)

class TestElement(node.Element, node.TimestampsMixin):
    def __init__(self):
        super(TestElement, self).__init__()
        self.timestamps = node.NodeTimestamps(0)

class TimestampsMixinTests(unittest.TestCase):
    def test_touch(self):
        n = TestElement()
        n.touch()
        self.assertTrue(n.dirty)
        self.assertTrue(n.timestamps.updated > node.NodeTimestamps.int_to_dt(0))
        self.assertTrue(n.timestamps.edited == node.NodeTimestamps.int_to_dt(0))

        n.touch(True)
        self.assertTrue(n.timestamps.updated > node.NodeTimestamps.int_to_dt(0))
        self.assertTrue(n.timestamps.edited > node.NodeTimestamps.int_to_dt(0))

    def test_deleted(self):
        n = TestElement()
        self.assertFalse(n.deleted)

        n.timestamps.deleted = None
        self.assertFalse(n.deleted)

        n.timestamps.deleted = node.NodeTimestamps.int_to_dt(0)
        self.assertFalse(n.deleted)

        n.timestamps.deleted = node.NodeTimestamps.int_to_dt(1)
        self.assertTrue(n.deleted)

    def test_trashed(self):
        n = TestElement()
        self.assertFalse(n.trashed)

        n.timestamps.trashed = None
        self.assertFalse(n.trashed)

        n.timestamps.trashed = node.NodeTimestamps.int_to_dt(0)
        self.assertFalse(n.trashed)

        n.timestamps.trashed = node.NodeTimestamps.int_to_dt(1)
        self.assertTrue(n.trashed)

    def test_trash(self):
        n = TestElement()

        clean_node(n)
        n.trash()

        self.assertTrue(n.timestamps.dirty)
        self.assertTrue(n.timestamps.trashed > node.NodeTimestamps.int_to_dt(0))

        clean_node(n)
        n.untrash()

        self.assertTrue(n.timestamps.dirty)
        self.assertIsNone(n.timestamps.trashed)

    def test_delete(self):
        n = TestElement()

        clean_node(n)
        n.delete()

        self.assertTrue(n.timestamps.dirty)
        self.assertTrue(n.timestamps.deleted > node.NodeTimestamps.int_to_dt(0))

        clean_node(n)
        n.undelete()

        self.assertTrue(n.timestamps.dirty)
        self.assertIsNone(n.timestamps.deleted)

class TopLevelNodeTests(unittest.TestCase):
    def test_fields(self):
        n = node.TopLevelNode(type_=node.NodeType.Note)

        COLOR = node.ColorValue.White
        ARCHIVED = True
        PINNED = True
        TITLE = 'Title'
        LABEL = 'x'

        clean_node(n)
        n.color = COLOR
        self.assertTrue(n.dirty)
        self.assertEqual(COLOR, n.color)

        clean_node(n)
        n.archived = ARCHIVED
        self.assertTrue(n.dirty)
        self.assertEqual(ARCHIVED, n.archived)

        clean_node(n)
        n.pinned = PINNED
        self.assertTrue(n.dirty)
        self.assertEqual(PINNED, n.pinned)

        clean_node(n)
        n.title = TITLE
        self.assertTrue(n.dirty)
        self.assertEqual(TITLE, n.title)

        l = node.Label()
        l.name = LABEL
        clean_node(l)

        clean_node(n)
        n.labels.add(l)
        self.assertTrue(n.dirty)

        b = node.Blob()
        clean_node(b)

        clean_node(n)
        n.append(b)
        self.assertEqual([b], n.blobs)

        clean_node(n)
        n.labels.remove(l)
        self.assertTrue(n.dirty)

class NoteTests(unittest.TestCase):
    def test_fields(self):
        n = node.Note(id_='3')

        TEXT = 'Text'

        clean_node(n)
        n.text = TEXT
        self.assertTrue(n.dirty)
        self.assertEqual(TEXT, n.text)

        self.assertEqual('https://keep.google.com/u/0/#NOTE/3', n.url)

    def test_str(self):
        n = node.Note()

        TITLE = 'Title'
        TEXT = 'Test'

        self.assertEqual('', n.text)

        n.title = TITLE
        n.text = TEXT
        self.assertEqual('%s\n%s' % (TITLE, TEXT), str(n))
        self.assertEqual(TEXT, n.text)

class ListTests(unittest.TestCase):
    def test_fields(self):
        n = node.List()

        TEXT = 'Text'

        clean_node(n)
        sub_a = n.add(TEXT, sort=1)
        sub_b = n.add(TEXT, True, sort=2)
        self.assertTrue(n.dirty)

        self.assertEqual([sub_b], n.checked)
        self.assertEqual([sub_a], n.unchecked)

    def test_indent(self):
        n = node.List()

        TEXT = 'Test'

        clean_node(n)
        sub_a = node.ListItem()
        clean_node(sub_a)

        sub_b = n.add(TEXT)
        clean_node(sub_b)

        with self.assertRaises(exception.InvalidException):
            sub_a.add(sub_b)

        sub_c = sub_b.add(TEXT)
        self.assertIsInstance(sub_c, node.ListItem)

        clean_node(sub_b)
        sub_a.indent(sub_b)
        self.assertFalse(sub_b.dirty)

        clean_node(sub_b)
        sub_a.dedent(sub_b)
        self.assertFalse(sub_b.dirty)

        clean_node(sub_c)
        sub_b.dedent(sub_c)
        self.assertTrue(sub_c.dirty)

    def test_sort_items(self):
        n = node.List()

        sub_a = n.add('a', sort=3)
        sub_b = n.add('b', sort=0)
        sub_c = n.add('c', sort=5)
        sub_d = n.add('d', sort=1)
        sub_e = n.add('e', sort=2)
        sub_f = n.add('f', sort=4)

        n.sort_items()

        self.assertEqual(sub_a.id, n.items[0].id)
        self.assertEqual(sub_b.id, n.items[1].id)
        self.assertEqual(sub_c.id, n.items[2].id)
        self.assertEqual(sub_d.id, n.items[3].id)
        self.assertEqual(sub_e.id, n.items[4].id)
        self.assertEqual(sub_f.id, n.items[5].id)

        n = node.List()

        sub_a = n.add('a', sort=3)
        sub_ba = sub_a.add('ba', sort=3)
        sub_aa = sub_a.add('aa', sort=2)
        sub_b = n.add('b', sort=4)
        sub_bd = sub_b.add('bd', sort=4)
        sub_bc = sub_b.add('bc', sort=3)

        n.sort_items()

        self.assertEqual(sub_a.id, n.items[0].id)
        self.assertEqual(sub_aa.id, n.items[1].id)
        self.assertEqual(sub_ba.id, n.items[2].id)
        self.assertEqual(sub_b.id, n.items[3].id)
        self.assertEqual(sub_bc.id, n.items[4].id)
        self.assertEqual(sub_bd.id, n.items[5].id)

        n = node.List()

        time_1 = n.add('test1')
        time_2 = n.add('test2')
        time_3 = n.add('test3')

        n.sort_items(key=attrgetter('timestamps.created'), reverse=True)

        self.assertEqual(time_3.id, n.items[0].id)
        self.assertEqual(time_2.id, n.items[1].id)
        self.assertEqual(time_1.id, n.items[2].id)

    def test_str(self):
        n = node.List()

        TITLE = 'Title'

        n.title = TITLE
        sub_a = n.add('a', sort=0)
        sub_b = n.add('b', sort=0)
        sub_c = n.add('c', sort=1)
        sub_d = n.add('d', sort=2)
        sub_e = n.add('e', sort=3)
        sub_f = n.add('f', sort=4)
        sub_g = n.add('g', sort=node.NewListItemPlacementValue.Bottom)

        sub_c.indent(sub_d)
        sub_f.indent(sub_e)

        n_str = '%s\n☐ f\n  ☐ e\n☐ c\n  ☐ d\n☐ a\n☐ b\n☐ g' % TITLE
        n_text = '☐ f\n  ☐ e\n☐ c\n  ☐ d\n☐ a\n☐ b\n☐ g'
        self.assertEqual(n_str, str(n))
        self.assertEqual(n_text, n.text)

class ListItemTests(unittest.TestCase):
    def test_fields(self):
        n = node.ListItem()

        TEXT = 'Text'
        CHECKED = False

        clean_node(n)
        n.text = TEXT
        self.assertTrue(n.dirty)
        self.assertEqual(TEXT, n.text)

        clean_node(n)
        n.checked = CHECKED
        self.assertTrue(n.dirty)
        self.assertEqual(CHECKED, n.checked)

class CollaboratorTests(unittest.TestCase):
    def test_save_load(self):
        a = node.NodeCollaborators()
        b = node.NodeCollaborators()
        b.load(*a.save())
        self.assertEqual(a.save(), b.save())

    def test_fields(self):
        n = node.TopLevelNode(type_=node.NodeType.Note)

        collab = 'user@google.com'

        clean_node(n)
        n.collaborators.add(collab)
        self.assertTrue(n.dirty)
        self.assertEqual(1, len(n.collaborators))

        clean_node(n)
        n.collaborators.remove(collab)
        self.assertTrue(n.dirty)


class BlobTests(unittest.TestCase):
    def test_save_load(self):
        a, b = generate_save_load(node.NodeImage)
        self.assertEqual(a, b)

        a, b = generate_save_load(node.NodeDrawing)
        self.assertEqual(a, b)

        a, b = generate_save_load(node.NodeAudio)
        self.assertEqual(a, b)

    def test_fields(self):
        # FIXME: Not implemented
        pass

class LabelTests(unittest.TestCase):
    def test_save_load(self):
        a, b = generate_save_load(node.Label)
        self.assertEqual(a, b)

    def test_fields(self):
        n = node.Label()

        NAME = 'name'
        CATEGORY_2 = node.CategoryValue.TV
        TZ = node.NodeTimestamps.int_to_dt(0)

        clean_node(n)
        n.name = NAME
        self.assertTrue(n.dirty)
        self.assertEqual(NAME, n.name)
        self.assertEqual(NAME, str(n))

        clean_node(n)
        n.merged = TZ
        self.assertTrue(n.dirty)
        self.assertEqual(TZ, n.merged)

class ElementTests(unittest.TestCase):
    def test_load(self):
        with self.assertRaises(exception.ParseException):
            node.Node().load({})

    def test_save(self):
        n = node.Element()
        data = n.save(False)

        self.assertIn('_dirty', data)

class LoadTests(unittest.TestCase):
    def test_load(self):
        self.assertIsNone(node.from_json({}))

        data = {
            'id': '',
            'parentId': '',
            'timestamps': {
                'created': '2000-01-01T00:00:00.000Z',
                'updated': '2000-01-01T00:00:00.000Z',
            },
            'nodeSettings': {
                'newListItemPlacement': 'TOP',
                'graveyardState': 'COLLAPSED',
                'checkedListItemsPolicy': 'DEFAULT',
            },
            'annotationsGroup': {},
            'kind': 'notes#node',
            'type': 'NOTE',
        }
        self.assertIsInstance(node.from_json(data), node.Note)

if __name__ == '__main__':
    unittest.main()
