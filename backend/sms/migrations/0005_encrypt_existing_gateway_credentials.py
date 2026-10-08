import json

from django.db import migrations

from core.fields import (
    ENCRYPTED_PREFIX,
    encrypt_value,
)


def encrypt_existing_credentials(
    apps,
    schema_editor,
):
    connection = (
        schema_editor.connection
    )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, credentials
            FROM sms_smsgateway
            """
        )

        rows = cursor.fetchall()

        for gateway_id, value in rows:
            if value is None:
                continue

            if isinstance(
                value,
                (
                    dict,
                    list,
                ),
            ):
                serialized = json.dumps(
                    value,
                    separators=(",", ":"),
                    sort_keys=True,
                )

            else:
                serialized = str(
                    value
                )

                if not serialized:
                    continue

                if serialized.startswith(
                    ENCRYPTED_PREFIX
                ):
                    continue

                try:
                    parsed = json.loads(
                        serialized
                    )

                    serialized = json.dumps(
                        parsed,
                        separators=(",", ":"),
                        sort_keys=True,
                    )

                except (
                    json.JSONDecodeError,
                    TypeError,
                ):
                    continue

            encrypted = encrypt_value(
                serialized
            )

            cursor.execute(
                """
                UPDATE sms_smsgateway
                SET credentials = %s
                WHERE id = %s
                """,
                [
                    encrypted,
                    gateway_id,
                ],
            )


class Migration(migrations.Migration):

    dependencies = [
        (
            "sms",
            "0004_alter_smsgateway_credentials",
        ),
    ]

    operations = [
        migrations.RunPython(
            encrypt_existing_credentials,
            migrations.RunPython.noop,
        ),
    ]