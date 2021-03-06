# Generated by Django 2.0.1 on 2018-02-22 08:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_auto_20180222_1533'),
    ]

    operations = [
        migrations.CreateModel(
            name='ColumnType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=8, verbose_name='Название')),
            ],
            options={
                'ordering': ['id'],
                'verbose_name_plural': 'Наркозы',
                'verbose_name': 'наркоз',
            },
        ),
        migrations.AddField(
            model_name='columnvalue',
            name='column_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.ColumnType'),
        ),
    ]
