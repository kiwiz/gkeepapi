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
    note.color = gkeepapi.node.ColorValue.Red

    keep.sync()

    print note.title
    print note.text

The client is mostly complete and ready for use, but there are some hairy spots. In particular, the interface for manipulating labels and blobs is subject to change.

Client Usage
============

All interaction with Google Keep is done through a :py:class:`gkeepapi.Keep` object, which is responsible for authenticating, syncing changes and tracking modifications.

Logging in
----------

gkeepapi leverages the mobile Google Keep API. To do so, it makes use of :py:mod:`gpsoauth`, which requires passing in the username and password. This was necessary as the API we're using is restricted to Google applications (put differently, there is no way to enable it on the Developer Console)::

    keep = gkeepapi.Keep()
    keep.login('...', '...')

To reduce the number of logins you make to the server, you can store the master token after logging in. Protect this like a password, as it grants full access to your account::

    import keyring
    # <snip>
    token = keep.getMasterToken()
    keyring.set_password('google-keep-token', username, token)

You can load this token at a later point::

    import keyring
    # <snip>
    token = keyring.get_password('google-keep-token', username)
    keep.resume(email, master_token)

Note: Enabling TwoFactor and logging via an app password is recommended.

Syncing
-------

gkeepapi automatically pulls down all notes after login. It takes care of refreshing API tokens, so there's no need to call :py:meth:`Keep.login` again. After making any local modifications to notes, make sure to call :py:meth:`Keep.sync` to update them on the server!::

    keep.sync()

Caching notes
-------------

The initial sync can take a while, especially if you have a lot of notes. To mitigate this, you can serialize note data to a file. The next time your program runs, it can resume from this state::

    # Store cache
    state = keep.dump()
    fh = open('state', 'w')
    json.dump(state, fh)

    # Load cache
    fh = open('state', 'r')
    state = json.load(fh)
    keep.restore(state)

You can also pass the state directly to the :py:meth:`Keep.login` and :py:meth:`Keep.resume` methods::

    keep.login(username, password, state=state)
    keep.resume(username, master_token, state=state)

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
    gnotes = keep.find(colors=[gkeepapi.node.ColorValue.White])

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
* :py:attr:`TopLevelNode.deleted`

ListItems:

* :py:attr:`TopLevelNode.id` (Read only)
* :py:attr:`TopLevelNode.parent` (Read only)
* :py:attr:`TopLevelNode.parent_item` (Read only)
* :py:attr:`TopLevelNode.indented` (Read only)
* :py:attr:`TopLevelNode.text`
* :py:attr:`TopLevelNode.checked`
* :py:attr:`TopLevelNode.deleted`

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

    # Checked ListItems
    cglistitems = glist.checked

    # Unchecked ListItems
    uglistitems = glist.unchecked

Setting Note content
^^^^^^^^^^^^^^^^^^^^

Example usage::

    gnote.title = 'Title 2'
    gnote.text = 'Text 2'
    gnote.color = gkeepapi.node.ColorValue.White
    gnote.archived = True
    gnote.pinned = False

Setting List content
^^^^^^^^^^^^^^^^^^^^

New items can be added via :py:meth:`List.add`::

    glist.add('Item 2', True)

Existing items can be retrieved and modified directly::

    glistitem = glist.items[0]
    glistitem.text = 'Item 3'
    glistitem.checked = True

Or deleted::

   glistitem.delete()

Indent/dedent List items
^^^^^^^^^^^^^^^^^^^^^^^^

To indent a list item::

    gparentlistitem.indent(gchildlistitem)

To dedent::

    gparentlistitem.dedent(gchildlistitem)

Deleting Notes
--------------

The :py:meth:`TopLevelNode.delete` method marks the note for deletion::

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

Constants
=========

TODO

Annotations
===========

TODO

Settings
========

TODO

Timestamps
==========

All notes and lists have a `NodeTimestamps` object with timestamp data::

    node.timestamps.created
    node.timestamps.deleted
    node.timestamps.trashed
    node.timestamps.updated
    node.timestamps.edited

These timestamps are all modifiable, but are automatically managed by the client.

FAQ
===

1. I get a "NeedsBrowser" `APIException` when I try to log in.

Your account probably has Two Factor enabled. To get around this, you'll need to generate an App Password for your Google account.

Known Issues
============

The :py:class:`gkeepapi.Keep` class isn't aware of new :py:class:`ListItem` objects till they're synced up to the server. In other words, :py:meth:`Keep.get`:: calls for their IDs will fail.

Debug
=====

To enable development debug logs::

    gkeepapi.node.DEBUG = True

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
