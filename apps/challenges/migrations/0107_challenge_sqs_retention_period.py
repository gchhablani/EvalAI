# Generated by Django 2.2.20 on 2023-10-11 00:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('challenges', '0106_challenge_worker_image_url_alter'),
    ]

    operations = [
        migrations.AddField(
            model_name='challenge',
            name='sqs_retention_period',
            field=models.PositiveIntegerField(default=259200, verbose_name='SQS Retention Period'),
        ),
    ]
