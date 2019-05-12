gkeepapi
========

[![Documentation Status](https://readthedocs.org/projects/gkeepapi/badge/?version=latest)](http://gkeepapi.readthedocs.io/en/latest/?badge=latest)
[![Build Status](https://travis-ci.org/kiwiz/gkeepapi.svg?branch=master)](https://travis-ci.org/kiwiz/gkeepapi)
[![Gitter chat](https://badges.gitter.im/gkeepapi/Lobby.png)](https://gitter.im/gkeepapi/Lobby)
[![Test Coverage](https://api.codeclimate.com/v1/badges/4386792a941a156a14f0/test_coverage)](https://codeclimate.com/github/kiwiz/gkeepapi/test_coverage)

An unofficial client for the [Google Keep](https://keep.google.com) API.

```
import gkeepapi

keep = gkeepapi.Keep()
success = keep.login('...', '...')

note = keep.createNote('Todo', 'Eat breakfast')
note.pinned = True
note.color = gkeepapi.node.ColorValue.Red
keep.sync()
```

*gkeepapi is not supported nor endorsed by Google.*

This is beta quality code! Don't use in production. The project is under active development, so feel free to open an issue if you have questions, see any bugs or have a feature request. PRs are welcome too!

## Installation

`pip install gkeepapi`

## Documentation

The docs are available on [Read the Docs](https://gkeepapi.readthedocs.io/en/latest/).

## Todo (Open an issue if you'd like to help!)

- Determine how `forceFullSync` works.
- Reminders
    - `reminders`
- Figure out all possible values for `TaskAssist._suggest`
- Figure out all possible values for `NodeImage._extraction_status`
- Blobs (Drawings/Images/Recordings)
