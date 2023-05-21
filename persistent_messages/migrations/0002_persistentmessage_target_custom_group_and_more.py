# Generated by Django 4.2 on 2023-05-21 16:07

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("persistent_messages", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="persistentmessage",
            name="target_custom_group",
            field=models.CharField(
                blank=True,
                help_text="Custom group to enable this flag for",
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="persistentmessage",
            name="target",
            field=models.CharField(
                choices=[
                    ("ALL_USERS", "All users, even logged out"),
                    ("AUTHENTICATED_USERS", "All logged-in users"),
                    ("ANONYMOUS_USERS", "All anonymous users"),
                    ("USERS_OR_GROUPS", "Specific users or groups (inc. custom)"),
                ],
                default="AUTHENTICATED_USERS",
                max_length=50,
            ),
        ),
    ]
