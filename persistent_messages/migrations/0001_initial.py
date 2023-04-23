# Generated by Django 4.2 on 2023-04-23 15:29

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MessageDismissal",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("dismissed_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="PersistentMessage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("content", models.TextField()),
                (
                    "mark_content_safe",
                    models.BooleanField(
                        default=False,
                        help_text="Explicitly allow JS and/or HTML in this message.",
                    ),
                ),
                (
                    "message_level",
                    models.IntegerField(
                        choices=[
                            (10, "DEBUG"),
                            (20, "INFO"),
                            (25, "SUCCESS"),
                            (30, "WARNING"),
                            (40, "ERROR"),
                        ],
                        default=20,
                        help_text="The level of the message, mapped from django.contrib.messages.constants.",
                    ),
                ),
                (
                    "message_target",
                    models.CharField(
                        choices=[
                            ("ALL_USERS", "All users, even logged out"),
                            ("AUTHENTICATED_USERS", "All logged-in users"),
                            ("USERS_OR_GROUPS", "Specific users or groups"),
                        ],
                        default="AUTHENTICATED_USERS",
                        max_length=50,
                    ),
                ),
                (
                    "display_from",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        help_text="The earliest time this message should be shown.",
                    ),
                ),
                (
                    "display_until",
                    models.DateTimeField(
                        blank=True,
                        help_text="The latest time this message should be shown.",
                        null=True,
                    ),
                ),
                (
                    "is_dismissable",
                    models.BooleanField(
                        default=True,
                        help_text="Whether this message can be dismissed by the user.",
                    ),
                ),
                (
                    "additional_extra_tags",
                    models.CharField(
                        blank=True,
                        help_text="Space-separated tags to add to the default extra tags ('persistent', 'dismissable').",
                        max_length=100,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dismissed_by",
                    models.ManyToManyField(
                        help_text="Users who have dismissed this message.",
                        through="persistent_messages.MessageDismissal",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "target_groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific groups to target - used when message_target is USERS_OR_GROUPS",
                        related_name="persistent_messages",
                        to="auth.group",
                    ),
                ),
                (
                    "target_users",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific users to target - used when message_target is USERS_OR_GROUPS",
                        related_name="persistent_messages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="messagedismissal",
            name="message",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="message_dismissals",
                to="persistent_messages.persistentmessage",
            ),
        ),
        migrations.AddField(
            model_name="messagedismissal",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="dismissed_messages",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="messagedismissal",
            unique_together={("user", "message")},
        ),
    ]
