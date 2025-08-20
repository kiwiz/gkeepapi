.. gkeepapi documentation master file, created by
   sphinx-quickstart on Sat Oct 14 10:43:15 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.
.. py:currentmodule:: gkeepapi

Welcome to gkeepapi's documentation!
====================================

.. contents::

**gkeepapi** is an unofficial client for programmatically interacting with Google Keep::

    import gkeepapi

    # Obtain a master token for your account
    master_token = '...'

    keep = gkeepapi.Keep()
    keep.authenticate('user@gmail.com', master_token)

    note = keep.createNote('Todo', 'Eat breakfast')
    note.pinned = True
    note.color = gkeepapi.node.ColorValue.Red

    keep.sync()

    print(note.title)
    print(note.text)

The client is mostly complete and ready for use, but there are some hairy spots. In particular, the interface for manipulating labels and blobs is subject to change.

Client Usage
============

All interaction with Google Keep is done through a :py:class:`Keep` object, which is responsible for authenticating, syncing changes and tracking modifications.

Authenticating
--------------

The client uses the (private) mobile Google Keep API. A valid OAuth token is generated via :py:mod:`gpsoauth`, which requires a master token for the account. These tokens are so called because they have full access to your account. Protect them like you would a password::

    keep = gkeepapi.Keep()
    keep.authenticate('user@gmail.com', master_token)

Rather than storing the token in the script, consider using your platform secrets store::

    import keyring

    # To save the token
    # ...
    # keyring.set_password('google-keep-token', 'user@gmail.com', master_token)

    master_token = keyring.get_password("google-keep-token", "user@gmail.com")

There is also a deprecated :py:meth:`Keep.login` method which accepts a username and password. This is discouraged (and unlikely to work), due to increased security requirements on logins::

    keep.login('user@gmail.com', 'password')

Obtaining a Master Token
------------------------

Instructions can be found in the gpsoauth `documentation <https://github.com/simon-weber/gpsoauth#alternative-flow>`__. If you have Docker installed, the following one-liner prompts for the necessary information and outputs the token::

    docker run --rm -it --entrypoint /bin/sh python:3 -c 'pip install gpsoauth; python3 -c '\''print(__import__("gpsoauth").exchange_token(input("Email: "), input("OAuth Token: "), input("Android ID: ")))'\'


Syncing
-------

gkeepapi automatically pulls down all notes after authenticating. It takes care of refreshing API tokens, so there's no need to call :py:meth:`Keep.authenticate` again. After making any local modifications to notes, make sure to call :py:meth:`Keep.sync` to update them on the server!::

    keep.sync()

Caching notes
-------------

The initial sync can take a while, especially if you have a lot of notes. To mitigate this, you can serialize note data to a file. The next time your program runs, it can resume from this state. This is handled via :py:meth:`Keep.dump` and :py:meth:`Keep.restore`::

    # Store cache
    state = keep.dump()
    fh = open('state', 'w')
    json.dump(state, fh)

    # Load cache
    fh = open('state', 'r')
    state = json.load(fh)
    keep.restore(state)

You can also pass the state directly to the :py:meth:`Keep.authenticate` and the (deprecated) :py:meth:`Keep.login` methods::

    keep.authenticate(username, master_token, state=state)
    keep.login(username, password, state=state)

Notes and Lists
===============

Notes and Lists are the primary types of notes visible to a Google Keep user. gkeepapi exposes these two notes via the :py:class:`node.Note` and :py:class:`node.List` classes. For Lists, there's also the :py:class:`node.ListItem` class.

Creating Notes
--------------

New notes are created with the :py:meth:`Keep.createNote` and :py:meth:`Keep.createList` methods. The :py:class:`Keep` object keeps track of these objects and, upon :py:meth:`Keep.sync`, will sync them if modifications have been made::

    gnote = keep.createNote('Title', 'Text')

    glist = keep.createList('Title', [
        ('Item 1', False), # Not checked
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

* :py:attr:`node.TopLevelNode.id` (Read only)
* :py:attr:`node.TopLevelNode.parent` (Read only)
* :py:attr:`node.TopLevelNode.title`
* :py:attr:`node.TopLevelNode.text`
* :py:attr:`node.TopLevelNode.color`
* :py:attr:`node.TopLevelNode.archived`
* :py:attr:`node.TopLevelNode.pinned`
* :py:attr:`node.TopLevelNode.labels`
* :py:attr:`node.TopLevelNode.annotations`
* :py:attr:`node.TopLevelNode.timestamps` (Read only)
* :py:attr:`node.TopLevelNode.collaborators`
* :py:attr:`node.TopLevelNode.blobs` (Read only)
* :py:attr:`node.TopLevelNode.drawings` (Read only)
* :py:attr:`node.TopLevelNode.images` (Read only)
* :py:attr:`node.TopLevelNode.audio` (Read only)

ListItems:

* :py:attr:`node.TopLevelNode.id` (Read only)
* :py:attr:`node.TopLevelNode.parent` (Read only)
* :py:attr:`node.TopLevelNode.parent_item` (Read only)
* :py:attr:`node.TopLevelNode.indented` (Read only)
* :py:attr:`node.TopLevelNode.text`
* :py:attr:`node.TopLevelNode.checked`

Getting Note content
^^^^^^^^^^^^^^^^^^^^

Example usage::

    print gnote.title
    print gnote.text

Getting List content
^^^^^^^^^^^^^^^^^^^^

Retrieving the content of a list is slightly more nuanced as they contain multiple entries. To get a serialized version of the contents, simply access :py:attr:`node.List.text` as usual. To get the individual :py:class:`node.ListItem` objects, access :py:attr:`node.List.items`::

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

New items can be added via :py:meth:`node.List.add`::

    # Create a checked item
    glist.add('Item 2', True)

    # Create an item at the top of the list
    glist.add('Item 1', True, gkeepapi.node.NewListItemPlacementValue.Top)

    # Create an item at the bottom of the list
    glist.add('Item 3', True, gkeepapi.node.NewListItemPlacementValue.Bottom)

Existing items can be retrieved and modified directly::

    glistitem = glist.items[0]
    glistitem.text = 'Item 4'
    glistitem.checked = True

Or deleted via :py:meth:`node.ListItem.delete`::

   glistitem.delete()

Setting List item position
^^^^^^^^^^^^^^^^^^^^^^^^^^

To reposition an item (larger is closer to the top)::

   # Set a specific sort id
   glistitem1.sort = 42

   # Swap the position of two items
   val = glistitem2.sort
   glistitem2.sort = glistitem3.sort
   glistitem3.sort = val

Sorting a List
^^^^^^^^^^^^^^

Lists can be sorted via :py:meth:`node.List.sort_items`::

   # Sorts items alphabetically by default
   glist.sort_items()

Indent/dedent List items
^^^^^^^^^^^^^^^^^^^^^^^^

To indent a list item::

    gparentlistitem.indent(gchildlistitem)

To dedent::

    gparentlistitem.dedent(gchildlistitem)

Deleting Notes
--------------

The :py:meth:`node.TopLevelNode.delete` method marks the note for deletion (or undo)::

    gnote.delete()
    gnote.undelete()

To send the node to the trash instead (or undo)::

    gnote.trash()
    gnote.untrash()

Media
=====

Media blobs are images, drawings and audio clips that are attached to notes.

Accessing media
---------------

Drawings:

* :py:attr:`node.NodeDrawing.extracted_text` (Read only)

Images:

* :py:attr:`node.NodeImage.width` (Read only)
* :py:attr:`node.NodeImage.height` (Read only)
* :py:attr:`node.NodeImage.byte_size` (Read only)
* :py:attr:`node.NodeImage.extracted_text` (Read only)

Audio:

* :py:attr:`node.NodeAudio.length` (Read only)

Fetching media
--------------

To download media, you can use the :py:meth:`Keep.getMediaLink` method to get a link::

    blob = gnote.images[0]
    keep.getMediaLink(blob)

Labels
======

Labels are short identifiers that can be assigned to notes. Labels are exposed via the :py:class:`node.Label` class. Management is a bit unwieldy right now and is done via the :py:class:`Keep` object. Like notes, labels are automatically tracked and changes are synced to the server.

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

When working with labels and notes, the key point to remember is that we're always working with :py:class:`node.Label` objects or IDs. Interaction is done through the :py:class:`node.NodeLabels` class.

To add a label to a note::

    gnote.labels.add(label)

To check if a label is on a note::

    gnote.labels.get(label.id) != None

To remove a label from a note::

    gnote.labels.remove(label)

Constants
=========

- :py:class:`node.ColorValue` enumerates valid colors.
- :py:class:`node.CategoryValue` enumerates valid note categories.
- :py:class:`node.CheckedListItemsPolicyValue` enumerates valid policies for checked list items.
- :py:class:`node.GraveyardStateValue` enumerates valid visibility settings for checked list items.
- :py:class:`node.NewListItemPlacementValue` enumerates valid locations for new list items.
- :py:class:`node.NodeType` enumerates valid node types.
- :py:class:`node.BlobType` enumerates valid blob types.
- :py:class:`node.RoleValue` enumerates valid collaborator permissions.
- :py:class:`node.ShareRequestValue` enumerates vaild collaborator modification requests.
- :py:class:`node.SuggestValue` enumerates valid suggestion types.

Annotations
===========

READ ONLY
TODO

Settings
========

TODO

Collaborators
=============

Collaborators are users you've shared notes with. Access can be granted or revoked per note. Interaction is done through the :py:class:`node.NodeCollaborators` class.

To add a collaborator to a note::

    gnote.collaborators.add(email)

To check if a collaborator has access to a note::

    email in gnote.collaborators.all()

To remove a collaborator from a note::

    gnote.collaborators.remove(email)

Timestamps
==========

All notes and lists have a :py:class:`node.NodeTimestamps` object with timestamp data::

    node.timestamps.created
    node.timestamps.deleted
    node.timestamps.trashed
    node.timestamps.updated
    node.timestamps.edited

These timestamps are all read-only.

FAQ
===

1. I get a "NeedsBrowser", "CaptchaRequired" or "BadAuthentication" :py:class:`exception.LoginException` when I try to log in. (Not an issue when using :py:meth:`Keep.authenticate`)

This usually occurs when Google thinks the login request looks suspicious. Here are some steps you can take to resolve this:

- Make sure you have the newest version of gkeepapi installed.
- Instead of logging in every time, cache the authentication token and reuse it on subsequent runs. See `here <https://github.com/kiwiz/keep-cli/blob/master/src/keep_cli/__main__.py#L106-L128>`__ for an example implementation.
- Upgrading to a newer version of Python (3.7+) has worked for some people. See this `issue <https://gitlab.com/AuroraOSS/AuroraStore/issues/217#note_249390026>`__ for more information.
- If all else fails, try testing gkeepapi on a separate IP address and/or user to see if you can isolate the problem.

2. I get a "DeviceManagementRequiredOrSyncDisabled" :py:class:`exception.LoginException` when I try to log in. (Not an issue when using :py:meth:`Keep.authenticate`)

This is due to the enforcement of Android device policies on your G-Suite account. To resolve this, you can try disabling that setting `here <https://admin.google.com/AdminHome?hl=no#MobileSettings:section=advanced&flyout=security>`__.

3. My notes take a long time to sync

Follow the instructions in the caching notes section and see if that helps. If you only need to update notes, you can try creating a new Google account. Share the notes to the new account and manage through there.

Known Issues
============

1. :py:class:`node.ListItem` consistency

The :py:class:`Keep` class isn't aware of new :py:class:`node.ListItem` objects till they're synced up to the server. In other words, :py:meth:`Keep.get` calls for their IDs will fail.

Debug
=====

To enable development debug logs::

    gkeepapi.node.DEBUG = True

Notes
=====

- Many sub-elements are read only.
- :py:class:`node.Node` specific :py:class:`node.NewListItemPlacementValue` settings are not used.

Reporting errors
----------------

Google occasionally ramps up changes to the Keep data format. When this happens, you'll likely get a :py:class:`exception.ParseException`. Please report this on Github with the raw data, which you can grab like so::

    try:
        # Code that raises the exception
    except gkeepapi.exception.ParseException as e:
        print(e.raw)

If you're not getting an :py:class:`exception.ParseException`, just a log line, make sure you've enabled debug mode.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
