# -*- coding: utf-8 -*-
import unittest
import logging

from gkeepapi import node

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
        sub = node.WebLink()
        sub.id = None

        n._entries['x'] = sub

        data = n.save()

        n.load(data)
        self.assertEqual(1, len(n._entries))

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
        # FIXME: Node is not done

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

    def test_delete(self):
        n = TestElement()
        n.delete()

        self.assertTrue(n.timestamps.dirty)
        self.assertTrue(n.timestamps.deleted > node.NodeTimestamps.int_to_dt(0))

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

class ListTests(unittest.TestCase):
    def test_fields(self):
        n = node.List()

        TEXT = 'Text'

        clean_node(n)
        n.add('Text')
        self.assertTrue(n.dirty)
        self.assertEqual(u'☐ %s' % TEXT, n.text)

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

    # FIXME: Not implemented
    pass

if __name__ == '__main__':
    unittest.main()
