# Generated by Django 3.0.4 on 2020-03-30 11:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0010_auto_20200330_1416'),
    ]

    operations = [
        migrations.AddField(
            model_name='helprequest',
            name='first_name',
            field=models.CharField(default='', max_length=200),
        ),
        migrations.AddField(
            model_name='helprequest',
            name='last_name',
            field=models.CharField(default='', max_length=200),
        ),
    ]
