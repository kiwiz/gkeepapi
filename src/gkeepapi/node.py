""".. automodule:: gkeepapi

   :members:
   :inherited-members:

.. moduleauthor:: Kai <z@kwi.li>
"""

import datetime
import enum
import itertools
import logging
import random
import time
from collections.abc import Callable
from operator import attrgetter

from . import exception

DEBUG = False

logger = logging.getLogger(__name__)


class NodeType(enum.Enum):
    """Valid note types."""

    Note = "NOTE"
    """A Note"""

    List = "LIST"
    """A List"""

    ListItem = "LIST_ITEM"
    """A List item"""

    Blob = "BLOB"
    """A blob (attachment)"""


class BlobType(enum.Enum):
    """Valid blob types."""

    Audio = "AUDIO"
    """Audio"""

    Image = "IMAGE"
    """Image"""

    Drawing = "DRAWING"
    """Drawing"""


class ColorValue(enum.Enum):
    """Valid note colors."""

    White = "DEFAULT"
    """White"""

    Red = "RED"
    """Red"""

    Orange = "ORANGE"
    """Orange"""

    Yellow = "YELLOW"
    """Yellow"""

    Green = "GREEN"
    """Green"""

    Teal = "TEAL"
    """Teal"""

    Blue = "BLUE"
    """Blue"""

    DarkBlue = "CERULEAN"
    """Dark blue"""

    Purple = "PURPLE"
    """Purple"""

    Pink = "PINK"
    """Pink"""

    Brown = "BROWN"
    """Brown"""

    Gray = "GRAY"
    """Gray"""


class CategoryValue(enum.Enum):
    """Valid note categories."""

    Books = "BOOKS"
    """Books"""

    Food = "FOOD"
    """Food"""

    Movies = "MOVIES"
    """Movies"""

    Music = "MUSIC"
    """Music"""

    Places = "PLACES"
    """Places"""

    Quotes = "QUOTES"
    """Quotes"""

    Travel = "TRAVEL"
    """Travel"""

    TV = "TV"
    """TV"""


class SuggestValue(enum.Enum):
    """Valid task suggestion categories."""

    GroceryItem = "GROCERY_ITEM"
    """Grocery item"""


class NewListItemPlacementValue(enum.Enum):
    """Target location to put new list items."""

    Top = "TOP"
    """Top"""

    Bottom = "BOTTOM"
    """Bottom"""


class GraveyardStateValue(enum.Enum):
    """Visibility setting for the graveyard."""

    Expanded = "EXPANDED"
    """Expanded"""

    Collapsed = "COLLAPSED"
    """Collapsed"""


class CheckedListItemsPolicyValue(enum.Enum):
    """Movement setting for checked list items."""

    Default = "DEFAULT"
    """Default"""

    Graveyard = "GRAVEYARD"
    """Graveyard"""


class ShareRequestValue(enum.Enum):
    """Collaborator change type."""

    Add = "WR"
    """Grant access."""

    Remove = "RM"
    """Remove access."""


class RoleValue(enum.Enum):
    """Collaborator role type."""

    Owner = "O"
    """Note owner."""

    User = "W"
    """Note collaborator."""


class Element:
    """Interface for elements that can be serialized and deserialized."""

    __slots__ = ("_dirty",)

    def __init__(self) -> None:
        """Construct an element object"""
        self._dirty = False

    def _find_discrepancies(self, raw: dict | list) -> None:  # pragma: no cover
        s_raw = self.save(False)
        if isinstance(raw, dict):
            for key, val in raw.items():
                if key in ["parentServerId", "lastSavedSessionId"]:
                    continue
                if key not in s_raw:
                    logger.info("Missing key for %s key %s", type(self), key)
                    continue

                if isinstance(val, list | dict):
                    continue

                val_a = raw[key]
                val_b = s_raw[key]
                # Python strftime's 'z' format specifier includes microseconds, but the response from GKeep
                # only has milliseconds. This causes a string mismatch, so we construct datetime objects
                # to properly compare
                if isinstance(val_a, str) and isinstance(val_b, str):
                    try:
                        tval_a = NodeTimestamps.str_to_dt(val_a)
                        tval_b = NodeTimestamps.str_to_dt(val_b)
                        val_a, val_b = tval_a, tval_b
                    except (KeyError, ValueError):
                        pass
                if val_a != val_b:
                    logger.info(
                        "Different value for %s key %s: %s != %s",
                        type(self),
                        key,
                        raw[key],
                        s_raw[key],
                    )
        elif isinstance(raw, list) and len(raw) != len(s_raw):
            logger.info(
                "Different length for %s: %d != %d",
                type(self),
                len(raw),
                len(s_raw),
            )

    def load(self, raw: dict) -> None:
        """Unserialize from raw representation. (Wrapper)

        Args:
            raw: Raw.


        Raises:
            ParseException: If there was an error parsing data.
        """
        try:
            self._load(raw)
        except (KeyError, ValueError) as e:
            raise exception.ParseException(f"Parse error in {type(self)}", raw) from e

    def _load(self, raw: dict) -> None:
        """Unserialize from raw representation. (Implementation logic)

        Args:
            raw: Raw.
        """
        self._dirty = raw.get("_dirty", False)

    def save(self, clean: bool = True) -> dict:
        """Serialize into raw representation. Clears the dirty bit by default.

        Args:
            clean: Whether to clear the dirty bit.

        Returns:
            Raw.
        """
        ret = {}
        if clean:
            self._dirty = False
        else:
            ret["_dirty"] = self._dirty
        return ret

    @property
    def dirty(self) -> bool:
        """Get dirty state.

        Returns:
            Whether this element is dirty.
        """
        return self._dirty


class Annotation(Element):
    """Note annotations base class."""

    __slots__ = ("id",)

    def __init__(self) -> None:
        """Construct a note annotation"""
        super().__init__()
        self.id = self._generateAnnotationId()

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self.id = raw.get("id")

    def save(self, clean: bool = True) -> dict:
        """Save the annotation"""
        ret = {}
        if self.id is not None:
            ret = super().save(clean)
        if self.id is not None:
            ret["id"] = self.id
        return ret

    @classmethod
    def _generateAnnotationId(cls) -> str:
        return "{:08x}-{:04x}-{:04x}-{:04x}-{:012x}".format(  # noqa: UP032
            random.randint(0x00000000, 0xFFFFFFFF),  # noqa: S311
            random.randint(0x0000, 0xFFFF),  # noqa: S311
            random.randint(0x0000, 0xFFFF),  # noqa: S311
            random.randint(0x0000, 0xFFFF),  # noqa: S311
            random.randint(0x000000000000, 0xFFFFFFFFFFFF),  # noqa: S311
        )


class WebLink(Annotation):
    """Represents a link annotation on a :class:`TopLevelNode`."""

    __slots__ = ("_title", "_url", "_image_url", "_provenance_url", "_description")

    def __init__(self) -> None:
        """Construct a weblink"""
        super().__init__()
        self._title = None
        self._url = ""
        self._image_url = None
        self._provenance_url = ""
        self._description = None

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self._title = raw["webLink"].get("title", self.title)
        self._url = raw["webLink"]["url"]
        self._image_url = raw["webLink"].get("imageUrl", self.image_url)
        self._provenance_url = raw["webLink"]["provenanceUrl"]
        self._description = raw["webLink"].get("description", self.description)

    def save(self, clean: bool = True) -> dict:
        """Save the weblink"""
        ret = super().save(clean)
        ret["webLink"] = {
            "title": self._title,
            "url": self._url,
            "imageUrl": self._image_url,
            "provenanceUrl": self._provenance_url,
            "description": self._description,
        }
        return ret

    @property
    def title(self) -> str | None:
        """Get the link title.

        Returns:
            The link title or None.
        """
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = value
        self._dirty = True

    @property
    def url(self) -> str:
        """Get the link url.

        Returns:
            The link url.
        """
        return self._url

    @url.setter
    def url(self, value: str) -> None:
        self._url = value
        self._dirty = True

    @property
    def image_url(self) -> str | None:
        """Get the link image url.

        Returns:
            The image url or None.
        """
        return self._image_url

    @image_url.setter
    def image_url(self, value: str) -> None:
        self._image_url = value
        self._dirty = True

    @property
    def provenance_url(self) -> str:
        """Get the provenance url.

        Returns:
            The provenance url.
        """
        return self._provenance_url

    @provenance_url.setter
    def provenance_url(self, value: str) -> None:
        self._provenance_url = value
        self._dirty = True

    @property
    def description(self) -> str | None:
        """Get the link description.

        Returns:
            The link description or None.
        """
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = value
        self._dirty = True


class Category(Annotation):
    """Represents a category annotation on a :class:`TopLevelNode`."""

    __slots__ = ("_category",)

    def __init__(self) -> None:
        """Construct a category annotation"""
        super().__init__()
        self._category = None

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self._category = CategoryValue(raw["topicCategory"]["category"])

    def save(self, clean: bool = True) -> dict:
        """Save the category annotation"""
        ret = super().save(clean)
        ret["topicCategory"] = {"category": self._category.value}
        return ret

    @property
    def category(self) -> CategoryValue:
        """Get the category.

        Returns:
            The category.
        """
        return self._category

    @category.setter
    def category(self, value: CategoryValue) -> None:
        self._category = value
        self._dirty = True


class TaskAssist(Annotation):
    """Unknown."""

    __slots__ = ("_suggest",)

    def __init__(self) -> None:
        """Construct a taskassist annotation"""
        super().__init__()
        self._suggest = None

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self._suggest = raw["taskAssist"]["suggestType"]

    def save(self, clean: bool = True) -> dict:
        """Save the taskassist annotation"""
        ret = super().save(clean)
        ret["taskAssist"] = {"suggestType": self._suggest}
        return ret

    @property
    def suggest(self) -> str:
        """Get the suggestion.

        Returns:
            The suggestion.
        """
        return self._suggest

    @suggest.setter
    def suggest(self, value: str) -> None:
        self._suggest = value
        self._dirty = True


class Context(Annotation):
    """Represents a context annotation, which may contain other annotations."""

    __slots__ = ("_entries",)

    def __init__(self) -> None:
        """Construct a context annotation"""
        super().__init__()
        self._entries = {}

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self._entries = {}
        for key, entry in raw.get("context", {}).items():
            self._entries[key] = NodeAnnotations.from_json({key: entry})

    def save(self, clean: bool = True) -> dict:
        """Save the context annotation"""
        ret = super().save(clean)
        context = {}
        for entry in self._entries.values():
            context.update(entry.save(clean))
        ret["context"] = context
        return ret

    def all(self) -> list[Annotation]:
        """Get all sub annotations.

        Returns:
            Sub Annotations.
        """
        return list(self._entries.values())

    @property
    def dirty(self) -> bool:  # noqa: D102
        return super().dirty or any(
            annotation.dirty for annotation in self._entries.values()
        )


class NodeAnnotations(Element):
    """Represents the annotation container on a :class:`TopLevelNode`."""

    __slots__ = ("_annotations",)

    def __init__(self) -> None:
        """Construct an annotations container"""
        super().__init__()
        self._annotations = {}

    def __len__(self) -> int:
        return len(self._annotations)

    @classmethod
    def from_json(cls, raw: dict) -> Annotation | None:
        """Helper to construct an annotation from a dict.

        Args:
            raw: Raw annotation representation.

        Returns:
            An Annotation object or None.
        """
        bcls = None
        if "webLink" in raw:
            bcls = WebLink
        elif "topicCategory" in raw:
            bcls = Category
        elif "taskAssist" in raw:
            bcls = TaskAssist
        elif "context" in raw:
            bcls = Context

        if bcls is None:
            logger.warning("Unknown annotation type: %s", raw.keys())
            return None
        annotation = bcls()
        annotation.load(raw)

        return annotation

    def all(self) -> list[Annotation]:
        """Get all annotations.

        Returns:
            Annotations.
        """
        return list(self._annotations.values())

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self._annotations = {}
        if "annotations" not in raw:
            return

        for raw_annotation in raw["annotations"]:
            annotation = self.from_json(raw_annotation)
            self._annotations[annotation.id] = annotation

    def save(self, clean: bool = True) -> dict:
        """Save the annotations container"""
        ret = super().save(clean)
        ret["kind"] = "notes#annotationsGroup"
        if self._annotations:
            ret["annotations"] = [
                annotation.save(clean) for annotation in self._annotations.values()
            ]
        return ret

    def _get_category_node(self) -> Category | None:
        for annotation in self._annotations.values():
            if isinstance(annotation, Category):
                return annotation
        return None

    @property
    def category(self) -> CategoryValue | None:
        """Get the category.

        Returns:
            The category.
        """
        node = self._get_category_node()

        return node.category if node is not None else None

    @category.setter
    def category(self, value: CategoryValue) -> None:
        node = self._get_category_node()
        if value is None:
            if node is not None:
                del self._annotations[node.id]
        else:
            if node is None:
                node = Category()
                self._annotations[node.id] = node

            node.category = value
        self._dirty = True

    @property
    def links(self) -> list[WebLink]:
        """Get all links.

        Returns:
            A list of links.
        """
        return [
            annotation
            for annotation in self._annotations.values()
            if isinstance(annotation, WebLink)
        ]

    def append(self, annotation: Annotation) -> Annotation:
        """Add an annotation.

        Args:
            annotation: An Annotation object.

        Returns:
            The Annotation.
        """
        self._annotations[annotation.id] = annotation
        self._dirty = True
        return annotation

    def remove(self, annotation: Annotation) -> None:
        """Removes an annotation.

        Args:
            annotation: An Annotation object.
        """
        if annotation.id in self._annotations:
            del self._annotations[annotation.id]
        self._dirty = True

    @property
    def dirty(self) -> bool:  # noqa: D102
        return super().dirty or any(
            annotation.dirty for annotation in self._annotations.values()
        )


class NodeTimestamps(Element):
    """Represents the timestamps associated with a :class:`TopLevelNode`."""

    __slots__ = ("_created", "_deleted", "_trashed", "_updated", "_edited")

    TZ_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"

    def __init__(self, create_time: float | None = None) -> None:
        """Construct a timestamps container"""
        super().__init__()
        if create_time is None:
            create_time = time.time()

        self._created = self.int_to_dt(create_time)
        self._deleted = None
        self._trashed = None
        self._updated = self.int_to_dt(create_time)
        self._edited = self.int_to_dt(create_time)

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        if "created" in raw:
            self._created = self.str_to_dt(raw["created"])
        self._deleted = self.str_to_dt(raw["deleted"]) if "deleted" in raw else None
        self._trashed = self.str_to_dt(raw["trashed"]) if "trashed" in raw else None
        self._updated = self.str_to_dt(raw["updated"])
        self._edited = (
            self.str_to_dt(raw["userEdited"]) if "userEdited" in raw else None
        )

    def save(self, clean: bool = True) -> dict:
        """Save the timestamps container"""
        ret = super().save(clean)
        ret["kind"] = "notes#timestamps"
        ret["created"] = self.dt_to_str(self._created)
        if self._deleted is not None:
            ret["deleted"] = self.dt_to_str(self._deleted)
        if self._trashed is not None:
            ret["trashed"] = self.dt_to_str(self._trashed)
        ret["updated"] = self.dt_to_str(self._updated)
        if self._edited is not None:
            ret["userEdited"] = self.dt_to_str(self._edited)
        return ret

    @classmethod
    def str_to_dt(cls, tzs: str | None) -> datetime.datetime:
        """Convert a datetime string into an object.

        Params:
            tsz: Datetime string.

        Returns:
            Datetime.
        """
        if tzs is None:
            return cls.int_to_dt(0)

        return datetime.datetime.strptime(tzs, cls.TZ_FMT).replace(
            tzinfo=datetime.timezone.utc
        )

    @classmethod
    def int_to_dt(cls, tz: float) -> datetime.datetime:
        """Convert a unix timestamp into an object.

        Params:
            ts: Unix timestamp.

        Returns:
            Datetime.
        """
        return datetime.datetime.fromtimestamp(tz, tz=datetime.timezone.utc)

    @classmethod
    def dt_to_str(cls, dt: datetime.datetime) -> str:
        """Convert a datetime to a str.

        Params:
            dt: Datetime.

        Returns:
            Datetime string.
        """
        return dt.strftime(cls.TZ_FMT)

    @classmethod
    def int_to_str(cls, tz: int) -> str:
        """Convert a unix timestamp to a str.

        Returns:
            Datetime string.
        """
        return cls.dt_to_str(cls.int_to_dt(tz))

    @property
    def created(self) -> datetime.datetime:
        """Get the creation datetime.

        Returns:
            Datetime.
        """
        return self._created

    @created.setter
    def created(self, value: datetime.datetime) -> None:
        self._created = value
        self._dirty = True

    @property
    def deleted(self) -> datetime.datetime | None:
        """Get the deletion datetime.

        Returns:
            Datetime.
        """
        return self._deleted

    @deleted.setter
    def deleted(self, value: datetime.datetime) -> None:
        self._deleted = value
        self._dirty = True

    @property
    def trashed(self) -> datetime.datetime | None:
        """Get the move-to-trash datetime.

        Returns:
            Datetime.
        """
        return self._trashed

    @trashed.setter
    def trashed(self, value: datetime.datetime) -> None:
        self._trashed = value
        self._dirty = True

    @property
    def updated(self) -> datetime.datetime:
        """Get the updated datetime.

        Returns:
            Datetime.
        """
        return self._updated

    @updated.setter
    def updated(self, value: datetime.datetime) -> None:
        self._updated = value
        self._dirty = True

    @property
    def edited(self) -> datetime.datetime:
        """Get the user edited datetime.

        Returns:
            Datetime.
        """
        return self._edited

    @edited.setter
    def edited(self, value: datetime.datetime) -> None:
        self._edited = value
        self._dirty = True


class NodeSettings(Element):
    """Represents the settings associated with a :class:`TopLevelNode`."""

    __slots__ = (
        "_new_listitem_placement",
        "_graveyard_state",
        "_checked_listitems_policy",
    )

    def __init__(self) -> None:
        """Construct a settings container"""
        super().__init__()
        self._new_listitem_placement = NewListItemPlacementValue.Bottom
        self._graveyard_state = GraveyardStateValue.Collapsed
        self._checked_listitems_policy = CheckedListItemsPolicyValue.Graveyard

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self._new_listitem_placement = NewListItemPlacementValue(
            raw["newListItemPlacement"]
        )
        self._graveyard_state = GraveyardStateValue(raw["graveyardState"])
        self._checked_listitems_policy = CheckedListItemsPolicyValue(
            raw["checkedListItemsPolicy"]
        )

    def save(self, clean: bool = True) -> dict:
        """Save the settings container"""
        ret = super().save(clean)
        ret["newListItemPlacement"] = self._new_listitem_placement.value
        ret["graveyardState"] = self._graveyard_state.value
        ret["checkedListItemsPolicy"] = self._checked_listitems_policy.value
        return ret

    @property
    def new_listitem_placement(self) -> NewListItemPlacementValue:
        """Get the default location to insert new listitems.

        Returns:
            Placement.
        """
        return self._new_listitem_placement

    @new_listitem_placement.setter
    def new_listitem_placement(self, value: NewListItemPlacementValue) -> None:
        self._new_listitem_placement = value
        self._dirty = True

    @property
    def graveyard_state(self) -> GraveyardStateValue:
        """Get the visibility state for the list graveyard.

        Returns:
            Visibility.
        """
        return self._graveyard_state

    @graveyard_state.setter
    def graveyard_state(self, value: GraveyardStateValue) -> None:
        self._graveyard_state = value
        self._dirty = True

    @property
    def checked_listitems_policy(self) -> CheckedListItemsPolicyValue:
        """Get the policy for checked listitems.

        Returns:
            Policy.
        """
        return self._checked_listitems_policy

    @checked_listitems_policy.setter
    def checked_listitems_policy(self, value: CheckedListItemsPolicyValue) -> None:
        self._checked_listitems_policy = value
        self._dirty = True


class NodeCollaborators(Element):
    """Represents the collaborators on a :class:`TopLevelNode`."""

    __slots__ = ("_collaborators",)

    def __init__(self) -> None:
        """Construct a collaborators container"""
        super().__init__()
        self._collaborators = {}

    def __len__(self) -> int:
        return len(self._collaborators)

    def load(self, collaborators_raw: list, requests_raw: list) -> None:  # noqa: D102
        # Parent method not called.
        if requests_raw and isinstance(requests_raw[-1], bool):
            self._dirty = requests_raw.pop()
        else:
            self._dirty = False
        self._collaborators = {}
        for collaborator in collaborators_raw:
            self._collaborators[collaborator["email"]] = RoleValue(collaborator["role"])
        for collaborator in requests_raw:
            self._collaborators[collaborator["email"]] = ShareRequestValue(
                collaborator["type"]
            )

    def save(self, clean: bool = True) -> tuple[list, list]:
        """Save the collaborators container"""
        # Parent method not called.
        collaborators = []
        requests = []
        for email, action in self._collaborators.items():
            if isinstance(action, ShareRequestValue):
                requests.append({"email": email, "type": action.value})
            else:
                collaborators.append(
                    {"email": email, "role": action.value, "auxiliary_type": "None"}
                )
        if not clean:
            requests.append(self._dirty)
        else:
            self._dirty = False
        return (collaborators, requests)

    def add(self, email: str) -> None:
        """Add a collaborator.

        Args:
            email: Collaborator email address.
        """
        if email not in self._collaborators:
            self._collaborators[email] = ShareRequestValue.Add
        self._dirty = True

    def remove(self, email: str) -> None:
        """Remove a Collaborator.

        Args:
            email: Collaborator email address.
        """
        if email in self._collaborators:
            if self._collaborators[email] == ShareRequestValue.Add:
                del self._collaborators[email]
            else:
                self._collaborators[email] = ShareRequestValue.Remove
        self._dirty = True

    def all(self) -> list[str]:
        """Get all collaborators.

        Returns:
            Collaborators.
        """
        return [
            email
            for email, action in self._collaborators.items()
            if action in [RoleValue.Owner, RoleValue.User, ShareRequestValue.Add]
        ]


class TimestampsMixin:
    """A mixin to add methods for updating timestamps."""

    __slots__ = ()  # empty to resolve multiple inheritance

    def __init__(self) -> None:
        """Instantiate mixin"""
        self.timestamps: NodeTimestamps

    def touch(self, edited: bool = False) -> None:
        """Mark the node as dirty.

        Args:
            edited: Whether to set the edited time.
        """
        self._dirty = True
        dt = datetime.datetime.now(tz=datetime.timezone.utc)
        self.timestamps.updated = dt
        if edited:
            self.timestamps.edited = dt

    @property
    def trashed(self) -> bool:
        """Get the trashed state.

        Returns:
            Whether this item is trashed.
        """
        return (
            self.timestamps.trashed is not None
            and self.timestamps.trashed > NodeTimestamps.int_to_dt(0)
        )

    def trash(self) -> None:
        """Mark the item as trashed."""
        self.timestamps.trashed = datetime.datetime.now(tz=datetime.timezone.utc)

    def untrash(self) -> None:
        """Mark the item as untrashed."""
        self.timestamps.trashed = self.timestamps.int_to_dt(0)

    @property
    def deleted(self) -> bool:
        """Get the deleted state.

        Returns:
            Whether this item is deleted.
        """
        return (
            self.timestamps.deleted is not None
            and self.timestamps.deleted > NodeTimestamps.int_to_dt(0)
        )

    def delete(self) -> None:
        """Mark the item as deleted."""
        self.timestamps.deleted = datetime.datetime.now(tz=datetime.timezone.utc)

    def undelete(self) -> None:
        """Mark the item as undeleted."""
        self.timestamps.deleted = None


class Label(Element, TimestampsMixin):
    """Represents a label."""

    __slots__ = ("id", "_name", "timestamps", "_merged")

    def __init__(self) -> None:
        """Construct a label"""
        super().__init__()

        create_time = time.time()

        self.id = self._generateId(create_time)
        self._name = ""
        self.timestamps = NodeTimestamps(create_time)
        self._merged = NodeTimestamps.int_to_dt(0)

    @classmethod
    def _generateId(cls, tz: float) -> str:
        return "tag.{}.{:x}".format(
            "".join(
                [
                    random.choice("abcdefghijklmnopqrstuvwxyz0123456789")  # noqa: S311
                    for _ in range(12)
                ]
            ),
            int(tz * 1000),
        )

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self.id = raw["mainId"]
        self._name = raw["name"]
        self.timestamps.load(raw["timestamps"])
        self._merged = NodeTimestamps.str_to_dt(raw.get("lastMerged"))

    def save(self, clean: bool = True) -> dict:
        """Save the label"""
        ret = super().save(clean)
        ret["mainId"] = self.id
        ret["name"] = self._name
        ret["timestamps"] = self.timestamps.save(clean)
        ret["lastMerged"] = NodeTimestamps.dt_to_str(self._merged)
        return ret

    @property
    def name(self) -> str:
        """Get the label name.

        Returns:
            Label name.
        """
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        self.touch(True)

    @property
    def merged(self) -> datetime.datetime:
        """Get last merge datetime.

        Returns:
            Datetime.
        """
        return self._merged

    @merged.setter
    def merged(self, value: datetime.datetime) -> None:
        self._merged = value
        self.touch()

    @property
    def dirty(self) -> bool:  # noqa: D102
        return super().dirty or self.timestamps.dirty

    def __str__(self) -> str:
        return self.name


class NodeLabels(Element):
    """Represents the labels on a :class:`TopLevelNode`."""

    __slots__ = ("_labels",)

    def __init__(self) -> None:
        """Construct a labels container"""
        super().__init__()
        self._labels = {}

    def __len__(self) -> int:
        return len(self._labels)

    def _load(self, raw: list) -> None:
        # Parent method not called.
        if raw and isinstance(raw[-1], bool):
            self._dirty = raw.pop()
        else:
            self._dirty = False
        self._labels = {}
        for raw_label in raw:
            self._labels[raw_label["labelId"]] = None

    def save(self, clean: bool = True) -> tuple[dict] | tuple[dict, bool]:  # noqa: D102
        # Parent method not called.
        ret = [
            {
                "labelId": label_id,
                "deleted": NodeTimestamps.dt_to_str(
                    datetime.datetime.now(tz=datetime.timezone.utc)
                )
                if label is None
                else NodeTimestamps.int_to_str(0),
            }
            for label_id, label in self._labels.items()
        ]
        if not clean:
            ret.append(self._dirty)
        else:
            self._dirty = False
        return ret

    def add(self, label: Label) -> None:
        """Add a label.

        Args:
            label: The Label object.
        """
        self._labels[label.id] = label
        self._dirty = True

    def remove(self, label: Label) -> None:
        """Remove a label.

        Args:
            label: The Label object.
        """
        if label.id in self._labels:
            self._labels[label.id] = None
        self._dirty = True

    def get(self, label_id: str) -> str:
        """Get a label by ID.

        Args:
            label_id: The label ID.
        """
        return self._labels.get(label_id)

    def all(self) -> list[Label]:
        """Get all labels.

        Returns:
            Labels.
        """
        return [label for _, label in self._labels.items() if label is not None]


class Node(Element, TimestampsMixin):
    """Node base class."""

    __slots__ = (
        "parent",
        "id",
        "server_id",
        "parent_id",
        "type",
        "_sort",
        "_version",
        "_text",
        "_children",
        "timestamps",
        "settings",
        "annotations",
        "_moved",
    )

    def __init__(
        self,
        id_: str | None = None,
        type_: str | None = None,
        parent_id: str | None = None,
    ) -> None:
        """Construct a node"""
        super().__init__()

        create_time = time.time()

        self.parent = None
        self.id = self._generateId(create_time) if id_ is None else id_
        self.server_id = None
        self.parent_id = parent_id
        self.type = type_
        self._sort = random.randint(1000000000, 9999999999)  # noqa: S311
        self._version = None
        self._text = ""
        self._children = {}
        self.timestamps = NodeTimestamps(create_time)
        self.settings = NodeSettings()
        self.annotations = NodeAnnotations()

        # Set if there is no baseVersion in the raw data
        self._moved = False

    @classmethod
    def _generateId(cls, tz: float) -> str:
        return "{:x}.{:016x}".format(  # noqa: UP032
            int(tz * 1000),
            random.randint(0x0000000000000000, 0xFFFFFFFFFFFFFFFF),  # noqa: S311
        )

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        # Verify this is a valid type
        NodeType(raw["type"])
        if raw["kind"] != "notes#node":
            logger.warning("Unknown node kind: %s", raw["kind"])

        if "mergeConflict" in raw:
            raise exception.MergeException(raw)

        self.id = raw["id"]
        self.server_id = raw.get("serverId", self.server_id)
        self.parent_id = raw["parentId"]
        self._sort = raw.get("sortValue", self.sort)
        self._version = raw.get("baseVersion", self._version)
        self._text = raw.get("text", self._text)
        self.timestamps.load(raw["timestamps"])
        self.settings.load(raw["nodeSettings"])
        self.annotations.load(raw["annotationsGroup"])

    def save(self, clean: bool = True) -> dict:  # noqa: D102
        ret = super().save(clean)
        ret["id"] = self.id
        ret["kind"] = "notes#node"
        ret["type"] = self.type.value
        ret["parentId"] = self.parent_id
        ret["sortValue"] = self._sort
        if not self._moved and self._version is not None:
            ret["baseVersion"] = self._version
        ret["text"] = self._text
        if self.server_id is not None:
            ret["serverId"] = self.server_id
        ret["timestamps"] = self.timestamps.save(clean)
        ret["nodeSettings"] = self.settings.save(clean)
        ret["annotationsGroup"] = self.annotations.save(clean)
        return ret

    @property
    def sort(self) -> int:
        """Get the sort id.

        Returns:
            Sort id.
        """
        return int(self._sort)

    @sort.setter
    def sort(self, value: int) -> None:
        self._sort = value
        self.touch()

    @property
    def version(self) -> int:
        """Get the node version.

        Returns:
            Version.
        """
        return self._version

    @property
    def text(self) -> str:
        """Get the text value.

        Returns:
            Text value.
        """
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        """Set the text value.

        Args:
            value: Text value.
        """
        self._text = value
        self.timestamps.edited = datetime.datetime.now(tz=datetime.timezone.utc)
        self.touch(True)

    @property
    def children(self) -> list["Node"]:
        """Get all children.

        Returns:
            Children nodes.
        """
        return list(self._children.values())

    def get(self, node_id: str) -> "Node | None":
        """Get child node with the given ID.

        Args:
            node_id: The node ID.

        Returns:
            Child node.
        """
        return self._children.get(node_id)

    def append(self, node: "Node", dirty: bool = True) -> "Node":
        """Add a new child node.

        Args:
            node: Node to add.
            dirty: Whether this node should be marked dirty.
        """
        self._children[node.id] = node
        node.parent = self
        if dirty:
            self.touch()

        return node

    def remove(self, node: "Node", dirty: bool = True) -> None:
        """Remove the given child node.

        Args:
            node: Node to remove.
            dirty: Whether this node should be marked dirty.
        """
        if node.id in self._children:
            self._children[node.id].parent = None
            del self._children[node.id]
        if dirty:
            self.touch()

    @property
    def new(self) -> bool:
        """Get whether this node has been persisted to the server.

        Returns:
            True if node is new.
        """
        return self.server_id is None

    @property
    def dirty(self) -> bool:  # noqa: D102
        return (
            super().dirty
            or self.timestamps.dirty
            or self.annotations.dirty
            or self.settings.dirty
            or any(node.dirty for node in self.children)
        )


class Root(Node):
    """Internal root node."""

    __slots__ = ()

    ID = "root"

    def __init__(self) -> None:
        """Construct a root node"""
        super().__init__(id_=self.ID)

    @property
    def dirty(self) -> bool:  # noqa: D102
        return False


class TopLevelNode(Node):
    """Top level node base class."""

    __slots__ = ("_color", "_archived", "_pinned", "_title", "labels", "collaborators")

    _TYPE = None

    def __init__(self, **kwargs: dict) -> None:
        """Construct a top level node"""
        super().__init__(parent_id=Root.ID, **kwargs)
        self._color = ColorValue.White
        self._archived = False
        self._pinned = False
        self._title = ""
        self.labels = NodeLabels()
        self.collaborators = NodeCollaborators()

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self._color = ColorValue(raw["color"]) if "color" in raw else ColorValue.White
        self._archived = raw.get("isArchived", False)
        self._pinned = raw.get("isPinned", False)
        self._title = raw.get("title", "")
        self.labels.load(raw.get("labelIds", []))

        self.collaborators.load(
            raw.get("roleInfo", []),
            raw.get("shareRequests", []),
        )
        self._moved = "moved" in raw

    def save(self, clean: bool = True) -> dict:  # noqa: D102
        ret = super().save(clean)
        ret["color"] = self._color.value
        ret["isArchived"] = self._archived
        ret["isPinned"] = self._pinned
        ret["title"] = self._title
        labels = self.labels.save(clean)

        collaborators, requests = self.collaborators.save(clean)
        if labels:
            ret["labelIds"] = labels
        ret["collaborators"] = collaborators
        if requests:
            ret["shareRequests"] = requests
        return ret

    @property
    def color(self) -> ColorValue:
        """Get the node color.

        Returns:
            Color.
        """
        return self._color

    @color.setter
    def color(self, value: ColorValue) -> None:
        self._color = value
        self.touch(True)

    @property
    def archived(self) -> bool:
        """Get the archive state.

        Returns:
            Whether this node is archived.
        """
        return self._archived

    @archived.setter
    def archived(self, value: bool) -> None:
        self._archived = value
        self.touch(True)

    @property
    def pinned(self) -> bool:
        """Get the pin state.

        Returns:
            Whether this node is pinned.
        """
        return self._pinned

    @pinned.setter
    def pinned(self, value: bool) -> None:
        self._pinned = value
        self.touch(True)

    @property
    def title(self) -> str:
        """Get the title.

        Returns:
            Title.
        """
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = value
        self.touch(True)

    @property
    def url(self) -> str:
        """Get the url for this node.

        Returns:
            Google Keep url.
        """
        return "https://keep.google.com/u/0/#" + self._TYPE.value + "/" + self.id

    @property
    def dirty(self) -> bool:  # noqa: D102
        return super().dirty or self.labels.dirty or self.collaborators.dirty

    @property
    def blobs(self) -> list["Blob"]:
        """Get all media blobs.

        Returns:
            Media blobs.
        """
        return [node for node in self.children if isinstance(node, Blob)]

    @property
    def images(self) -> list["NodeImage"]:
        """Get all image blobs"""
        return [blob for blob in self.blobs if isinstance(blob.blob, NodeImage)]

    @property
    def drawings(self) -> list["NodeDrawing"]:
        """Get all drawing blobs"""
        return [blob for blob in self.blobs if isinstance(blob.blob, NodeDrawing)]

    @property
    def audio(self) -> list["NodeAudio"]:
        """Get all audio blobs"""
        return [blob for blob in self.blobs if isinstance(blob.blob, NodeAudio)]


class ListItem(Node):
    """Represents a Google Keep listitem.

    Interestingly enough, :class:`Note`s store their content in a single
    child :class:`ListItem`.
    """

    __slots__ = (
        "parent_item",
        "parent_server_id",
        "super_list_item_id",
        "prev_super_list_item_id",
        "_subitems",
        "_checked",
    )

    def __init__(
        self,
        parent_id: str | None = None,
        parent_server_id: str | None = None,
        super_list_item_id: str | None = None,
        **kwargs: dict,
    ) -> None:
        """Construct a list item node"""
        super().__init__(type_=NodeType.ListItem, parent_id=parent_id, **kwargs)
        self.parent_item = None
        self.parent_server_id = parent_server_id
        self.super_list_item_id = super_list_item_id
        self.prev_super_list_item_id = None
        self._subitems = {}
        self._checked = False

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self.prev_super_list_item_id = self.super_list_item_id
        self.super_list_item_id = raw.get("superListItemId") or None
        self._checked = raw.get("checked", False)

    def save(self, clean: bool = True) -> dict:  # noqa: D102
        ret = super().save(clean)
        ret["parentServerId"] = self.parent_server_id
        ret["superListItemId"] = self.super_list_item_id
        ret["checked"] = self._checked
        return ret

    def add(
        self,
        text: str,
        checked: bool = False,
        sort: NewListItemPlacementValue | int | None = None,
    ) -> "ListItem":
        """Add a new sub item to the list. This item must already be attached to a list.

        Args:
            text: The text.
            checked: Whether this item is checked.
            sort: Item id for sorting.
        """
        if self.parent is None:
            raise exception.InvalidException("Item has no parent")
        node = self.parent.add(text, checked, sort)
        self.indent(node)
        return node

    def indent(self, node: "ListItem", dirty: bool = True) -> None:
        """Indent an item. Does nothing if the target has subitems.

        Args:
            node: Item to indent.
            dirty: Whether this node should be marked dirty.
        """
        if node.subitems:
            return

        self._subitems[node.id] = node
        node.super_list_item_id = self.id
        node.parent_item = self
        if dirty:
            node.touch(True)

    def dedent(self, node: "ListItem", dirty: bool = True) -> None:
        """Dedent an item. Does nothing if the target is not indented under this item.

        Args:
            node: Item to dedent.
            dirty : Whether this node should be marked dirty.
        """
        if node.id not in self._subitems:
            return

        del self._subitems[node.id]
        node.super_list_item_id = ""
        node.parent_item = None
        if dirty:
            node.touch(True)

    @property
    def subitems(self) -> list["ListItem"]:
        """Get subitems for this item.

        Returns:
            Subitems.
        """
        return List.sorted_items(self._subitems.values())

    @property
    def indented(self) -> bool:
        """Get indentation state.

        Returns:
            Whether this item is indented.
        """
        return self.parent_item is not None

    @property
    def checked(self) -> bool:
        """Get the checked state.

        Returns:
            Whether this item is checked.
        """
        return self._checked

    @checked.setter
    def checked(self, value: bool) -> None:
        self._checked = value
        self.touch(True)

    def __str__(self) -> str:
        return "{}{} {}".format(
            "  " if self.indented else "",
            "☑" if self.checked else "☐",
            self.text,
        )


class Note(TopLevelNode):
    """Represents a Google Keep note."""

    __slots__ = ()

    _TYPE = NodeType.Note

    def __init__(self, **kwargs: dict) -> None:
        """Construct a note node"""
        super().__init__(type_=self._TYPE, **kwargs)

    def _get_text_node(self) -> ListItem | None:
        node = None
        for child_node in self.children:
            if isinstance(child_node, ListItem):
                node = child_node
                break

        return node

    @property
    def text(self) -> str:  # noqa: D102
        node = self._get_text_node()

        if node is None:
            return self._text
        return node.text

    @text.setter
    def text(self, value: str) -> None:
        node = self._get_text_node()
        if node is None:
            node = ListItem(parent_id=self.id)
            self.append(node, True)
        node.text = value
        self.touch(True)

    def __str__(self) -> str:
        return f"{self.title}\n{self.text}"


class List(TopLevelNode):
    """Represents a Google Keep list."""

    _TYPE = NodeType.List
    SORT_DELTA = 10000  # Arbitrary constant

    def __init__(self, **kwargs: dict) -> None:
        """Construct a list node"""
        super().__init__(type_=self._TYPE, **kwargs)

    def add(
        self,
        text: str,
        checked: bool = False,
        sort: NewListItemPlacementValue | int | None = None,
    ) -> ListItem:
        """Add a new item to the list.

        Args:
            text: The text.
            checked: Whether this item is checked.
            sort: Item id for sorting or a placement policy.
        """
        node = ListItem(parent_id=self.id, parent_server_id=self.server_id)
        node.checked = checked
        node.text = text

        items = list(self.items)
        if isinstance(sort, int):
            node.sort = sort
        elif isinstance(sort, NewListItemPlacementValue) and len(items):
            func = max
            delta = self.SORT_DELTA
            if sort == NewListItemPlacementValue.Bottom:
                func = min
                delta *= -1

            node.sort = func(int(item.sort) for item in items) + delta

        self.append(node, True)
        self.touch(True)
        return node

    @property
    def text(self) -> str:  # noqa: D102
        return "\n".join(str(node) for node in self.items)

    @classmethod
    def sorted_items(cls, items: list[ListItem]) -> list[ListItem]:  # noqa: C901
        """Generate a list of sorted list items, taking into account parent items.

        Args:
            items: Items to sort.


        Returns:
            Sorted items.
        """

        class T(tuple):
            """Tuple with element-based sorting"""

            __slots__ = ()

            def __cmp__(self, other: "T") -> int:
                for a, b in itertools.zip_longest(self, other):
                    if a != b:
                        if a is None:
                            return 1
                        if b is None:
                            return -1
                        return a - b
                return 0

            def __lt__(self, other: "T") -> bool:  # pragma: no cover
                return self.__cmp__(other) < 0

            def __gt__(self, other: "T") -> bool:  # pragma: no cover
                return self.__cmp__(other) > 0

            def __le__(self, other: "T") -> bool:  # pragma: no cover
                return self.__cmp__(other) <= 0

            def __ge__(self, other: "T") -> bool:  # pragma: no cover
                return self.__cmp__(other) >= 0

            def __eq__(self, other: "T") -> bool:  # pragma: no cover
                return self.__cmp__(other) == 0

            def __ne__(self, other: "T") -> bool:  # pragma: no cover
                return self.__cmp__(other) != 0

        def key_func(x: ListItem) -> T:
            if x.indented:
                return T((int(x.parent_item.sort), int(x.sort)))
            return T((int(x.sort),))

        return sorted(items, key=key_func, reverse=True)

    def _items(self, checked: bool | None = None) -> list[ListItem]:
        return [
            node
            for node in self.children
            if isinstance(node, ListItem)
            and not node.deleted
            and (checked is None or node.checked == checked)
        ]

    def sort_items(
        self, key: Callable = attrgetter("text"), reverse: bool = False
    ) -> None:
        """Sort list items in place. By default, the items are alphabetized, but a custom function can be specified.

        Args:
            key: A filter function.
            reverse: Whether to reverse the output.
        """
        sorted_children = sorted(self._items(), key=key, reverse=reverse)
        sort_value = random.randint(1000000000, 9999999999)  # noqa: S311

        for node in sorted_children:
            node.sort = sort_value
            sort_value -= self.SORT_DELTA

    def __str__(self) -> str:
        return "\n".join([self.title] + [str(node) for node in self.items])

    @property
    def items(self) -> list[ListItem]:
        """Get all listitems.

        Returns:
            List items.
        """
        return self.sorted_items(self._items())

    @property
    def checked(self) -> list[ListItem]:
        """Get all checked listitems.

        Returns:
            List items.
        """
        return self.sorted_items(self._items(True))

    @property
    def unchecked(self) -> list[ListItem]:
        """Get all unchecked listitems.

        Returns:
            List items.
        """
        return self.sorted_items(self._items(False))


class NodeBlob(Element):
    """Represents a blob descriptor."""

    __slots__ = ("blob_id", "type", "_media_id", "_mimetype")

    _TYPE = None

    def __init__(self, type_: str | None = None) -> None:
        """Construct a node blob"""
        super().__init__()
        self.blob_id = None
        self.type = type_
        self._media_id = None
        self._mimetype = ""

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        # Verify this is a valid type
        BlobType(raw["type"])
        self.blob_id = raw.get("blob_id")
        self._media_id = raw.get("media_id")
        self._mimetype = raw.get("mimetype")

    def save(self, clean: bool = True) -> dict:
        """Save the node blob"""
        ret = super().save(clean)
        ret["kind"] = "notes#blob"
        ret["type"] = self.type.value
        if self.blob_id is not None:
            ret["blob_id"] = self.blob_id
        if self._media_id is not None:
            ret["media_id"] = self._media_id
        ret["mimetype"] = self._mimetype
        return ret


class NodeAudio(NodeBlob):
    """Represents an audio blob."""

    __slots__ = ("_length",)

    _TYPE = BlobType.Audio

    def __init__(self) -> None:
        """Construct a node audio blob"""
        super().__init__(type_=self._TYPE)
        self._length = None

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self._length = raw.get("length")

    def save(self, clean: bool = True) -> dict:
        """Save the node audio blob"""
        ret = super().save(clean)
        if self._length is not None:
            ret["length"] = self._length
        return ret

    @property
    def length(self) -> int:
        """Get length of the audio clip.

        Returns:
            Audio length.
        """
        return self._length


class NodeImage(NodeBlob):
    """Represents an image blob."""

    __slots__ = (
        "_is_uploaded",
        "_width",
        "_height",
        "_byte_size",
        "_extracted_text",
        "_extraction_status",
    )

    _TYPE = BlobType.Image

    def __init__(self) -> None:
        """Construct a node image blob"""
        super().__init__(type_=self._TYPE)
        self._is_uploaded = False
        self._width = 0
        self._height = 0
        self._byte_size = 0
        self._extracted_text = ""
        self._extraction_status = ""

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self._is_uploaded = raw.get("is_uploaded") or False
        self._width = raw.get("width")
        self._height = raw.get("height")
        self._byte_size = raw.get("byte_size")
        self._extracted_text = raw.get("extracted_text")
        self._extraction_status = raw.get("extraction_status")

    def save(self, clean: bool = True) -> dict:
        """Save the node image blob"""
        ret = super().save(clean)
        ret["width"] = self._width
        ret["height"] = self._height
        ret["byte_size"] = self._byte_size
        ret["extracted_text"] = self._extracted_text
        ret["extraction_status"] = self._extraction_status
        return ret

    @property
    def width(self) -> int:
        """Get width of image.

        Returns:
            Image width.
        """
        return self._width

    @property
    def height(self) -> int:
        """Get height of image.

        Returns:
            Image height.
        """
        return self._height

    @property
    def byte_size(self) -> int:
        """Get size of image in bytes.

        Returns:
            Image byte size.
        """
        return self._byte_size

    @property
    def extracted_text(self) -> str:
        """Get text extracted from image

        Returns:
            Extracted text.
        """
        return self._extracted_text

    @property
    def url(self) -> str:
        """Get a url to the image.

        Returns:
            Image url.
        """
        raise NotImplementedError


class NodeDrawing(NodeBlob):
    """Represents a drawing blob."""

    __slots__ = ("_extracted_text", "_extraction_status", "_drawing_info")

    _TYPE = BlobType.Drawing

    def __init__(self) -> None:
        """Construct a node drawing blob"""
        super().__init__(type_=self._TYPE)
        self._extracted_text = ""
        self._extraction_status = ""
        self._drawing_info = None

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self._extracted_text = raw.get("extracted_text")
        self._extraction_status = raw.get("extraction_status")
        drawing_info = None
        if "drawingInfo" in raw:
            drawing_info = NodeDrawingInfo()
            drawing_info.load(raw["drawingInfo"])
        self._drawing_info = drawing_info

    def save(self, clean: bool = True) -> dict:
        """Save the node drawing blob"""
        ret = super().save(clean)
        ret["extracted_text"] = self._extracted_text
        ret["extraction_status"] = self._extraction_status
        if self._drawing_info is not None:
            ret["drawingInfo"] = self._drawing_info.save(clean)
        return ret

    @property
    def extracted_text(self) -> str:
        """Get text extracted from image

        Returns:
            Extracted text.
        """
        return (
            self._drawing_info.snapshot.extracted_text
            if self._drawing_info is not None
            else ""
        )


class NodeDrawingInfo(Element):
    """Represents information about a drawing blob."""

    __slots__ = (
        "drawing_id",
        "snapshot",
        "_snapshot_fingerprint",
        "_thumbnail_generated_time",
        "_ink_hash",
        "_snapshot_proto_fprint",
    )

    def __init__(self) -> None:
        """Construct a drawing info container"""
        super().__init__()
        self.drawing_id = ""
        self.snapshot = NodeImage()
        self._snapshot_fingerprint = ""
        self._thumbnail_generated_time = NodeTimestamps.int_to_dt(0)
        self._ink_hash = ""
        self._snapshot_proto_fprint = ""

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self.drawing_id = raw["drawingId"]
        self.snapshot.load(raw["snapshotData"])
        self._snapshot_fingerprint = raw.get(
            "snapshotFingerprint", self._snapshot_fingerprint
        )
        self._thumbnail_generated_time = NodeTimestamps.str_to_dt(
            raw.get("thumbnailGeneratedTime")
        )
        self._ink_hash = raw.get("inkHash", "")
        self._snapshot_proto_fprint = raw.get(
            "snapshotProtoFprint", self._snapshot_proto_fprint
        )

    def save(self, clean: bool = True) -> dict:  # noqa: D102
        ret = super().save(clean)
        ret["drawingId"] = self.drawing_id
        ret["snapshotData"] = self.snapshot.save(clean)
        ret["snapshotFingerprint"] = self._snapshot_fingerprint
        ret["thumbnailGeneratedTime"] = NodeTimestamps.dt_to_str(
            self._thumbnail_generated_time
        )
        ret["inkHash"] = self._ink_hash
        ret["snapshotProtoFprint"] = self._snapshot_proto_fprint
        return ret


class Blob(Node):
    """Represents a Google Keep blob."""

    __slots__ = ("blob",)

    _blob_type_map = {  # noqa: RUF012
        BlobType.Audio: NodeAudio,
        BlobType.Image: NodeImage,
        BlobType.Drawing: NodeDrawing,
    }

    def __init__(self, parent_id: str | None = None, **kwargs: dict) -> None:
        """Construct a blob"""
        super().__init__(type_=NodeType.Blob, parent_id=parent_id, **kwargs)
        self.blob = None

    @classmethod
    def from_json(cls: type, raw: dict) -> NodeBlob | None:
        """Helper to construct a blob from a dict.

        Args:
            raw: Raw blob representation.

        Returns:
            A NodeBlob object or None.
        """
        if raw is None:
            return None

        _type = raw.get("type")
        if _type is None:
            return None

        bcls = None
        try:
            bcls = cls._blob_type_map[BlobType(_type)]
        except (KeyError, ValueError) as e:
            logger.warning("Unknown blob type: %s", _type)
            if DEBUG:  # pragma: no cover
                raise exception.ParseException(f"Parse error for {_type}", raw) from e
            return None
        blob = bcls()
        blob.load(raw)

        return blob

    def _load(self, raw: dict) -> None:
        super()._load(raw)
        self.blob = self.from_json(raw.get("blob"))

    def save(self, clean: bool = True) -> dict:
        """Save the blob"""
        ret = super().save(clean)
        if self.blob is not None:
            ret["blob"] = self.blob.save(clean)
        return ret


_type_map = {
    NodeType.Note: Note,
    NodeType.List: List,
    NodeType.ListItem: ListItem,
    NodeType.Blob: Blob,
}


def from_json(raw: dict) -> Node | None:
    """Helper to construct a node from a dict.

    Args:
        raw: Raw node representation.

    Returns:
        A Node object or None.
    """
    ncls = None
    _type = raw.get("type")
    try:
        ncls = _type_map[NodeType(_type)]
    except (KeyError, ValueError) as e:
        logger.warning("Unknown node type: %s", _type)
        if DEBUG:  # pragma: no cover
            raise exception.ParseException(f"Parse error for {_type}", raw) from e
        return None
    node = ncls()
    node.load(raw)

    return node


if DEBUG:  # pragma: no cover
    Node.__load = Node._load  # noqa: SLF001

    def _load(self, raw):  # noqa: ANN001, ANN202
        self.__load(raw)
        self._find_discrepancies(raw)

    Node._load = _load  # noqa: SLF001
