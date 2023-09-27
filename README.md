gkeepapi
========

[![Documentation Status](https://readthedocs.org/projects/gkeepapi/badge/?version=latest)](http://gkeepapi.readthedocs.io/en/latest/?badge=latest)
[![Gitter chat](https://badges.gitter.im/gkeepapi/Lobby.png)](https://gitter.im/gkeepapi/Lobby)
[![Test Coverage](https://api.codeclimate.com/v1/badges/4386792a941a156a14f0/test_coverage)](https://codeclimate.com/github/kiwiz/gkeepapi/test_coverage)

## NOTICE: Google offers an official [API](https://developers.google.com/keep/api) which might be an option if you have an Enterprise account. 🎉

An unofficial client for the [Google Keep](https://keep.google.com) API.

```python
import gkeepapi

keep = gkeepapi.Keep()
success = keep.login('user@gmail.com', 'password')

note = keep.createNote('Todo', 'Eat breakfast')
note.pinned = True
note.color = gkeepapi.node.ColorValue.Red
keep.sync()
```

*gkeepapi is not supported nor endorsed by Google.*

The code is pretty stable at this point, but you should always make backups. The project is under development, so feel free to open an issue if you have questions, see any bugs or have a feature request. PRs are welcome too!

## Installation

`pip install gkeepapi`

## Documentation

The docs are available on [Read the Docs](https://gkeepapi.readthedocs.io/en/latest/).

## Todo (Open an issue if you'd like to help!)

- Reminders
    - `reminders`
- Figure out all possible values for `TaskAssist._suggest` (Same as CategoryValue?)
- Figure out all possible values for `NodeImage._extraction_status` (integer)
- Blobs (Drawings/Images/Recordings)
