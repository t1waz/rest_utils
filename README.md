[![Codacy Badge](https://api.codacy.com/project/badge/Grade/2f2a446ef74646ec8494676a65eecb6b)](https://www.codacy.com/manual/t1waz/rest_utils?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=t1waz/rest_utils&amp;utm_campaign=Badge_Grade)[![CircleCI](https://circleci.com/gh/t1waz/rest_utils.svg?style=shield)](https://circleci.com/gh/t1waz/rest_utils)[![PyPI version](https://badge.fury.io/py/async-easy-utils.svg)](https://badge.fury.io/py/async-easy-utils)

ASYNC EASY UTILS
================
Simple tools to create RESTful backend API based on TorToiseORM and Starlette stack.

DESCRIPTION
===========
The main goal of the project is to provide easy-to-use tools for creating 
simple backend applications, inspired by Django REST based on:
- TorTosie ORM
    https://github.com/tortoise/tortoise-orm
- Starlette
    https://www.starlette.io/

The project provides:
- Serializer
- View

Serializer
---------
Tool similar to Django REST Serializer, which purpose is to:
- interface with the database model while performing CRUD operations
  Provide save, update and delete method. 
- data serialization
  Provide methods to serialize model instance into dict, dict to model instance.   
- data validation
  Validates data integrity against the model class. Inside serializer it is 
  possible to enclose custom validation logic by adding validation methods.
- defining access to model attributes
  provides the ability to define the available fields of the database model.
- creating dynamic model attributes
  Provide ability to define custom property methods for model that's are 
  dynamic calculate.

View
----
Tool similar to Django REST ModelViewSet, which purpose is to:
- provide basic views for CRUD operations.
  View implement GET, POST, PATCH, DELETE methods OOTB
- provide ability to define queryset access.
  Inside view we can assign queryset which will be used


HOW TO USE
==========

Serializer
----------
Definition based on Django REST. Each Seriliazier must have a defined 
model and fields to operate on. These definitions must be inside the
Meta class.

    from tortoise_rest_utils.serializer import Serializer
    
    
    class SampleSerializer(Serializer):
        class Meta:
                model = SampleModel
                fields = ('attribute_1', 'attribute_2')

Each value inside fields must be part od model attribute or belongs to serialized 
methods. We can define read only custom model properties by using methods like:

    class SampleSerializer(Serializer):
        class Meta:
                model = SampleModel
                fields = (attribute_1', 'attribute_2', 'serialized_attribute')
                
        async def get_serialized_attribute(self):
            return 'Foo'

Methods that start with 'get_' are handled like model properties 
in pattern: 'get_<field_name>'. After creating serialized attribute You should
inlcude field_name in fields. Each  serialized attribute is corutine.

It is possible to create custom validation method for field from model attributes:

    class SampleSerializer(Serializer):
        class Meta:
                model = SampleModel
                fields = (attribute_1', 'attribute_2')
                
        async def validate_attribute_1(self, data):
            if data is not 'Foo':
                return False

Methods that start with 'validate_' are handled like validators to model attribute in pattern: 'validate_<field_name>'. 
During validation Serializer pass initial data into each validator method. Each validator method is corutine.

It is possible to create foreign key slug field:

    class SampleSerializer(Serializer):
        sample_slug = ForeignKeyField(slug_field='foo',
                                      queryset=lambda: Model.all(),
                                      many=False)

    class Meta:
        model = SampleModel
        fields = (attribute_1', 'attribute_2', 'sample_slug')
        


