import core.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "olt",
            "0006_alter_oltdevice_organization",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="oltdevice",
            name="snmp_community",
            field=core.fields.EncryptedTextField(
                default="public",
            ),
        ),
        migrations.AlterField(
            model_name="oltdevice",
            name="telnet_password",
            field=core.fields.EncryptedTextField(
                blank=True,
                default="",
            ),
        ),
    ]