# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-23 22:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sciapplications', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scienceapplication',
            name='coi',
            field=models.TextField(blank=True, default=''),
        ),
    ]