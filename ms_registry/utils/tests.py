from rest_framework.fields import empty

DEFAULT_ACTIONS = ("list", "retrieve", "create", "update", "partial_update", "destroy")

HTTP_METHODS = ("GET", "HEAD", "OPTIONS", "POST", "DELETE", "PUT", "PATCH")


def assert_serializer_errors(
    serializer_class, data, expected_errors, instance=None, **kwargs
):
    serializer = serializer_class(instance=instance, data=data, **kwargs)
    assert not serializer.is_valid()
    assert serializer.errors == expected_errors


def assert_read_fields_set_equal(serializer_class, field_set, required_only=False):
    serializer = serializer_class()
    readable = {
        f.field_name
        for f in serializer._readable_fields
        if not required_only or f.required
    }
    assert readable == field_set


def assert_write_fields_set_equal(serializer_class, field_set, required_only=False):
    serializer = serializer_class()
    writable = {
        name
        for name, f in serializer.get_fields().items()
        if (not f.read_only or f.default is not empty)
        and (not required_only or f.required)
    }
    assert writable == field_set


# --- View helpers ---


def assert_permissions(view_class, expected, actions=DEFAULT_ACTIONS):
    view = view_class()
    expected_types = [Klass().__class__ for Klass in expected]
    for action in actions:
        view.action = action
        assert [p.__class__ for p in view.get_permissions()] == expected_types


# --- Permission helpers ---


def perm_call(permission_class, *args, **kwargs):
    return permission_class().has_permission(*args, **kwargs)


def perm_call_obj(permission_class, *args, **kwargs):
    return permission_class().has_object_permission(*args, **kwargs)
