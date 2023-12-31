# Generated by Django 2.2.12 on 2020-05-07 23:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0106_auto_20200507_1709'),
    ]

    operations = [
        migrations.AddField(
            model_name='problemgroup',
            name='description',
            field=models.CharField(default='no description registered', max_length=100, verbose_name='problem group description'),
        ),
        migrations.AlterField(
            model_name='problemgroup',
            name='full_name',
            field=models.CharField(max_length=40, verbose_name='problem group name'),
        ),
    ]
