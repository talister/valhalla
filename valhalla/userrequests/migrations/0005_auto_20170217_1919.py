# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-17 19:19
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('userrequests', '0004_auto_20170125_1724'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='userrequest',
            options={'ordering': ('-created',)},
        ),
        migrations.AlterField(
            model_name='molecule',
            name='request',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='molecules', to='userrequests.Request'),
        ),
        migrations.AlterField(
            model_name='request',
            name='user_request',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requests', to='userrequests.UserRequest'),
        ),
        migrations.AlterField(
            model_name='window',
            name='request',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='windows', to='userrequests.Request'),
        ),
    ]