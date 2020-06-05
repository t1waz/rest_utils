from async_easy_utils.utils import MetaValidatorMixin


class ViewMetaValidator(MetaValidatorMixin):
    def __init__(self, instance, attrs):
        self._instance = instance
        self._attrs = attrs

    def check_if_queryset_exists(self):
        if 'get_queryset' not in self._attrs:
            raise ValueError(f'{self._instance.__name__} missing queryset in view')

    def check_if_serializer_class_exists(self):
        if 'serializer_class' not in self._attrs:
            raise ValueError(f'{self._instance.__name__} missing serializer_class in view')

    def check_if_serializer_class_is_serializer_instance(self):
        pass    # TODO
