# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2020-04-28 19:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("jobs", "0015_add_archived_as_a_submission_status")]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="ignore_submission",
            field=models.BooleanField(default=False),
        )
    ]
