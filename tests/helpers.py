import asyncio
import datetime

from tortoise import Tortoise

from tests.fixtures import (
    SampleModel,
    SampleModelChild,
    SampleModelGroups,
)


async def init_models():
    sample_model_1 = SampleModel(name='model_1')
    await sample_model_1.save()

    sample_model_2 = SampleModel(name='model_2')
    await sample_model_2.save()

    sample_model_3 = SampleModel(name='model_3')
    await sample_model_3.save()

    sample_model_child_1 = SampleModelChild(name='child_1',
                                            number=1,
                                            data=b'1',
                                            sample_model=sample_model_1,
                                            created=datetime.datetime.now())
    await sample_model_child_1.save()

    sample_model_child_2 = SampleModelChild(name='child_2',
                                            number=2,
                                            data=b'2',
                                            sample_model=sample_model_2,
                                            created=datetime.datetime.now())
    await sample_model_child_2.save()

    sample_model_child_3 = SampleModelChild(name='child_3',
                                            number=3,
                                            data=b'3',
                                            sample_model=sample_model_3,
                                            created=datetime.datetime.now())
    await sample_model_child_3.save()

    sample_model_4 = SampleModelChild(name='child_4',
                                      number=4,
                                      data=b'4',
                                      sample_model=sample_model_1,
                                      created=datetime.datetime.now())
    await sample_model_4.save()

    sample_model_group_1 = SampleModelGroups(name='group_1')
    await sample_model_group_1.save()
    await sample_model_group_1.sample_models.add(sample_model_1, sample_model_2)

    sample_model_group_2 = SampleModelGroups(name='group_2')
    await sample_model_group_2.save()
    await sample_model_group_2.sample_models.add(sample_model_1, sample_model_3)


class DBHandler:
    def __enter__(self, *args, **kwargs):
        asyncio.get_event_loop().run_until_complete(self.open_db())
        asyncio.get_event_loop().run_until_complete(self.clear_models())
        asyncio.get_event_loop().run_until_complete(init_models())

    def __exit__(self, *args, **kwargs):
        asyncio.get_event_loop().run_until_complete(self.close_db())

    @classmethod
    async def clear_models(cls):
        await SampleModel.all().delete()
        await SampleModelChild.all().delete()
        await SampleModelGroups.all().delete()

    @classmethod
    async def open_db(cls):
        await Tortoise.init(db_url='sqlite://:memory1:',
                            modules={'tests': ['tests.fixtures']})
        await Tortoise.generate_schemas()

    @classmethod
    async def close_db(cls):
        await Tortoise.close_connections()


class FakeRequest:
    def __init__(self, url_params={}, data=None):
        self._url_params = url_params
        self._data = data

    @property
    def path_params(self):
        return self._url_params

    async def json(self):
        return self._data
