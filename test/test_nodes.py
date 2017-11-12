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

        a, b = generate_save_load(node.WebLink)
        self.assertEqual(a, b)

        a, b = generate_save_load(node.Category)
        self.assertEqual(a, b)

    def test_weblink_dirty(self):
        n = node.WebLink()

        clean_node(n)
        n.title = ''
        self.assertTrue(n.dirty)

        clean_node(n)
        n.url = ''
        self.assertTrue(n.dirty)

        clean_node(n)
        n.image_url = None
        self.assertTrue(n.dirty)

        clean_node(n)
        n.provenance_url = ''
        self.assertTrue(n.dirty)

        clean_node(n)
        n.description = ''
        self.assertTrue(n.dirty)

    def test_category(self):
        n = node.Category()

        clean_node(n)
        n.category = None
        self.assertTrue(n.dirty)

    def test_taskassist(self):
        n = node.TaskAssist()

        clean_node(n)
        n.suggest = None
        self.assertTrue(n.dirty)

class NodeAnnotationsTests(unittest.TestCase):
    def test_save_load(self):
        a, b = generate_save_load(node.NodeAnnotations)
        self.assertEqual(a, b)

    def test_category(self):
        n = node.NodeAnnotations()
        self.assertIsNone(n.category)

        n.category = node.CATEGORY['BOOKS']
        self.assertEqual(n.category, node.CATEGORY['BOOKS'])

    def test_dirty(self):
        n = node.NodeAnnotations()

        clean_node(n)
        n.category = None
        self.assertTrue(n.dirty)

        sub = node.Category()
        clean_node(sub)

        clean_node(n)
        n.append(sub)
        self.assertTrue(n.dirty)

        clean_node(n)
        sub.category = None
        self.assertTrue(n.dirty)

        clean_node(n)
        n.remove(sub)
        self.assertTrue(n.dirty)

class NodeTimestampsTests(unittest.TestCase):
    def test_save_load(self):
        a, b = generate_save_load(node.NodeTimestamps)
        self.assertEqual(a, b)

    def test_dirty(self):
        n = node.NodeTimestamps(0)

        clean_node(n)
        n.created = node.NodeTimestamps.int_to_dt(0)
        self.assertTrue(n.dirty)

        clean_node(n)
        n.deleted = node.NodeTimestamps.int_to_dt(0)
        self.assertTrue(n.dirty)

        clean_node(n)
        n.trashed = node.NodeTimestamps.int_to_dt(0)
        self.assertTrue(n.dirty)

        clean_node(n)
        n.updated = node.NodeTimestamps.int_to_dt(0)
        self.assertTrue(n.dirty)

        clean_node(n)
        n.edited = node.NodeTimestamps.int_to_dt(0)
        self.assertTrue(n.dirty)

class NodeSettingsTests(unittest.TestCase):
    def test_save_load(self):
        a, b = generate_save_load(node.NodeSettings)
        self.assertEqual(a, b)

    def test_dirty(self):
        n = node.NodeSettings()

        clean_node(n)
        n.new_listitem_placement = node.NEW_LISTITEM_PLACEMENT['BOTTOM']
        self.assertTrue(n.dirty)

        clean_node(n)
        n.graveyard_state = node.GRAVEYARD_STATE['COLLAPSED']
        self.assertTrue(n.dirty)

        clean_node(n)
        n.checked_listitems_policy = node.CHECKED_LISTITEMS_POLICY['GRAVEYARD']
        self.assertTrue(n.dirty)

class NodeLabelsTests(unittest.TestCase):
    def test_save_load(self):
        a, b = generate_save_load(node.NodeLabels)
        self.assertEqual(a, b)

    def test_dirty(self):
        n = node.NodeLabels()

        sub = node.Label()
        sub.name = 'x'
        clean_node(sub)

        clean_node(n)
        n.add(sub)
        self.assertTrue(n.dirty)

        clean_node(n)
        n.remove(sub)
        self.assertTrue(n.dirty)

class NodeTests(unittest.TestCase):
    def test_save_load(self):
        a, b = generate_save_load(node.Node)
        self.assertEqual(a, b)

        a, b = generate_save_load(node.TopLevelNode)
        self.assertEqual(a, b)

        a, b = generate_save_load(node.Note)
        self.assertEqual(a, b)

        a, b = generate_save_load(node.List)
        self.assertEqual(a, b)

        a, b = generate_save_load(node.ListItem)
        self.assertEqual(a, b)

        # a, b = generate_save_load(node.Blob) # FIXME: Broken
        # self.assertEqual(a, b)

    def test_dirty(self):
        n = node.Node()

        clean_node(n)
        n.timestamps.created = node.NodeTimestamps.int_to_dt(0)
        self.assertTrue(n.dirty)

        clean_node(n)
        n.sort = 0
        self.assertTrue(n.dirty)

        clean_node(n)
        n.text = ''
        self.assertTrue(n.dirty)

        clean_node(n)
        n.settings.new_listitem_placement = node.NEW_LISTITEM_PLACEMENT['BOTTOM']
        self.assertTrue(n.dirty)

        clean_node(n)
        n.annotations.category = None
        self.assertTrue(n.dirty)

        sub = node.ListItem()
        clean_node(sub)

        clean_node(n)
        n.append(sub)
        self.assertTrue(n.dirty)

        clean_node(n)
        sub.text = ''
        self.assertTrue(n.dirty)

        clean_node(n)
        sub.delete()
        self.assertTrue(n.dirty)

    def test_delete(self):
        n = node.Node(type_='NOTE')
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
    def test_dirty(self):
        n = node.TopLevelNode()

        clean_node(n)
        n.color = node.COLOR['WHITE']
        self.assertTrue(n.dirty)

        clean_node(n)
        n.archived = True
        self.assertTrue(n.dirty)

        clean_node(n)
        n.pinned = True
        self.assertTrue(n.dirty)

        clean_node(n)
        n.title = ''
        self.assertTrue(n.dirty)

        l = node.Label()
        l.name = 'x'
        clean_node(l)

        clean_node(n)
        n.labels.add(l)
        self.assertTrue(n.dirty)

        clean_node(n)
        n.labels.remove(l)
        self.assertTrue(n.dirty)

class NoteTests(unittest.TestCase):
    def test_dirty(self):
        n = node.Note()

        clean_node(n)
        n.text = ''
        self.assertTrue(n.dirty)

class ListTests(unittest.TestCase):
    def test_dirty(self):
        n = node.List()

        clean_node(n)
        n.add('')
        self.assertTrue(n.dirty)

class ListItemTests(unittest.TestCase):
    def test_dirty(self):
        n = node.ListItem()

        clean_node(n)
        n.checked = True
        self.assertTrue(n.dirty)

class BlobTests(unittest.TestCase):
    def test_dirty(self):
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
