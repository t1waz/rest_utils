import asyncio
import unittest

from serializer import Serializer
from serializer.exceptions import ValidationError
from serializer.fields import ForeignKeyField
from serializer.fields import (
    IntegerField,
    StringField,
    BinaryField,
    DateTimeField,
    MethodField,
)
from tests.fixtures import (
    SampleModel,
    SampleModelChild,
    IncorrectModel,
    CorrectSerializerOne,
    CorrectSerializerTwo,
    SampleModelView,
    SampleModelChildView,
)
from tests.helpers import DBHandler
from view import View
from starlette.testclient import TestClient


class TestSerializerMeta(unittest.TestCase):
    def test_missing_serializer_meta(self):
        with self.assertRaises(ValueError):
            class MissingMetaSerializer(Serializer):
                pass

            assert MissingMetaSerializer

    def test_incorrect_serializer_meta_model(self):
        with self.assertRaises(ValueError):
            class IncorrectMetaModelSerializer(Serializer):
                class Meta:
                    model = IncorrectModel

            assert IncorrectMetaModelSerializer

    def test_missing_serializer_meta_fields(self):
        with self.assertRaises(ValueError):
            class MissingMetaFieldsSerializerOne(Serializer):
                class Meta:
                    model = SampleModel

            assert MissingMetaFieldsSerializerOne

    def test_incorrect_serializer_meta_fields(self):
        with self.assertRaises(ValueError):
            class IncorrectMetaFieldsSerializerOne(Serializer):
                class Meta:
                    model = SampleModel
                    fields = None

            assert IncorrectMetaFieldsSerializerOne

        with self.assertRaises(ValueError):
            class IncorrectMetaFieldsSerializerTwo(Serializer):
                class Meta:
                    model = SampleModel
                    fields = ()

            assert IncorrectMetaFieldsSerializerTwo

        with self.assertRaises(ValueError):
            class IncorrectMetaFieldsSerializerThree(Serializer):
                class Meta:
                    model = SampleModel
                    fields = ('incorrect_value', )

            assert IncorrectMetaFieldsSerializerThree

        with self.assertRaises(ValueError):
            class IncorrectMetaFieldsSerializerFour(Serializer):
                class Meta:
                    model = SampleModel
                    fields = ('id', 'incorrect_value')

            assert IncorrectMetaFieldsSerializerFour

    def test_incorrect_read_only_fields(self):
        with self.assertRaises(ValueError):
            class IncorrectMetaFieldsSerializerFive(Serializer):
                class Meta:
                    model = SampleModel
                    fields = ('id',)
                    read_only_fields = ('incorrect_value',)

            assert IncorrectMetaFieldsSerializerFive

        with self.assertRaises(ValueError):
            class IncorrectMetaFieldsSerializerSix(Serializer):
                class Meta:
                    model = SampleModel
                    fields = ('id',)
                    read_only_fields = ('id', 'incorrect_value')

            assert IncorrectMetaFieldsSerializerSix

    def test_correct_serializer(self):
        class CorrectSerializerOne(Serializer):
            class Meta:
                model = SampleModel
                fields = ('id', )

        assert CorrectSerializerOne

    def test_incorrect_serializer_foreign_key_declaration(self):
        with self.assertRaises(ValueError):
            class IncorrectMetaRelatedOne(Serializer):
                class Meta:
                    model = SampleModelChild
                    fields = ('id', 'sample_model')

            assert IncorrectMetaRelatedOne

        with self.assertRaises(ValueError):
            class IncorrectMetaRelatedTwo(Serializer):
                incorrect = ForeignKeyField(many=False,
                                            queryset=None,
                                            slug_field='sample_model')

                class Meta:
                    model =  SampleModelChild
                    fields = ('id', 'sample_model')

            assert IncorrectMetaRelatedTwo

        with self.assertRaises(ValueError):
            class IncorrectMetaRelatedThree(Serializer):
                sample_model = ForeignKeyField(many=False,
                                               queryset=None,
                                               slug_field='name')

                class Meta:
                    model = SampleModelChild
                    fields = ('id',)

            assert IncorrectMetaRelatedThree

    def test_serializer_model_initialization(self):
        correct_serializer = CorrectSerializerOne()
        assert hasattr(correct_serializer, 'model')
        assert correct_serializer.model == SampleModel
        assert hasattr(correct_serializer, 'model_pk_field_name')
        assert correct_serializer.model_pk_field_name == SampleModel._meta.pk_attr

    def test_serializer_fields_initalization(self):
        correct_serializer = CorrectSerializerTwo()
        another_serializer = CorrectSerializerTwo()

        correct_serializer_fields = {
            'id': StringField,
            'name': StringField,
            'number': IntegerField,
            'created': DateTimeField,
            'data': BinaryField,
            'sample_model': ForeignKeyField,
            'ser_test': MethodField
        }

        assert hasattr(correct_serializer, 'fields')
        assert hasattr(correct_serializer, 'read_only_fields')
        assert correct_serializer.read_only_fields == ('ser_test', 'created')

        for field_name, field in correct_serializer.fields.items():
            assert isinstance(field, correct_serializer_fields.get(field_name))
            assert id(field) == id(another_serializer.fields.get(field_name))


class TestSerializer(unittest.TestCase):
    def test_serializer_cannot_set_not_tortoise_model_instance(self):
        with self.assertRaises(ValidationError):
            serializer = CorrectSerializerTwo(instance=SampleModel())

            assert serializer

        with self.assertRaises(ValidationError):
            serializer = CorrectSerializerTwo(instance=IncorrectModel())

            assert serializer

    def test_serializer_has_errors(self):
        serializer = CorrectSerializerTwo()

        assert getattr(serializer, 'errors', False) == {}

    def test_check_input_data_if_pk_in_input(self):
        input_data = {
            'id': 23,
            'name': 'test_name should be here because its read only',
            'number': 1,
            'data': 'some data to store',
            'sample_model': 'sample_model',
        }

        serializer = CorrectSerializerTwo(data=input_data)
        is_valid, errors = serializer._check_input_data_for_missing_values()

        assert is_valid is False
        assert errors == {'id': 'primary key, cannot be in input'}

    def test_check_input_data_if_read_only_in_input(self):
        input_data = {
            'name': 'test_name should be here because its read only',
            'number': 1,
            'created': '1990-01-01',
            'data': 'some data to store',
            'sample_model': 'sample_model',
        }

        serializer = CorrectSerializerTwo(data=input_data)
        is_valid, errors = serializer._check_input_data_for_missing_values()

        assert is_valid is False
        assert errors == {'created': 'field is read only'}

    def test_check_input_data_if_serialized_method_in_input(self):
        input_data = {
            'name': 'test_name should be here because its read only',
            'number': 1,
            'ser_test': 'this field should not be included, its method field',
            'data': 'some data to store',
            'sample_model': 'sample_model',
        }

        serializer = CorrectSerializerTwo(data=input_data)
        is_valid, errors = serializer._check_input_data_for_missing_values()

        assert is_valid is False
        assert errors == {'ser_test': 'field is read only'}

    def test_check_input_data_if_missing_input(self):
        input_data = {
            'name': 'test_name should be here because its read only',
            'data': 'some data to store',
            'sample_model': 'sample_model',
        }

        serializer = CorrectSerializerTwo(data=input_data)
        is_valid, errors = serializer._check_input_data_for_missing_values()

        assert is_valid is False
        assert errors == {'number': 'missing in input'}

    def test_check_input_data_for_valid_input(self):
        input_data = {
            'number': 1,
            'name': 'test_name should be here because its read only',
            'data': 'some data to store',
            'sample_model': 'sample_model',
        }

        serializer = CorrectSerializerTwo(data=input_data)
        is_valid, errors = serializer._check_input_data_for_missing_values()
        assert is_valid
        assert not errors

    def test_serializer_is_valid_for_invalid_data(self):
        with DBHandler():
            input_data = {
                'name': 'test name',
                'number': 'aaa',
                'created': 'aaaa',
                'data': 'some data to store',
                'sample_model': 'name number 1',
            }
            serializer = CorrectSerializerTwo(data=input_data)
            is_valid = asyncio.get_event_loop().run_until_complete(serializer.is_valid())

            assert not is_valid
            assert serializer.errors == {'created': 'field is read only'}

            input_data.pop('created')
            serializer = CorrectSerializerTwo(data=input_data)
            is_valid = asyncio.get_event_loop().run_until_complete(serializer.is_valid())

            assert not is_valid
            assert serializer.errors == {'number': 'incorrect value, cannot transform to integer',
                                         'sample_model': 'name number 1 does not exists'}

    def test_serializer_is_valid_for_valid_data(self):
        with DBHandler():
            input_data = {
                'name': 'correct name',
                'number': 23,
                'data': 'some data to store',
                'sample_model': 'model_1',
            }
            serializer = CorrectSerializerTwo(data=input_data)
            is_valid = asyncio.get_event_loop().run_until_complete(serializer.is_valid())

            assert is_valid is True
            assert not serializer.errors

    def test_serializer_save(self):
        with DBHandler():
            input_data = {
                'name': 'correct name',
                'number': 55,
                'data': 'some data to store second',
                'sample_model': 'model_1',
            }
            serializer = CorrectSerializerTwo(data=input_data)
            is_valid = asyncio.get_event_loop().run_until_complete(serializer.is_valid())

            assert is_valid is True
            assert not serializer.errors

            instance = asyncio.get_event_loop().run_until_complete(serializer.save())

            assert isinstance(instance, SampleModelChild)

            for name, value in serializer.validated_data.items():
                assert getattr(instance, name) == value

            dict_instance = asyncio.get_event_loop().run_until_complete(
                serializer.save(to_dict=True))

            assert isinstance(dict_instance, dict)
            assert all(attr in dict_instance for attr in input_data)

    def test_serializer_is_valid_if_no_data(self):
        with DBHandler():
            serializer = CorrectSerializerTwo(data={})
            with self.assertRaises(ValidationError):
                is_valid = asyncio.get_event_loop().run_until_complete(serializer.is_valid())

                assert is_valid

    def test_serializer_is_valid_if_invalid_instance(self):
        class InvalidModel:
            pass

        with self.assertRaises(ValidationError):
            serializer = CorrectSerializerTwo(instance=InvalidModel())

            assert serializer

    def test_serializer_save_invalid_data(self):
        with DBHandler():
            input_data = {
                'name': 'test name',
                'number': 'aaa',
                'created': 'aaaa',
                'data': 'some data to store',
                'sample_model': 'name number 1',
            }
            serializer = CorrectSerializerTwo(data=input_data)
            is_valid = asyncio.get_event_loop().run_until_complete(serializer.is_valid())

            assert not is_valid

            with self.assertRaises(ValidationError):
                instance = asyncio.get_event_loop().run_until_complete(serializer.save())

                assert instance

            serializer = CorrectSerializerTwo(data={})
            with self.assertRaises(ValidationError):
                instance = asyncio.get_event_loop().run_until_complete(serializer.save())

                assert instance

    def test_serializer_get_dict_for_valid_data(self):
        with DBHandler():
            input_data = {
                'name': 'correct name',
                'number': 55,
                'data': 'some data to store second',
                'sample_model': 'model_1',
            }
            serializer = CorrectSerializerTwo(data=input_data)
            is_valid = asyncio.get_event_loop().run_until_complete(serializer.is_valid())

            assert is_valid is True
            assert not serializer.errors

            instance = asyncio.get_event_loop().run_until_complete(serializer.save())

            assert instance

            dict_instance = asyncio.get_event_loop().run_until_complete(serializer.to_dict())

            assert isinstance(dict_instance, dict)
            assert 'id' in dict_instance
            assert all(attr in dict_instance for attr in input_data)

    def test_serializer_update(self):
        pass


class TestViewMeta(unittest.TestCase):
    def test_missing_queryset_in_view(self):
        with self.assertRaises(ValueError):
            class MissingQuerysetView(View):
                pass

            assert MissingQuerysetView

    def test_missing_serializer_class_in_view(self):
        with self.assertRaises(ValueError):
            class MissingSerializerClassView(View):
                pass

            assert MissingSerializerClassView


class TestView(unittest.TestCase):
    def test_get_instance(self):
        pass
        # with DBHandler():
        #     sample_model = asyncio.get_event_loop().run_until_complete(SampleModel.first())
        #     client = TestClient(SampleModelView)
        #     print(client.request(params="1", method='GET', url=f'/{sample_model.id}'))
        #     print(f'/{sample_model.id}')
        #     response = client.get(f'/{sample_model.id}')
        #
        #     # request = FakeRequest(path_params={'id': sample_model.id})
        #     # function = getattr(View, 'get')
        #     # response = asyncio.get_event_loop().run_until_complete(function(SampleModelView, request))
        #     # print(response)
        #     assert 1 == 0

    def test_get_instances(self):
        pass

    def test_post(self):
        pass

    def test_update(self):
        pass

    def test_delete(self):
        pass


if __name__ == '__main__':
    unittest.main()
