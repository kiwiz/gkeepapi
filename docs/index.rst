.. gkeepapi documentation master file, created by
   sphinx-quickstart on Sat Oct 14 10:43:15 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to gkeepapi's documentation!
====================================

.. contents::

**gkeepapi** is an unofficial client for programmatically interacting with Google Keep::

    keep = gkeepapi.Keep()
    keep.login('...', '...')

    note = gkeepapi.createNote('Todo', 'Eat breakfast')
    note.pinned = True
    note.color = gkeepapi.node.COLOR['RED']

    keep.sync()

    print note.title
    print note.text

The client is mostly complete and ready for use, but there are some hairy spots. In particular, the interface for manipulating labels and blobs is subject to change.

Client Usage
============

All interaction with Google Keep is done through a :py:class:`Keep` object, which is responsible for authenticating, syncing changes and tracking modifications.

Logging in
----------

gkeepapi leverages the mobile Google Keep API. To do so, it makes use of :py:mod:`gpsoauth`, which requires passing in the username and password. This was necessary as the API we're using is restricted to Google applications (put differently, there is no way to enable it on the Developer Console)::

    keep = gkeepapi.Keep()
    keep.login('...', '...')

Note: For accounts with Twofactor, you'll need to generate an app password.

Syncing
-------

gkeepapi automatically pulls down all notes after login. After making any local modifications to notes, make sure to call :py:meth:`Keep.sync` to update them on the server!::

    keep.sync()

Notes and Lists
===============

Notes and Lists are the primary types of notes visible to a Google Keep user. gkeepapi exposes these two notes via the :py:class:`Note` and :py:class:`List` classes. For Lists, there's also the :py:class:`ListItem` class.

Creating Notes
--------------

New notes are created with the :py:meth:`Keep.createNote` and :py:meth:`Keep.createList` methods. The :py:class:`Keep` object keeps track of these objects and, upon :py:meth:`Keep.sync`, will sync them if modifications have been made::

    gnote = keep.createNote('Title', 'Text')

    glist = keep.createList('Title', [
        ('Item 1', False) # Not checked
        ('Item 2', True)  # Checked
    ])

    # Sync up changes
    keep.sync()

Getting Notes
-------------

Notes can be retrieved via :py:meth:`Keep.get` by their ID (visible in the URL when selecting a Note in the webapp)::

    gnote = keep.get('...')

To fetch all notes, use :py:meth:`Keep.all`::

    gnotes = keep.all()

Searching for Notes
-------------------

Notes can be searched for via :py:meth:`Keep.find`::

    # Find by string
    gnotes = keep.find(query='Title')

    # Find by filter function
    gnotes = keep.find(func=lambda x: x.deleted and x.title == 'Title')

    # Find by labels
    gnotes = keep.find(labels=[keep.findLabel('todo')])

    # Find by colors
    gnotes = keep.find(colors=[gkeepapi.node.COLOR['WHITE']])

    # Find by pinned/archived/trashed state
    gnotes = keep.find(pinned=True, archived=False, trashed=False)

Manipulating Notes
------------------

Note objects have many attributes that can be directly get and set. Here is a non-comprehensive list of the more interesting ones.

Notes and Lists:

* :py:attr:`TopLevelNode.id` (Read only)
* :py:attr:`TopLevelNode.parent` (Read only)
* :py:attr:`TopLevelNode.title`
* :py:attr:`TopLevelNode.text`
* :py:attr:`TopLevelNode.color`
* :py:attr:`TopLevelNode.archived`
* :py:attr:`TopLevelNode.pinned`

ListItems:

* :py:attr:`TopLevelNode.id` (Read only)
* :py:attr:`TopLevelNode.parent` (Read only)
* :py:attr:`TopLevelNode.text`
* :py:attr:`TopLevelNode.checked`

Getting Note content
^^^^^^^^^^^^^^^^^^^^

Example usage::

    print gnote.title
    print gnote.text

Getting List content
^^^^^^^^^^^^^^^^^^^^

Retrieving the content of a list is slightly more nuanced as they contain multiple entries. To get a serialized version of the contents, simply access :py:attr:`List.text` as usual. To get the individual :py:class:`ListItem` objects, access :py:attr:`List.items`::

    # Serialized content
    print glist.text

    # ListItem objects
    glistitems = glist.items

Setting Note content
^^^^^^^^^^^^^^^^^^^^

Example usage::

    gnote.title = 'Title 2'
    gnote.text = 'Text 2'
    gnote.color = gkeepapi.node.COLOR['WHITE']
    gnote.archived = True
    gnote.pinned = False

Setting List content
^^^^^^^^^^^^^^^^^^^^

New items can be added via :py:meth:`List.add`::

    glist.add('Item 2', True)

Existing items can be retrieved and modified directly::

    glistitem = glist.all()[0]
    glistitem.text = 'Item 3'
    glistitem.checked = True

Or deleted::

   glistitem.delete()

Deleting Notes
--------------

The :py:meth:`TopLevelNode.delete` method marks the note for deletion.

    gnote.delete()
    glist.delete()

Labels
======

Labels are short identifiers that can be assigned to notes. Label management is a bit unweildy right now and is done via the :py:class:`Keep` object. Like notes, labels are automatically tracked and changes are synced to the server.

Getting Labels
--------------

Labels can be retrieved via :py:meth:`Keep.getLabel` by their ID::

    label = keep.getLabel('...')

To fetch all labels, use :py:meth:`Keep.labels`::

    labels = keep.labels()

Searching for Labels
--------------------

Most of the time, you'll want to find a label by name. For that, use :py:meth:`Keep.findLabel`::

    label = keep.findLabel('todo')

Regular expressions are also supported here::

    label = keep.findLabel(re.compile('^todo$'))

Creating Labels
---------------

New labels can be created with :py:meth:`Keep.createLabel`::

    label = keep.createLabel('todo')

Editing Labels
--------------

A label's name can be updated directly::

    label.name = 'later'

Deleting Labels
---------------

A label can be deleted with :py:meth:`Keep.deleteLabel`. This method ensures the label is removed from all notes::

    keep.deleteLabel(label)

Manipulating Labels on Notes
----------------------------

When working with labels and notes, the key point to remember is that we're always working with Label objects or IDs.

To add a label to a note::

    gnote.labels.add(label)

To check if a label is on a note::

    gnote.labels.get(label.id) != None

To remove a label from a note::

    gnote.labels.remove(label)

Annotations
===========

TODO

Settings
========

TODO

Timestamps
==========

TODO


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
