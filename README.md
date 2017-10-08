gkeepapi
========

```
import gkeepapi

keep = gkeepapi.Keep()
success = keep.login('...', '...')
keep.sync()

note = gkeepapi.Note()
note.title = 'Todo'
note.text = 'Eat breakfast'
note.pinned = True
note.color = gkeepapi.COLOR.RED
keep.add(note)
keep.sync()
```

# Todo

[ ] Calling sync before login
[ ] Dirtiness isn't propagated correctly
[-] Adding/Editng/Deleting children
    [-] List/Annotations
[-] Conflicts
[ ] Label
    [ ] Parse
    [ ] Generate
    [ ] Delete
[ ] Tests

# Issues

[ ] How does `forceFullSync` work?


# Not implemented

- Sharing
- Reminders
- Blobs (Drawings/Images/Recordings)
