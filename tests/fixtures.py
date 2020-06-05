from tortoise import fields
from tortoise.models import Model

from async_easy_utils.serializer import Serializer
from async_easy_utils.serializer.fields import SlugRelatedField
from async_easy_utils.view import View


class SampleModel(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField(max_length=400)


class SampleModelChild(Model):
    id = fields.UUIDField(pk=True)
    name = fields.TextField(max_length=400)
    number = fields.IntField()
    created = fields.DatetimeField(auto_now_add=True)
    data = fields.BinaryField()
    sample_model = fields.ForeignKeyField('tests.SampleModel', related_name='childs')


class IncorrectModel:
    pass


class CorrectSerializerOne(Serializer):
    class Meta:
        model = SampleModel
        fields = ('id',)


class CorrectSerializerTwo(Serializer):
    sample_model = SlugRelatedField(many=False,
                                    queryset=lambda: SampleModel.all(),
                                    slug_field='name')

    class Meta:
        model = SampleModelChild
        fields = ('id', 'name', 'number', 'created', 'data', 'sample_model', 'ser_test')
        read_only_fields = ('created',)

    async def get_ser_test(self, instance):
        return 'ser_test'


class CorrectSerializerThree(Serializer):
    sample_model = SlugRelatedField(many=False,
                                    queryset=lambda: SampleModel.all(),
                                    slug_field='name')

    class Meta:
        model = SampleModelChild
        fields = ('id', 'sample_model')


class CorrectSerializerFour(Serializer):
    class Meta:
        model = SampleModel
        fields = ('id', 'name')


class SampleModelView(View):
    serializer_class = CorrectSerializerFour

    def get_queryset(self):
        return SampleModel.all()


class SampleModelChildView(View):
    serializer_class = CorrectSerializerTwo

    def get_queryset(self):
        return SampleModelChild.all()
