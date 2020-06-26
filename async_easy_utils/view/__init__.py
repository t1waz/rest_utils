import asyncio

from starlette.concurrency import run_in_threadpool
from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse
from tortoise import exceptions

from async_easy_utils.view.validators import ViewMetaValidator


class ViewMeta(type):
    def __new__(cls, name, bases, attrs, **kwargs):
        instance = super().__new__(cls, name, bases, attrs, **kwargs)
        if not bases or HTTPEndpoint in bases:
            return instance

        ViewMetaValidator.validate(instance, attrs)

        instance.get_queryset = attrs['get_queryset']
        instance.serializer = attrs['serializer_class']

        return instance


class View(HTTPEndpoint, metaclass=ViewMeta):
    action_mapping = {
        'get-list': 'list',
        'get-instance': 'instance',
        'post-list': 'create',
        'patch-instance': 'update',
        'delete-instance': 'delete',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.get_queryset()
        self.response_data = {
            'content': {},
            'status_code': 200
        }

    async def dispatch(self) -> None:  # pragma: no cover
        request = Request(self.scope, receive=self.receive)
        request_method = "get" if request.method == "HEAD" else request.method.lower()
        if 'id' in request.path_params:
            request_type = 'instance'
        else:
            request_type = 'list'

        handler_name = self.action_mapping.get(f'{request_method}-{request_type}')
        handler = getattr(self, handler_name, self.method_not_allowed)
        is_async = asyncio.iscoroutinefunction(handler)
        if is_async:
            response = await handler(request)
        else:
            response = await run_in_threadpool(handler, request)
        await response(self.scope, self.receive, self.send)

    @staticmethod
    async def get_request_data(request):
        try:
            data = await request.json()
            return dict(data)
        except (ValueError, TypeError):
            return None

    async def get_instance_from_pk(self, pk):
        try:
            return await self.queryset.get(**{self.serializer_class.model_pk_field_name: pk})
        except (exceptions.DoesNotExist, ValueError):
            return None

    async def list(self, request):
        instances = await self.queryset
        tasks = [self.serializer_class(instance=instance).to_dict() for instance in instances]
        self.response_data['content'] = await asyncio.gather(*tasks)

        return JSONResponse(**self.response_data)

    async def instance(self, request):
        instance = await self.get_instance_from_pk(request.path_params.get('id'))
        if instance:
            self.response_data['content'] = await self.serializer(instance=instance).to_dict()
        else:
            self.response_data['status_code'] = 404
            self.response_data['content'] = {'detail': 'not found'}

        return JSONResponse(**self.response_data)

    @staticmethod
    def get_not_allowed_response(request_method):
        return {
            'status_code': 405,
            'content': {
                'detail': f'Method {request_method} not allowed.'
            }
        }

    @staticmethod
    def get_invalid_response(request_action):
        return {
            'status_code': 400,
            'content': {
                'detail': f'invalid request for {request_action}.'
            }
        }

    async def create(self, request):
        if 'id' in request.path_params.keys():
            return JSONResponse(**self.get_not_allowed_response('POST'))

        data = await self.get_request_data(request)
        if not data:
            return JSONResponse(**self.get_invalid_response('create'))

        serializer = self.serializer_class(data=data)
        is_valid = await serializer.is_valid()

        if not is_valid:
            self.response_data['status_code'] = 400
            self.response_data['content'] = {'detail': serializer.errors or 'incorrect input data'}

            return JSONResponse(**self.response_data)

        if not await serializer.save():
            self.response_data['status_code'] = 500
            self.response_data['content'] = {'detail': 'cannot create, internal error'}

            return JSONResponse(**self.response_data)

        self.response_data['status_code'] = 201
        self.response_data['content'] = await serializer.to_dict()

        return JSONResponse(**self.response_data)

    async def update(self, request):
        pk = request.path_params.get('id')
        if not pk:
            return JSONResponse(**self.get_not_allowed_response('PATCH'))

        data = await self.get_request_data(request)
        if not data:
            self.response_data['status_code'] = 400
            self.response_data['content'] = {'detail': 'invalid request for update'}

            return JSONResponse(**self.response_data)

        instance = await self.get_instance_from_pk(pk)
        if not instance:
            self.response_data['status_code'] = 404
            self.response_data['content'] = {'detail': 'objects does not exists'}

            return JSONResponse(**self.response_data)

        serializer = self.serializer_class(instance=instance, data=data)
        is_valid = await serializer.is_valid()
        if not is_valid:
            self.response_data['status_code'] = 404
            self.response_data['content'] = {'detail': serializer.errors}

            return JSONResponse(**self.response_data)

        is_updated = await serializer.update()
        if not is_updated:
            self.response_data['status_code'] = 404
            self.response_data['content'] = serializer.errors

            return JSONResponse(**self.response_data)

        self.response_data['content'] = await serializer.to_dict()

        return JSONResponse(**self.response_data)

    async def delete(self, request):
        pk = request.path_params.get('id')
        if not pk:
            return JSONResponse(**self.get_not_allowed_response('DELETE'))

        instance = await self.get_instance_from_pk(pk)
        if not instance:
            self.response_data['status_code'] = 404
            self.response_data['content'] = {'detail': 'objects does not exists'}
        else:
            await instance.delete()
            self.response_data['content'] = {'deleted': True}

        return JSONResponse(**self.response_data)
