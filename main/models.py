from django.db import models
from model_utils.managers import InheritanceManager


class Building(models.Model):
    name = models.CharField(verbose_name='Название', max_length=16)
    odd_color = models.CharField(verbose_name='Цвет 1', max_length=7, default='#ffffff')
    even_color = models.CharField(verbose_name='Цвет 2', max_length=7, default='#ffffff')

    class Meta:
        verbose_name = 'корпус'
        verbose_name_plural = 'Корпусы'
        ordering = ['name']

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(verbose_name='Название', max_length=32)

    class Meta:
        verbose_name = 'отделение'
        verbose_name_plural = 'Отделения'
        ordering = ['name']

    def __str__(self):
        return self.name


# Дополнительные колонки, используются для разных видов наркозов
class ColumnType(models.Model):
    name = models.CharField(verbose_name='Название', max_length=8)

    class Meta:
        verbose_name = 'наркоз'
        verbose_name_plural = 'Наркозы'
        ordering = ['id']

    def __str__(self):
        return self.name


class Place(models.Model):
    enable = models.BooleanField(verbose_name='Показывать', default=True)
    template = models.BooleanField(verbose_name='Создавать каждый раз', default=False)


class Room(Place):
    building = models.ForeignKey(Building, verbose_name='Корпус', on_delete=models.SET_NULL, null=True)
    floor = models.IntegerField(verbose_name='Этаж')
    number = models.CharField(verbose_name='Номер', max_length=9, blank=True)
    department = models.ForeignKey(Department, verbose_name='Отделение', on_delete=models.SET_NULL,
                                   null=True, blank=True)
    # free_dept=True означает, что отделения будут задаваться в RoomLine, а Room.department не будет учитываться
    # операционная может быть закреплена за одним отделением, а может каждый день использоваться для разных отделений
    free_dept = models.BooleanField(verbose_name='Для разных отделений', default=False)

    class Meta:
        verbose_name = 'операционная'
        verbose_name_plural = 'Операционные'
        ordering = ['building__name', '-floor', 'number']

    ROMAN_LIT = ('0', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV')

    def floor_roman(self):
        return Room.ROMAN_LIT[self.floor] if 0 < self.floor < len(Room.ROMAN_LIT) else self.floor

    def __str__(self):
        return '{0}:{1} {2} {3}'.format(
            self.building.name if self.building else '', 
            self.floor_roman(), 
            ('№' if self.number.isdigit() else '') + self.number, 
            self.department.name if not self.free_dept and self.department else '')


class Chamber(Place):
    name = models.CharField(verbose_name='Название', max_length=32)

    class Meta:
        verbose_name = 'палата'
        verbose_name_plural = 'Палаты'
        ordering = ['name']

    def __str__(self):
        return self.name


class Employee(models.Model):
    name = models.CharField(verbose_name='ФИО', max_length=64)
    enable = models.BooleanField(verbose_name='Показывать', default=True)

    class Meta:
        verbose_name = 'работник'
        verbose_name_plural = 'Работники'
        ordering = ['name']

    def __str__(self):
        return self.name


class Doctor(Employee):

    class Meta:
        verbose_name = 'анестезиолог'
        verbose_name_plural = 'Анестезиологи'


class Resident(Employee):

    class Meta:
        verbose_name = 'ординатор'
        verbose_name_plural = 'Ординаторы'


class Nurse(Employee):

    class Meta:
        verbose_name = 'медсестра'
        verbose_name_plural = 'Медсестры'


class Table(models.Model):
    date = models.DateField(verbose_name='Дата')
    comment = models.TextField(verbose_name='Комментарий', blank=True)

    class Meta:
        verbose_name = 'расписание'
        verbose_name_plural = 'Расписания'
        ordering = ['-date']

    def column_types(self):
        return [{'id': cs['column_type__id'], 'name': cs['column_type__name']}
                for cs in ColumnValue.objects.filter(room_line__table=self)
                                             .values('column_type__id', 'column_type__name').distinct()]

    def __str__(self):
        return 'Расписание на ' + self.date.isoformat()


class Line(models.Model):
    objects = InheritanceManager()
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, verbose_name='Анестезиолог', on_delete=models.SET_NULL, 
                               null=True, blank=True, limit_choices_to={'enable': True})
    resident = models.ForeignKey(Resident, verbose_name='Ординатор', on_delete=models.SET_NULL, 
                                 null=True, blank=True, limit_choices_to={'enable': True})


class RoomLine(Line):
    room = models.ForeignKey(Room, verbose_name='Операционная', on_delete=models.SET_NULL,
                             null=True, limit_choices_to={'enable': True})
    link = models.ForeignKey(Line, related_name='linelink', verbose_name='Ссылка', 
                             on_delete=models.SET_NULL, null=True, blank=True)
    dept = models.ManyToManyField(Department, verbose_name='Отделения', blank=True)
    comment = models.CharField(verbose_name='Комментарий', max_length=256, blank=True)
    nurse = models.ForeignKey(Nurse, verbose_name='Медсестра', on_delete=models.SET_NULL, 
                              null=True, blank=True, limit_choices_to={'enable': True})
    begin_time = models.CharField(verbose_name='Начало', max_length=8, blank=True, null=True)
    oair = models.IntegerField(verbose_name='в ОАиР', blank=True, null=True)

    class Meta:
        verbose_name = 'назначение операционной'
        verbose_name_plural = 'Расписание операционных'
        ordering = ['room__building__name', '-room__floor', 'room__number']

    def dept_str(self):
        return ', '.join(dept.name for dept in self.dept.all()) if self.room.free_dept else \
            self.room.department.name if self.room.department else ''

    def columns(self):
        return {v.column_type.id: v.value for v in self.columnvalue_set.all()}

    def __str__(self):
        return '{0}:{1} {2} -> {3}'.format(
            self.room.building.name if self.room and self.room.building else '',
            self.room.floor_roman() if self.room else '',
            (('№' if self.room.number.isdigit() else '') + self.room.number) if self.room else '',
            self.doctor if self.doctor else '')


class ColumnValue(models.Model):
    column_type = models.ForeignKey(ColumnType, on_delete=models.SET_NULL, null=True, blank=True)
    room_line = models.ForeignKey(RoomLine, on_delete=models.CASCADE)
    value = models.CharField(max_length=8, blank=True)


class ChamberLine(Line):
    chamber = models.ManyToManyField(Chamber, verbose_name='Палаты', blank=True, limit_choices_to={'enable': True})

    class Meta:
        verbose_name = 'назначение для палаты'
        verbose_name_plural = 'Расписание для палат'
        ordering = ['chamber__name']

    def __str__(self):
        return '{0} -> {1}'.format('; '.join(ch.name for ch in self.chamber.all()), self.doctor if self.doctor else '')


class VacationLine(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, verbose_name='Врач', on_delete=models.SET_NULL, 
                                 null=True, limit_choices_to={'enable': True})

    class Meta:
        verbose_name = 'отпуск'
        verbose_name_plural = 'Отпуска'
        ordering = ['employee__name']
