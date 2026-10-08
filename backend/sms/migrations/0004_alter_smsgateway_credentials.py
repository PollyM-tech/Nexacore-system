import core.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "sms",
            "0003_alter_smsgateway_organization_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="smsgateway",
            name="credentials",
            field=core.fields.EncryptedJSONField(
                blank=True,
                default=dict,
            ),
        ),
    ]