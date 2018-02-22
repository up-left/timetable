from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django import forms
import datetime

from . import models

admin.site.register(models.ColumnType)
admin.site.register(models.Department)
admin.site.register(models.Room)
admin.site.register(models.Chamber)
admin.site.register(models.Doctor)
admin.site.register(models.Resident)
admin.site.register(models.Nurse)


class BuildingForm(forms.ModelForm):

    class Meta:
        model = models.Building
        fields = '__all__'
        widgets = {
            'odd_color': forms.TextInput(attrs={'type': 'color'}),
            'even_color': forms.TextInput(attrs={'type': 'color'}),
        }


@admin.register(models.Building)
class BuildingAdmin(admin.ModelAdmin):
    form = BuildingForm


class PlainTextWidget(forms.Widget):
    def __init__(self, text):
        super().__init__()
        self.text = mark_safe(text)

    def render(self, name, value, attrs=None, renderer=None):
        return self.text


COL_PREFIX = 'col_'


class RoomLineAdminFormMetaclass(forms.models.ModelFormMetaclass):

    def __new__(mcs, name, bases, attrs):
        # Динамически добавляем в форму дополнительные поля (они же дополнительные колонки)
        for coltype in models.ColumnType.objects.all():
            attrs[COL_PREFIX + str(coltype.pk)] = forms.CharField(label=coltype.name, max_length=8, required=False)
        return super().__new__(mcs, name, bases, attrs)


class RoomLineAdminForm(forms.ModelForm, metaclass=RoomLineAdminFormMetaclass):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Если операционная - для разных отделений, заменяем список множественного выбора на название отделения
        if self.instance.room is None:
            self.fields['dept'].widget = PlainTextWidget('')
        elif not self.instance.room.free_dept:
            self.fields['dept'].widget = PlainTextWidget(self.instance.room.department.name)

        for v in self.instance.columnvalue_set.all():
            self.fields[COL_PREFIX + str(v.column_type.pk)].initial = v.value

    def save(self, *args, **kwargs):
        line = super().save(*args, **kwargs)
        line.save()
        models.ColumnValue.objects.filter(room_line=line).delete()
        for key in self.cleaned_data.keys():
            if key.startswith(COL_PREFIX) and self.cleaned_data[key]:
                column_type_pk = int(key[len(COL_PREFIX):])
                models.ColumnValue(room_line=line, column_type=models.ColumnType(pk=column_type_pk), 
                                   value=self.cleaned_data[key]).save()
        return line

    class Meta:
        fields = ['room', 'begin_time', 'dept', 'doctor', 'resident', 'nurse', 'oair', 'link', 'comment']


class RoomLineAdmin(admin.TabularInline):
    model = models.RoomLine
    form = RoomLineAdminForm

    def get_formset(self, request, obj=None, **kwargs):
        # Ссылка со строки на строку: оставляем только строки, относящиеся к текущей таблице
        #  + делаем select_subclasses, чтобы у строки было человеческое описание
        formset = super().get_formset(request, obj, **kwargs)
        qs = formset.form.base_fields['link'].queryset
        qs = qs.filter(table=obj).select_subclasses()
        formset.form.base_fields['link'].queryset = qs
        return formset

    def get_fieldsets(self, request, obj=None):
        # Перемещаем колонки (дополнительные поля) в середину таблицы
        fieldsets = super().get_fieldsets(request, obj)
        field_names = fieldsets[0][1]['fields']
        fieldsets[0][1]['fields'] = field_names[:3] + field_names[9:] + field_names[3:9]
        return fieldsets


class ChamberLineAdmin(admin.TabularInline):
    model = models.ChamberLine
    fields = ['chamber', 'doctor', 'resident']

    def get_queryset(self, request):
        # workaround: без этого у палат будут дублирующиеся строчки
        return super().get_queryset(request).order_by()


class VacationLineAdmin(admin.TabularInline):
    model = models.VacationLine


@admin.register(models.Table)
class TableAdmin(admin.ModelAdmin):
    inlines = [RoomLineAdmin, ChamberLineAdmin, VacationLineAdmin]


def autocreate_table(request):
    table = models.Table(date=datetime.date.today() + datetime.timedelta(days=1))
    table.save()

    for room in models.Room.objects.filter(template=True, enable=True):
        table.line_set.add(models.RoomLine(table=table, room=room), bulk=False)

    for chamber in models.Chamber.objects.filter(template=True, enable=True):
        chamber_line = models.ChamberLine.objects.create(table=table)
        chamber_line.chamber.add(chamber)
        table.line_set.add(chamber_line, bulk=False)

    return HttpResponseRedirect(reverse("admin:main_table_change", args=[table.pk]))
