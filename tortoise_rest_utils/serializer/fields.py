from datetime import datetime


class SerializerField:
    def setup_from_model_field(self, model_attr):
        setattr(self, '_required_on_save', model_attr.required)
        setattr(self, '_required_on_update', model_attr.required)

    async def to_internal_value(self, value):
        if value is None and not any([self._required_on_save, self._required_on_update]):
            return None, None

    @property
    def required_on_save(self):
        return self._required_on_save

    @property
    def required_on_update(self):
        return self._required_on_update


class RelatedField(SerializerField):
    def __init__(self, queryset=None, many=False):
        self._queryset = queryset
        self._many = many

    async def to_internal_value(self, value):
        await super().to_internal_value(value)

        if self._many:
            db_data = await self._queryset().filter(**{self._slug_field: value})
        else:
            db_data = await self._queryset().filter(**{self._slug_field: value}).first()

        if db_data:
            return db_data, None
        else:
            return None, f'{value} does not exists'


class PrimaryKeyField(RelatedField):
    pass


class SlugRelatedField(RelatedField):
    def __init__(self, *args, slug_field=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._slug_field = slug_field

    async def to_representation(self, value):
        if not self._many:
            instance = await value.first()
            return getattr(instance, self._slug_field)
        else:
            instances = await value.all()
            return [getattr(instance, self._slug_field) for instance in instances]


class IntegerField(SerializerField):
    async def to_representation(self, value):
        return value

    async def to_internal_value(self, value):
        await super().to_internal_value(value)
        try:
            return int(value), None
        except (TypeError, ValueError):
            return None, 'incorrect value, cannot transform to integer'


class StringField(SerializerField):
    async def to_representation(self, value):
        return str(value)

    async def to_internal_value(self, value):
        await super().to_internal_value(value)
        if not isinstance(value, (int, float, str)):
            return None, 'incorrect value, cannot transform to string'

        return str(value), None


class DateTimeField(SerializerField):
    async def to_representation(self, value):
        return value.strftime('%Y-%m-%d %H:%M:%S')

    async def to_internal_value(self, value):
        await super().to_internal_value(value)
        try:
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S'), None
        except ValueError:
            return None, 'incorrect value, cannot transform to datetime'

    def setup_from_model_field(self, model_attr):
        if model_attr.auto_now_add:
            required_on_save = False
        else:
            required_on_save = model_attr.required

        if model_attr.auto_now:
            required_on_update = False
        else:
            required_on_update = model_attr.required

        setattr(self, '_required_on_save', required_on_save)
        setattr(self, '_required_on_update', required_on_update)


class BinaryField(SerializerField):
    async def to_representation(self, value):
        return value.decode('utf-8')

    async def to_internal_value(self, value):
        await super().to_internal_value(value)
        try:
            return value.encode('utf-8'), None
        except ValueError:
            return None, 'incorrect value, cannot transform to binary'


class MethodField(SerializerField):
    def __init__(self, method):
        self._method = method

    def to_internal_value(self, value):
        raise ValueError('method field is read only')

    async def to_representation(self, instance):
        return await self._method(self, instance)

    def setup_from_model_field(self, model_attr):
        setattr(self, '_required_on_save', False)
        setattr(self, '_required_on_update', False)
