# Generated by Django 2.2.12 on 2020-05-07 17:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0105_auto_20200507_1707'),
    ]

    operations = [
        migrations.AlterField(
            model_name='problem',
            name='summary',
            field=models.TextField(help_text='Plain-text, shown in problem list and meta description tag, e.g. for social media.', verbose_name='problem summary'),
        ),
        migrations.AlterField(
            model_name='problemtranslation',
            name='summary',
            field=models.TextField(verbose_name='translated summary'),
        ),
    ]
