from django.db import migrations

from core.fields import (
    ENCRYPTED_PREFIX,
    encrypt_value,
)


def encrypt_existing_olt_credentials(
    apps,
    schema_editor,
):
    connection = schema_editor.connection

    targets = [
        (
            "olt_oltdevice",
            "telnet_password",
        ),
        (
            "olt_oltdevice",
            "snmp_community",
        ),
    ]

    with connection.cursor() as cursor:
        for table_name, column_name in targets:
            cursor.execute(
                f"""
                SELECT id, {column_name}
                FROM {table_name}
                """
            )

            rows = cursor.fetchall()

            for row_id, value in rows:
                if value is None:
                    continue

                value = str(value)

                if not value:
                    continue

                if value.startswith(
                    ENCRYPTED_PREFIX
                ):
                    continue

                encrypted = encrypt_value(
                    value
                )

                cursor.execute(
                    f"""
                    UPDATE {table_name}
                    SET {column_name} = %s
                    WHERE id = %s
                    """,
                    [
                        encrypted,
                        row_id,
                    ],
                )


class Migration(migrations.Migration):

    dependencies = [
        (
            "olt",
            "0007_alter_oltdevice_snmp_community_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(
            encrypt_existing_olt_credentials,
            migrations.RunPython.noop,
        ),
    ]