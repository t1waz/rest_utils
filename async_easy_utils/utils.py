class MetaValidatorMixin:
    @classmethod
    def validate(cls, instance, attrs):
        obj = cls(instance, attrs)

        for validator in (getattr(obj, validator_name) for validator_name in dir(obj)
                          if validator_name.startswith('check')):
            validator()
