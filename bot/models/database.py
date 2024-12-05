from enum import StrEnum
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
    decline_comment = fields.TextField(null=True)

    class Meta:
        table = "acces_channel_users"


class BroadcastData(Model):

    class TypeMessage(StrEnum):
        TEXT = "TEXT"
        PHOTO = "PHOTO"
        VIDEO = "VIDEO"

    id = fields.IntField(primary_key=True)
    type = fields.CharEnumField(
        enum_type=TypeMessage,
        default=TypeMessage.TEXT
    )
    caption_text = fields.TextField()
    file_id = fields.TextField()
    created_date = fields.DatetimeField(auto_now_add=True)
    updated_date = fields.DatetimeField(auto_now=True)
    is_sheduled = fields.BooleanField(null=True)

    class Meta:
        table = "broadcast_data"


class BroadcastDataHistory(Model):
    user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE)
    message_id = fields.IntField()
    broadcast_data = fields.ForeignKeyField("models.BroadcastData", on_delete=fields.CASCADE)

    class Meta:
        table = "broadcast_data_history"


class LastUserMessage(Model):
    message_id = fields.IntField()
    user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE)
    updated_date = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "last_user_message"
