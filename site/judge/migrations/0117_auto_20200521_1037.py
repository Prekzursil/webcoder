# Generated by Django 2.2.12 on 2020-05-21 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0116_auto_20200519_0007'),
    ]

    operations = [
        migrations.AddField(
            model_name='problemtestcase',
            name='input_text',
            field=models.TextField(blank=True, verbose_name='input text'),
        ),
        migrations.AddField(
            model_name='problemtestcase',
            name='is_example',
            field=models.BooleanField(default=False, verbose_name='case is example?'),
        ),
        migrations.AddField(
            model_name='problemtestcase',
            name='output_text',
            field=models.TextField(blank=True, verbose_name='output text'),
        ),
    ]
