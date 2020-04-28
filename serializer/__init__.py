import asyncio
from collections import OrderedDict
from collections.abc import Iterable

from tortoise import exceptions
from tortoise import fields as model_fields
from tortoise.fields.relational import ForeignKeyFieldInstance
from tortoise.models import Model

from serializer.exceptions import ValidationError
from serializer.fields import (
    StringField,
    IntegerField,
    ForeignKeyField,
    DateTimeField,
    BinaryField,
    MethodField,
)


class SerializerInstanceValidator:
    def __init__(self, instance, attrs):
        self._instance = instance
        self._attrs = attrs
        self._meta = getattr(instance, 'Meta', None)

    @staticmethod
    def get_variable_from_method_name(method_name='', splitter='', end_rstrip=''):
        return next(iter(method_name.split(splitter)[1:2]), '').rstrip(end_rstrip)

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

    def check_if_meta_fields_containts_proper_values(self):
        if not all(attr in self.allowed_fields for attr in self._meta.fields):
            raise ValueError(f'incorrect Meta field declaration - some fields does '
                             f'not belong to model or serialized fields')

    def check_meta_read_only_fields(self):
        read_only_fields = getattr(self._meta, 'read_only_fields', None)
        if read_only_fields and not all(attr in self.allowed_fields for attr in read_only_fields):
            raise ValueError('incorrect Meta read_only_field declaration - some fields '
                             'does not belong to model or serialized fields')

    def check_fk_fields_declaration(self):
        model_fk_fields = self._meta.model._meta.fk_fields
        if model_fk_fields:
            fk_attrs = [name for name, field in self._attrs.items() if
                        isinstance(field, ForeignKeyField)]
            if not fk_attrs:
                raise ValueError(f'{self._instance.__name__} missing foreign keys mapping')

            if not all(field in self._meta.fields for field in fk_attrs):
                raise ValueError(f'{self._instance.__name__} some related fields are not included '
                                 f'on fields, but was specify inside serializer')

            if not all(fk_attr in model_fk_fields for fk_attr in fk_attrs):
                raise ValueError(f'{self._instance.__name__} incorrect foreign keys mapping')

    def check_m2m_fields_declaration(self):
        pass

    @property
    def serialized_fields(self):
        return [self.get_variable_from_method_name(name, 'get_', '_')
                for name, attr in self._attrs.items() if callable(attr) and
                self.get_variable_from_method_name(name, 'get_', '_')]

    @property
    def allowed_fields(self):
        return list(self._meta.model._meta.fields) + self.serialized_fields

    @classmethod
    def validate(cls, instance, attrs):
        validator = cls(instance, attrs)

        validator.check_if_meta_exists()
        validator.check_if_model_in_meta()
        validator.check_if_meta_model_is_tortoise_instance()
        validator.check_if_fields_in_meta()
        validator.check_if_meta_fields_are_iterable()
        validator.check_if_meta_fields_have_items()
        validator.check_if_meta_fields_containts_proper_values()
        validator.check_meta_read_only_fields()
        validator.check_fk_fields_declaration()
        validator.check_m2m_fields_declaration()


class SerializerMeta(type):
    """
    Meta class for Serializer. Provide creation and validation for new Serializer instances.
    """
    FIELD_MAPPING = {
        model_fields.UUIDField: StringField,
        model_fields.TextField: StringField,
        model_fields.IntField: IntegerField,
        ForeignKeyFieldInstance: ForeignKeyField,
        model_fields.DatetimeField: DateTimeField,
        model_fields.BinaryField: BinaryField,
    }

    def __new__(cls, name, bases, attrs, **kwargs):
        instance = super().__new__(cls, name, bases, attrs, **kwargs)
        if not bases:
            return instance

        SerializerInstanceValidator.validate(instance, attrs)
        meta = attrs.get('Meta')

        instance.model = meta.model
        instance.model_pk_field_name = instance.model._meta.pk_attr

        instance.fields = OrderedDict()

        for field_name in meta.fields:
            model_field = meta.model._meta.fields_map.get(field_name)
            field = cls.FIELD_MAPPING.get(model_field.__class__, MethodField)

            if field is MethodField:
                field = field(method=attrs.get(f'get_{field_name}'))
            else:
                field = attrs.get(field_name) or field()

            field.setup_from_model_field(model_field)
            instance.fields[field_name] = field

        instance.read_only_fields = tuple(name for name, field in instance.fields.items() if
                                          isinstance(field, MethodField))
        meta_read_only_fields = getattr(meta, 'read_only_fields', None)
        if meta_read_only_fields:
           instance.read_only_fields = instance.read_only_fields + meta_read_only_fields

        return instance


class Serializer(metaclass=SerializerMeta):
    """
    Simple serializer inspired by Django REST.
    """
    def __init__(self, instance=None, data=None):
        if instance and not issubclass(instance.__class__, self.model):
            raise ValidationError(f'{self.__class__.__name__} instance not serializer model class')

        self._data = data
        self._errors = {}
        self._instance = instance
        self._validated_data = None

    def _check_input_data_for_missing_values(self):
        errors = {}
        valid = True
        input_read_only_fields = [f for f in self._data.keys() if f in self.read_only_fields]
        if any(input_read_only_fields):
            valid = False
            errors.update({field: 'field is read only' for field in input_read_only_fields})

        if self.model_pk_field_name in self._data.keys():
            valid = False
            errors[self.model_pk_field_name] = 'primary key, cannot be in input'

        keys_diff = set(name for name in self.fields.keys() if
                        name not in self.read_only_fields).difference(set(self._data.keys()))
        keys_diff.discard(self.model_pk_field_name)
        if bool(keys_diff):
            valid = False
            errors.update({field: 'missing in input' for field in keys_diff})

        return valid, errors

    async def is_valid(self):
        if self._instance:
            return True

        if not self._data:
            raise ValidationError('initial data not provided, cannot call is_valid()')

        data_valid, errors = self._check_input_data_for_missing_values()
        self.errors.update(errors)
        if not data_valid:
            return False

        tasks = [self.fields.get(name).to_internal_value(value)
                 for name, value in self._data.items()]

        values, errors = zip(*await asyncio.gather(*tasks))
        self._errors.update({field: error for field, error
                             in zip(self._data.keys(), errors) if error})

        is_valid = not bool(self._errors)
        if is_valid:
            self._validated_data = {field: value for field, value
                                    in zip(self._data.keys(), values) if value}

        return is_valid

    async def to_dict(self):
        if self._data and not self.validated_data:
            raise ValidationError('first call is_valid')

        tasks = [field.to_representation(getattr(self._instance, name, self._instance))
                 for name, field in self.fields.items()]
        values = await asyncio.gather(*tasks)

        return {name: value for name, value in zip(self.fields.keys(), values)}

    async def save(self, to_dict=False):
        if self._errors:
            raise ValidationError('cannot save, data not valid')
        elif self._data is not None and self._validated_data is None:
            raise ValidationError('run is_valid first')

        try:
            self._instance = self.model(**self._validated_data)
            await self._instance.save()
        except exceptions.IntegrityError:
            self._errors.update({'error': 'cannot save instance'})

        if to_dict:
            return await self.to_dict()

        return self._instance

    async def update(self):
        if self._errors:
            raise ValueError('cannot update, data not valid')
        elif self._validated_data is None:
            raise ValueError('run is_valid first')

        for attr, value in self._validated_data.items():
            setattr(self._instance, attr, value)

        status = True
        try:
            await self._instance.save()
        except exceptions.IntegrityError:
            self._errors = 'cannot update instance, internal error'
            status = False

        return status

    async def delete(self):
        pass

    @property
    def validated_data(self):
        return self._validated_data

    @property
    def errors(self):
        return self._errors
