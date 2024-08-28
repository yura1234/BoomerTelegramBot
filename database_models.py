from tortoise.models import Model
from tortoise import fields


class User(Model):
    user_id = fields.IntField(primary_key=True)
    username = fields.TextField()
    fullname = fields.TextField()

    class Meta:
        table = "users"


class SupportChat(Model):
    chat_id = fields.IntField(primary_key=True)
    contract_type = fields.TextField()
    chat_name = fields.TextField()
    link = fields.TextField()
    user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE)

    class Meta:
        table = "support_chats"


class AccesChannelUser(Model):
    id = fields.IntField(primary_key=True)
    product = fields.TextField()
    email = fields.TextField()
    sto_name = fields.TextField()
    permission = fields.BooleanField()
    user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE)

    class Meta:
        table = "acces_channel_users"
