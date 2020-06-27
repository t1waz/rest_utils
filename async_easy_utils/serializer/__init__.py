import asyncio
from collections import OrderedDict

from tortoise import fields as model_fields
from tortoise import transactions
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

    @classmethod
    def _setup_fields_from_meta(cls, meta, instance, attrs):
        read_only_fields = getattr(meta, 'read_only_fields', ())

        instance.fields = OrderedDict()
        for field_name in meta.fields:
            if field_name not in attrs.keys():
                model_field = meta.model._meta.fields_map.get(field_name)
                field_class = cls.FIELD_MAPPING.get(model_field.__class__, MethodField)

                if field_class is MethodField:
                    field = field_class(method=attrs.get(f'get_{field_name}'))
                else:
                    field = field_class()
            else:
                field = attrs.get(field_name)

            field.read_only = field_name in read_only_fields
            instance.fields[field_name] = field

    def __new__(cls, name, bases, attrs, **kwargs):
        instance = super().__new__(cls, name, bases, attrs, **kwargs)
        if not bases:
            return instance

        SerializerMetaValidator.validate(instance, attrs)

        meta = attrs.get('Meta')
        instance.model = meta.model
        instance.model_pk_field_name = instance.model._meta.pk_attr

        cls._setup_fields_from_meta(meta, instance, attrs)

        return instance


class Serializer(metaclass=SerializerMeta):
    def __init__(self, instance=None, data=None):
        if instance and not issubclass(instance.__class__, self.model):
            raise ValidationError(f'{self.__class__.__name__} instance not serializer model class')

        if data and not isinstance(data, dict):
            raise ValidationError(f'{self.__class__.__name__} data is not dict')

        self._errors = {}
        self._instance = instance

        self._data = data
        self._validated_data = {}
        self._instance_validated_data = {}
        self._instance_related_validated_data = {}

    def _check_input_data_for_missing_values(self):
        errors = {}
        valid = True

        data_read_only_mapping = {field_name: field_name in self._data for field_name, field in
                                  self.fields.items() if field.read_only}
        if any(data_read_only_mapping.values()):
            valid = False
            errors.update({field_name: 'field is read only' for field_name, is_read_only in
                           data_read_only_mapping.items() if is_read_only})

        if self.model_pk_field_name in self._data.keys():
            valid = False
            errors[self.model_pk_field_name] = 'primary key, cannot be in input'

        allowed_fields = (field_name for field_name, field in
                          self.fields.items() if not field.read_only)
        missing_fields = set(allowed_fields).difference(set(self._data.keys()))
        missing_fields.discard(self.model_pk_field_name)
        if missing_fields:
            valid = False
            errors.update({field: 'missing in input' for field in missing_fields})

        return valid, errors

    @transactions.atomic()
    async def _handle_m2m_data(self):
        success = True
        for attr_name, values in self._instance_related_validated_data.items():
            m2m_attr_manager = getattr(self._instance, attr_name, None)

            try:
                await m2m_attr_manager.add(*values)
            except (ValueError, AttributeError):
                success = False
                self._errors[attr_name] = f'cannot save with with value/values {values}'
                break

        return success

    def _set_validated_data(self, data):
        self._validated_data = data

        for field, value in self._validated_data.items():
            if self.fields.get(field).is_m2m:
                self._instance_related_validated_data[field] = value
            else:
                self._instance_validated_data[field] = value

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
            self._set_validated_data({name: value for name, value in
                                      zip(self._data.keys(), values)})

        return is_valid

    def _validate_can_perform_write_operation(self):
        if self.errors:
            raise ValidationError('invalid data')
        elif self._data is not None and not self._validated_data:
            raise ValidationError('run is_valid first')

    async def save(self, to_dict=False):
        self._validate_can_perform_write_operation()

        try:
            self._instance = self.model(**self._instance_validated_data)
            await self._instance.save()
        except (ValueError, AttributeError):
            self._instance = None
            self._errors.update({'error': 'cannot save instance'})

            return self._instance

        m2m_save = await self._handle_m2m_data()
        if not m2m_save:
            self._instance = None
            await self._instance.delete()

            return self._instance

        if to_dict:
            return await self.to_dict()

        return self._instance

    async def update(self):
        self._validate_can_perform_write_operation()

        for attr, value in self._instance_validated_data.items():
            setattr(self._instance, attr, value)

        status = await self._handle_m2m_data()
        if not status:
            return status

        try:
            await self._instance.save()
        except (ValueError, AttributeError):
            self._errors = 'cannot update instance, internal error'
            status = False

        return status

    async def delete(self):
        pass

    async def to_dict(self):
        if not self._instance:
            raise ValidationError('first call is_valid')

        tasks = [field.to_representation(getattr(self._instance, name, self._instance))
                 for name, field in self.fields.items()]
        values = await asyncio.gather(*tasks)

        return {name: value for name, value in zip(self.fields.keys(), values)}

    @property
    def validated_data(self):
        return self._validated_data

    @property
    def errors(self):
        return self._errors
