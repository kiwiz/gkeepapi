gkeepapi
========

[![Documentation Status](https://readthedocs.org/projects/gkeepapi/badge/?version=latest)](http://gkeepapi.readthedocs.io/en/latest/?badge=latest)
[![Build Status](https://travis-ci.org/kiwiz/gkeepapi.svg?branch=master)](https://travis-ci.org/kiwiz/gkeepapi)

An unofficial client for the [Google Keep](https://keep.google.com) API.

```
import gkeepapi

keep = gkeepapi.Keep()
success = keep.login('...', '...')

note = keep.createNote('Todo', 'Eat breakfast')
note.pinned = True
note.color = gkeepapi.node.COLOR['RED']
keep.sync()
```

*gkeepapi is not supported nor endorsed by Google.*

This is alpha quality code! Don't use in production. The project is under active development, so feel free to open an issue if you see any bugs or have a feature request. PRs are welcome too!

## Documentation

The docs are available on [Read the Docs](https://gkeepapi.readthedocs.io/en/latest/).

## Todo (Open an issue if you'd like to help!)

- Determine how `forceFullSync` works.
- Reminders
    - `reminders`
- Sharing Notes
    - `lastModifierEmail`, `roleInfo`, `timestamps.recentSharedChangesSeen`, `shareState`
- Figure out all possible values for `TaskAssist._suggest`
- Figure out all possible values for `NodeImage._extraction_status`
- Blobs (Drawings/Images/Recordings)
