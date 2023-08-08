from tortoise import fields
from tortoise.models import Model
from uuid import uuid4


class TortoiseModel(Model):
    id = fields.CharField(max_length=255, pk=True, default=str(uuid4()))

    def as_dict(self):
        schema = self.describe()
        dicted = {field['name']: getattr(self, field['name']) for field in schema['data_fields']}
        dicted[schema['pk_field']['name']] = str(getattr(self, schema['pk_field']['name']))
        return dicted

    class Meta:
        abstract = True
