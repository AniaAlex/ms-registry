from utils.tests import assert_read_fields_set_equal, assert_write_fields_set_equal

from .. import serializers


def test_access_token_serializer_fields():
    assert_write_fields_set_equal(serializers.AccessTokenSerializer, set())
    assert_read_fields_set_equal(
        serializers.AccessTokenSerializer, {"refresh", "access"}
    )
