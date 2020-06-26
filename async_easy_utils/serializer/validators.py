import itertools
from collections.abc import Iterable

from tortoise.models import Model

from async_easy_utils.serializer.fields import RelatedField
from async_easy_utils.utils import MetaValidatorMixin


class SerializerMetaValidator(MetaValidatorMixin):
    def __init__(self, instance, attrs):
        self._instance = instance
        self._attrs = attrs
        self._meta = getattr(instance, 'Meta', None)

    @staticmethod
    def get_variable_from_method_name(method_name='', splitter='', end_rstrip=''):
        return next(iter(method_name.split(splitter, 1)[1:2]), '').rstrip(end_rstrip)

    def check_if_meta_exists(self):
        if self._meta is None:
            raise ValueError(f'{self._instance.__name__} missing Meta')

    def check_if_model_in_meta(self):
        if not hasattr(self._meta, 'model'):
            raise ValueError(f'{self._instance.__name__} Meta missing model')

    def check_if_fields_in_meta(self):
        if not hasattr(self._meta, 'fields'):
            raise ValueError(f'{self._instance.__name__} Meta missing fields')

    def check_if_meta_fields_are_iterable(self):
        if not isinstance(self._meta.fields, Iterable):
            raise ValueError(f'{self._instance.__name__} fields must be iterable')

    def check_if_meta_fields_have_items(self):
        if len(self._meta.fields) == 0:
            raise ValueError(f'{self._instance.__name__} fields zero length')

    def check_if_meta_model_is_tortoise_instance(self):
        if not issubclass(self._meta.model, Model):
            raise ValueError(f'{self._instance.__name__} Meta model is not TorToise model instance')

    def check_if_meta_fields_contains_proper_values(self):
        if not all(attr in self.allowed_fields for attr in self._meta.fields):
            raise ValueError('incorrect Meta field declaration - some fields does '
                             'not belong to model or serialized fields')

    def check_meta_read_only_fields(self):
        read_only_fields = getattr(self._meta, 'read_only_fields', None)
        if read_only_fields and not all(attr in self.allowed_fields for attr in read_only_fields):
            raise ValueError('incorrect Meta read_only_field declaration - some fields '
                             'does not belong to model or serialized fields')

    def check_if_all_declared_related_fields_in_meta_fields(self):
        if not all(attr in self._meta.fields for attr in self.declared_fields):
            raise ValueError('incorrect related field declaration - some fields '
                             'was not included to fields')

    @property
    def serialized_fields(self):
        return {self.get_variable_from_method_name(name, 'get_', '_')
                for name, attr in self._attrs.items() if callable(attr) and
                self.get_variable_from_method_name(name, 'get_', '_')}

    @property
    def model_fields(self):
        return self._meta.model._meta.fields.difference(self._meta.model._meta.fk_fields)

    @property
    def declared_fields(self):
        return {name for name, attr in self._attrs.items()
                if issubclass(attr.__class__, RelatedField)}

    @property
    def allowed_fields(self):
        return list(itertools.chain(
            self.model_fields, self.serialized_fields, self.declared_fields))

    @classmethod
    def validate(cls, instance, attrs):
        validator = cls(instance, attrs)

        validator.check_if_meta_exists()
        validator.check_if_model_in_meta()
        validator.check_if_fields_in_meta()
        validator.check_if_meta_fields_are_iterable()
        validator.check_if_meta_fields_have_items()
        validator.check_if_meta_model_is_tortoise_instance()
        validator.check_if_meta_fields_contains_proper_values()
        validator.check_meta_read_only_fields()
        validator.check_if_all_declared_related_fields_in_meta_fields()
