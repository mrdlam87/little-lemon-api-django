# Generated by Django 4.1.6 on 2023-02-10 20:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("LittleLemonAPI", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="cart",
            name="quantity",
            field=models.SmallIntegerField(default=0),
            preserve_default=False,
        ),
    ]
