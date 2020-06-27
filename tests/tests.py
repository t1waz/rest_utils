import asyncio
import json
import unittest

from async_easy_utils.serializer import Serializer
from async_easy_utils.serializer.exceptions import ValidationError
from async_easy_utils.serializer.fields import (
    IntegerField,
    StringField,
    BinaryField,
    DateTimeField,
    MethodField,
)
from async_easy_utils.serializer.fields import SlugRelatedField
from async_easy_utils.view import View
from tests.fixtures import (
    SampleModel,
    SampleModelChild,
    IncorrectModel,
    CorrectSerializerOne,
    CorrectSerializerTwo,
    CorrectSerializerFour,
    SampleModelView,
    SampleModelGroups,
    CorrectSerializerFive,
)
from tests.helpers import (
    DBHandler,
    FakeRequest,
)


class TestSerializerMeta(unittest.TestCase):
    def test_missing_serializer_meta(self):
        with self.assertRaises(ValueError):
            class MissingMetaSerializer(Serializer):
                pass

            assert MissingMetaSerializer

    def test_missing_serializer_meta_model(self):
        with self.assertRaises(ValueError):
            class MissingModelSerializer(Serializer):
                class Meta:
                    pass

            assert MissingModelSerializer

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

    def test_incorrect_serializer_related_field_declaration(self):
        with self.assertRaises(ValueError):
            class IncorrectMetaRelatedOne(Serializer):
                class Meta:
                    model = SampleModelChild
                    fields = ('id', 'sample_model')

            assert IncorrectMetaRelatedOne

        with self.assertRaises(ValueError):
            class IncorrectRelatedField(Serializer):
                sample_model = None

                class Meta:
                    model = SampleModelChild
                    fields = ('id', 'sample_model')

            assert IncorrectRelatedField

        with self.assertRaises(ValueError):
            class IncorrectMetaRelatedTwo(Serializer):
                incorrect = SlugRelatedField(many=False,
                                             queryset=None,
                                             slug_field='sample_model')

                class Meta:
                    model = SampleModelChild
                    fields = ('id', 'sample_model')

            assert IncorrectMetaRelatedTwo

        with self.assertRaises(ValueError):
            class IncorrectMetaRelatedThree(Serializer):
                sample_model = SlugRelatedField(many=False,
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

    def test_serializer_fields_initialization(self):
        correct_serializer = CorrectSerializerTwo()
        another_serializer = CorrectSerializerTwo()

        correct_serializer_fields = {
            'id': StringField,
            'name': StringField,
            'number': IntegerField,
            'created': DateTimeField,
            'data': BinaryField,
            'sample_model': SlugRelatedField,
            'ser_test': MethodField
        }

        assert hasattr(correct_serializer, 'fields')

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

    def test_passing_not_dict_data_to_serializer(self):
        with self.assertRaises(ValidationError):
            serializer = CorrectSerializerTwo(data='not dict')

            assert serializer

    def test_if_datetime_field_return_correct_value_for_is_m2m(self):
        datetime_field = DateTimeField()

        assert getattr(datetime_field, 'is_m2m', None) is False

    def test_if_method_field_return_correct_value_for_is_m2m(self):
        method_field = MethodField(method=lambda x: x)

        assert getattr(method_field, 'is_m2m', None) is False

    def test_if_calling_to_interval_value_for_method_field_raise_error(self):
        method_field = MethodField(method=lambda x: x)
        with self.assertRaises(ValueError):
            method_field.to_internal_value('test_value')

    def test_incorrect_value_for_datetime_field(self):
        with DBHandler():
            input_data = {
                'name': 'test_name should be here because its read only',
                'number': 434,
                'data': 'another data to store',
                'sample_model': 'model_1',
                'created': "not valid datetime value"
            }

            serializer = CorrectSerializerFive(data=input_data)
            is_valid = asyncio.get_event_loop().run_until_complete(serializer.is_valid())

            assert is_valid is False
            assert 'created' in serializer.errors

    def test_incorrect_value_for_binary_field(self):
        with DBHandler():
            input_data = {
                'name': 'test_name should be here because its read only',
                'number': 434,
                'data': 1.0,
                'sample_model': 'model_1',
                'created': '1990-01-01 11:01:01',
            }

            serializer = CorrectSerializerFive(data=input_data)
            is_valid = asyncio.get_event_loop().run_until_complete(serializer.is_valid())

            assert is_valid is False
            assert 'data' in serializer.errors

    def test_check_input_data_if_pk_in_input(self):
        input_data = {
            'id': 23,
            'name': 'aaaa',
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

    def test_serializer_get_dict_without_is_valid(self):
        with self.assertRaises(ValidationError):
            serializer = CorrectSerializerTwo(data={'data': {'some_data'}})
            asyncio.get_event_loop().run_until_complete(serializer.to_dict())

    def test_serializer_update(self):
        pass

    def test_get_serializer_slug_related_field_many(self):
        with DBHandler():
            sample_model_groups = asyncio.get_event_loop().run_until_complete(
                SampleModelGroups.all())

            for sample_model_group in sample_model_groups:
                serializer = CorrectSerializerFour(instance=sample_model_group)
                serialized_object = asyncio.get_event_loop().run_until_complete(
                    serializer.to_dict())

                assert serialized_object['id'] == sample_model_group.id
                assert serialized_object['name'] == sample_model_group.name

                sample_models = asyncio.get_event_loop().run_until_complete(
                    sample_model_group.sample_models.all().values_list('name', flat=True))
                assert serialized_object['sample_models'] == sample_models

    def test_save_serializer_slug_related_field_many(self):
        with DBHandler():
            input_data = {
                'name': 'group_3',
                'sample_models': ['model_2', 'model_3'],
            }
            serializer = CorrectSerializerFour(data=input_data)
            is_valid = asyncio.get_event_loop().run_until_complete(serializer.is_valid())

            assert is_valid is True
            assert not serializer.errors

            instance = asyncio.get_event_loop().run_until_complete(serializer.save())
            assert instance


class TestViewMeta(unittest.TestCase):
    def test_missing_queryset_in_view(self):
        with self.assertRaises(ValueError):
            class MissingQuerysetView(View):
                pass

            assert MissingQuerysetView

    def test_missing_serializer_class_in_view(self):
        with self.assertRaises(ValueError):
            class MissingSerializerClassView(View):
                queryset = None

            assert MissingSerializerClassView


class TestView(unittest.TestCase):
    def setUp(self):
        self.sample_model_view = SampleModelView({'type': 'http'}, None, None)

    def test_get_list(self):
        with DBHandler():
            response = asyncio.get_event_loop().run_until_complete(
                self.sample_model_view.list(FakeRequest()))
            response_data = json.loads(response.body.decode())
            sample_models = asyncio.get_event_loop().run_until_complete(
                SampleModel.all()
            )
            models_dicts = [{'id': sample_model.id, 'name': sample_model.name}
                            for sample_model in sample_models]

            assert models_dicts == response_data

    def test_get_correct_instance(self):
        with DBHandler():
            sample_model = asyncio.get_event_loop().run_until_complete(SampleModel.first())
            response = asyncio.get_event_loop().run_until_complete(
                self.sample_model_view.instance(FakeRequest(url_params={'id': sample_model.id})))
            response_data = json.loads(response.body.decode())

            assert {'id': sample_model.id, 'name': sample_model.name} == response_data

    def test_get_incorrect_instance(self):
        with DBHandler():
            response = asyncio.get_event_loop().run_until_complete(
                self.sample_model_view.instance(FakeRequest(url_params={'id': 'invalid id'})))
            response_data = json.loads(response.body.decode())

            assert response_data == {'detail': 'not found'}

    def test_create_for_invalid_url(self):
        with DBHandler():
            response = asyncio.get_event_loop().run_until_complete(
                self.sample_model_view.create(FakeRequest(url_params={'id': 'invalid id'})))
            response_data = json.loads(response.body.decode())

            assert response_data == {'detail': 'Method POST not allowed.'}

    def test_create_for_incorrect_data(self):
        with DBHandler():
            response = asyncio.get_event_loop().run_until_complete(
                self.sample_model_view.create(FakeRequest(data=b'/x///')))
            response_data = json.loads(response.body.decode())

            assert response_data == {'detail': 'invalid request for create.'}

    def test_create_for_invalid_data(self):
        with DBHandler():
            response = asyncio.get_event_loop().run_until_complete(
                self.sample_model_view.create(FakeRequest(data={'name': [1, 2, 3]})))
            response_data = json.loads(response.body.decode())

            assert response_data == {'detail': {'name': 'incorrect value, cannot transform to string'}}

    def test_create(self):
        with DBHandler():
            create_data = {'name': 'correct name'}
            response = asyncio.get_event_loop().run_until_complete(
                self.sample_model_view.create(FakeRequest(data={'name': 'correct name'})))
            response_data = json.loads(response.body.decode())

            new_instance = asyncio.get_event_loop().run_until_complete(
                SampleModel.get(**create_data))

            assert {'id': new_instance.id, 'name': new_instance.name} == response_data

    def test_update_for_invalid_url(self):
        response = asyncio.get_event_loop().run_until_complete(
            self.sample_model_view.update(FakeRequest(url_params={})))
        response_data = json.loads(response.body.decode())

        assert response_data == {'detail': 'Method PATCH not allowed.'}

    def test_update_for_incorrect_data(self):
        with DBHandler():
            sample_model = asyncio.get_event_loop().run_until_complete(SampleModel.first())
            response = asyncio.get_event_loop().run_until_complete(
                self.sample_model_view.update(FakeRequest(url_params={'id': sample_model.id},
                                                      data=b'/x///')))
            response_data = json.loads(response.body.decode())

            assert response_data == {'detail': 'invalid request for update'}

    def test_update_for_not_existing_pk(self):
        response = asyncio.get_event_loop().run_until_complete(
            self.sample_model_view.update(FakeRequest(url_params={'id': 'aa'},
                                                      data={'name': 'correct name'})))
        response_data = json.loads(response.body.decode())

        assert response_data == {'detail': 'objects does not exists'}

    def test_update_for_invalid_data(self):
        with DBHandler():
            sample_model = asyncio.get_event_loop().run_until_complete(SampleModel.first())
            response = asyncio.get_event_loop().run_until_complete(
                self.sample_model_view.update(FakeRequest(url_params={'id': sample_model.id},
                                                          data={'name': [1, 2, 3]})))
            response_data = json.loads(response.body.decode())

            assert response_data == {
                'detail': {
                    'name': 'incorrect value, cannot transform to string'
                }
            }

    def test_update(self):
        with DBHandler():
            update_data = {'name': 'updated name'}
            sample_model = asyncio.get_event_loop().run_until_complete(SampleModel.first())
            response = asyncio.get_event_loop().run_until_complete(
                self.sample_model_view.update(FakeRequest(url_params={'id': sample_model.id},
                                                          data=update_data)))
            response_data = json.loads(response.body.decode())
            sample_model = asyncio.get_event_loop().run_until_complete(
                SampleModel.get(**update_data))

            assert response_data == {
                'id': sample_model.id,
                'name': sample_model.name
            }

    def test_delete_for_incorrect_url(self):
        response = asyncio.get_event_loop().run_until_complete(
            self.sample_model_view.delete(FakeRequest()))
        response_data = json.loads(response.body.decode())

        assert response_data == {'detail': 'Method DELETE not allowed.'}

    def test_delete_for_invalid_url(self):
        response = asyncio.get_event_loop().run_until_complete(
            self.sample_model_view.update(FakeRequest(url_params={'id': 'aaa'})))
        response_data = json.loads(response.body.decode())

        assert response_data == {'detail': 'invalid request for update'}

    def test_delete(self):
        with DBHandler():
            sample_model = asyncio.get_event_loop().run_until_complete(SampleModel.first())
            response = asyncio.get_event_loop().run_until_complete(
                self.sample_model_view.delete(FakeRequest(url_params={'id': sample_model.id})))
            response_data = json.loads(response.body.decode())

            assert response_data == {'deleted': True}
            assert asyncio.get_event_loop().run_until_complete(
                SampleModel.filter(id=sample_model.id)) == []


if __name__ == '__main__':
    unittest.main()
