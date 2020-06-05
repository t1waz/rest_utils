import asyncio
from collections import OrderedDict

from tortoise import fields as model_fields
from tortoise.fields.relational import ForeignKeyFieldInstance

from async_easy_utils.serializer.exceptions import ValidationError
from async_easy_utils.serializer.fields import (
    StringField,
    IntegerField,
    RelatedField,
    DateTimeField,
    BinaryField,
    MethodField,
)
from async_easy_utils.serializer.validators import SerializerMetaValidator


class SerializerMeta(type):
    FIELD_MAPPING = {
        model_fields.UUIDField: StringField,
        model_fields.TextField: StringField,
        model_fields.IntField: IntegerField,
        model_fields.DatetimeField: DateTimeField,
        model_fields.BinaryField: BinaryField,
        ForeignKeyFieldInstance: RelatedField,
    }

    def __new__(cls, name, bases, attrs, **kwargs):
        instance = super().__new__(cls, name, bases, attrs, **kwargs)
        if not bases:
            return instance

        SerializerMetaValidator.validate(instance, attrs)

        meta = attrs.get('Meta')
        instance.model = meta.model
        instance.model_pk_field_name = instance.model._meta.pk_attr
        instance.fields = OrderedDict()

        for field_name in meta.fields:
            model_field = meta.model._meta.fields_map.get(field_name)
            field = cls.FIELD_MAPPING.get(model_field.__class__, MethodField)

            if field is MethodField:
                field = field(method=attrs.get(f'get_{field_name}'))
            elif field is RelatedField:
                field = attrs.get(field_name)
            else:
                field = field()

            field.setup_from_model_field(model_field)
            instance.fields[field_name] = field

        instance.read_only_fields = tuple(name for name, field in instance.fields.items() if
                                          isinstance(field, MethodField))
        meta_read_only_fields = getattr(meta, 'read_only_fields', None)
        if meta_read_only_fields:
            instance.read_only_fields = instance.read_only_fields + meta_read_only_fields

        return instance


class Serializer(metaclass=SerializerMeta):
    def __init__(self, instance=None, data=None):
        if instance and not issubclass(instance.__class__, self.model):
            raise ValidationError(f'{self.__class__.__name__} instance not serializer model class')

        if data and not isinstance(data, dict):
            raise ValidationError(f'{self.__class__.__name__} data is not dict')

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
        if not self._instance:
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
        except (ValueError, AttributeError):
            self._errors.update({'error': 'cannot save instance'})
            self._instance = None

        if to_dict:
            return await self.to_dict()

        return self._instance

    async def update(self):
        if self._errors:
            raise ValidationError('cannot save, data not valid')
        elif self._data is not None and self._validated_data is None:
            raise ValidationError('run is_valid first')

        for attr, value in self._validated_data.items():
            setattr(self._instance, attr, value)

        status = True
        try:
            await self._instance.save()
        except (ValueError, AttributeError):
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
