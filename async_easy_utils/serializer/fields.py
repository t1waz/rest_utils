from datetime import datetime


class SerializerField:
    async def to_internal_value(self, value):
        raise NotImplementedError()  # pragma: no cover

    async def to_representation(self, value):
        raise NotImplementedError()  # pragma: no cover

    @property
    def is_m2m(self):
        raise NotImplementedError()  # pragma: no cover

    @property
    def read_only(self):
        return getattr(self, '_read_only', False)

    @read_only.setter
    def read_only(self, value):
        self._read_only = value


class RelatedField(SerializerField):
    def __init__(self, queryset=None, many=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._queryset = queryset
        self._many = many

    async def to_internal_value(self, value):
        if self._many:
            db_data = await self._queryset().filter(**{f'{self._slug_field}__in': value})
        else:
            db_data = await self._queryset().filter(**{self._slug_field: value}).first()

        if db_data:
            return db_data, None
        else:
            return None, f'{value} does not exists'

    async def to_representation(self, value):
        return value

    @property
    def is_m2m(self):
        return self._many


class PrimaryKeyField(RelatedField):
    pass


class SlugRelatedField(RelatedField):
    def __init__(self, slug_field=None, *args, **kwargs):
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
        return int(value)

    async def to_internal_value(self, value):
        try:
            return int(value), None
        except (TypeError, ValueError):
            return None, 'incorrect value, cannot transform to integer'

    @property
    def is_m2m(self):
        return False


class StringField(SerializerField):
    async def to_representation(self, value):
        return str(value)

    async def to_internal_value(self, value):
        if not isinstance(value, (int, float, str)):
            return None, 'incorrect value, cannot transform to string'

        return str(value), None

    @property
    def is_m2m(self):
        return False


class DateTimeField(SerializerField):
    async def to_representation(self, value):
        return value.strftime('%Y-%m-%d %H:%M:%S')

    async def to_internal_value(self, value):
        try:
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S'), None
        except ValueError:
            return None, 'incorrect value, cannot transform to datetime'

    @property
    def is_m2m(self):
        return False


class BinaryField(SerializerField):
    async def to_representation(self, value):
        return value.decode('utf-8')

    async def to_internal_value(self, value):
        try:
            return value.encode('utf-8'), None
        except (ValueError, AttributeError):
            return None, 'incorrect value, cannot transform to binary'

    @property
    def is_m2m(self):
        return False


class MethodField(SerializerField):
    def __init__(self, method, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._method = method

    def to_internal_value(self, value):
        raise ValueError('method field is read only')

    async def to_representation(self, instance):
        return await self._method(self, instance)

    @property
    def is_m2m(self):
        return False

    @property
    def read_only(self):
        return True

    @read_only.setter
    def read_only(self, value):
        pass
