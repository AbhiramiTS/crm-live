# Generated by Django 3.1.1 on 2020-12-12 17:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_order_date_delivered'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='order_price',
            field=models.FloatField(null=True),
        ),
    ]
